# Internal Expert & Policy Finder

Search an internal knowledge base (policies and Q&As) and the employee
directory using semantic search, so an employee can find either "what's the
answer" (a KnowledgeEntry, with the author surfaced as "the expert to
contact") or "who should I ask" (a ranked list of Employee profiles whose
skills/bio best match a free-text query).

Stack: React + Vite + TypeScript (frontend), Django REST Framework
(backend), **Postgres** (plain, relational data only) + **Qdrant** (a
dedicated vector database, embeddings only). No Celery/Redis - there is no
background/async work in this app.

## Two databases, not pgvector

Unlike the six earlier "AI apps" in this workspace (doc-search,
faq-chatbot, job-matcher, product-recommender, ticket-triage, recipe-finder),
which bolt pgvector onto Postgres as an extension, this app keeps **two
genuinely separate database systems**:

1. **Postgres** - every relational/transactional row: users, employee
   profiles, knowledge entries. No `vector` extension, no special column
   types. Plain `postgres:16`.
2. **Qdrant** - a dedicated vector database (`qdrant-client` Python
   package), running as its own service, holding nothing but embeddings and
   a small filterable payload per point. Two collections:
   - `knowledge_entries` (payload: `visibility_departments`, `entry_type`,
     `author_id`)
   - `employees` (payload: `department`)

**There is no foreign-key or shared-transaction consistency between the
two.** A Qdrant point id is just the matching Django model's integer
primary key (`KnowledgeEntry.id` / `Employee.id`) - that's the only thing
joining the two stores back together, done explicitly in application code
(`apps/knowledge/services/search.py`), not by the database.

### Keeping them in sync

- `apps/directory/signals.py` and `apps/knowledge/signals.py` hook
  `post_save`/`post_delete` on `Employee` and `KnowledgeEntry`. On save, the
  Qdrant upsert is scheduled via `transaction.on_commit(...)` - **not**
  inline in `save()` - so a vector is never written for a Postgres write
  that later rolls back. On delete there's no rollback risk, so the Qdrant
  point is removed directly.
- **This is a real operational tradeoff, not just a testing detail**: if the
  Qdrant container/volume is ever lost while Postgres survives, every
  embedding is gone and search returns nothing, even though all the
  underlying rows are still in Postgres. The recovery path is:
  ```bash
  python manage.py sync_vectors
  ```
  which re-embeds and re-upserts every `Employee` and `KnowledgeEntry` row
  into Qdrant from scratch. It's idempotent (upsert replaces by id), so it's
  always safe to run.
- The demo seed data migration
  (`apps/knowledge/migrations/0002_seed_demo_data.py`) seeds Qdrant too, not
  just Postgres - guarded so a Qdrant hiccup at migrate time only logs a
  warning and the Postgres-side seed still succeeds (`sync_vectors` repairs
  it afterwards).

### Dev/test mode: an in-process Qdrant, not a mock

`apps/common/qdrant_store.py` is a thin wrapper around
`qdrant_client.QdrantClient`:

- **`QDRANT_URL` unset** (combined with `USE_SQLITE=True`): constructs
  `QdrantClient(location=":memory:")` - qdrant-client's fully local,
  in-process embedded mode. This is the **real Qdrant engine itself**
  running in-process, not a stub or fake - search/filter behavior is
  identical to a real server. This is the equivalent of `USE_SQLITE` for the
  vector half of this app's architecture, and it's why the whole app,
  including semantic search, is fully testable with zero external services.
- **`QDRANT_URL` set** (e.g. `http://localhost:6333`): constructs
  `QdrantClient(url=QDRANT_URL)`, talking to a real Qdrant server
  (docker-compose's `qdrant` service).

**Important caveat specific to `:memory:` mode**: the in-process store is
held in a single Python process's memory (a module-level singleton client -
see `qdrant_store._get_client`) and is **not persisted across process
restarts**, unlike SQLite's file-backed database. Concretely: if you run
`python manage.py migrate` (which seeds Qdrant) and then start a *separate*
`python manage.py runserver` process, that new process's in-memory Qdrant
store starts **empty** - search will return nothing until you run
`python manage.py sync_vectors` in that same running process (or restart
it after running `sync_vectors` isn't necessary - just run it once after
the server is up). This is only relevant to the `USE_SQLITE=True` dev-only
path; `docker-compose.yml` always points `QDRANT_URL` at the real `qdrant`
service, which persists via its own volume regardless of how many times the
`backend` container restarts.

## Data model

- `User` (`apps/accounts`) - email login, `role` (`employee` or
  `hr_admin`), `department`, `full_name`. No self-registration endpoint -
  accounts are provisioned by an hr_admin or the demo seed migration, since
  role/department assignment isn't something a user should grant themselves.
- `Employee` (`apps/directory`) - a directory profile: `full_name`,
  `department`, `title`, `skills_summary`, `bio`, and an optional one-to-one
  link to a `User` (nullable - most directory entries don't correspond to a
  login account at all; a `User` who wants to author `KnowledgeEntry` rows
  needs a linked `Employee` profile).
- `KnowledgeEntry` (`apps/knowledge`) - `title`, `body`, `entry_type`
  (`policy` or `qna`), `author` (FK to `Employee`), `visibility_departments`
  (a `JSONField` list of department-name strings; empty/null = public,
  non-empty = restricted to those departments), timestamps.

  `visibility_departments` is a plain `JSONField` rather than Postgres's
  `ArrayField`, so the exact same model works on SQLite (`USE_SQLITE=True`)
  and Postgres. For the same reason, visibility filtering in
  `apps/knowledge/views.py` is done in Python rather than via a DB-level
  JSONField `contains` lookup - Django's `contains`/`contained_by` lookups
  are Postgres/MySQL/MariaDB-only, not supported on SQLite at all.

## Permissions

- **Employee directory** (`/api/employees/`): any authenticated user can
  list/retrieve (org-wide directory). `hr_admin` can create/edit/delete any
  profile; a regular employee can edit (not create/delete) only the profile
  linked to their own account.
- **Knowledge entries** (`/api/knowledge-entries/`): list/retrieve is
  filtered by department visibility (see below) at the queryset level, so a
  non-visible entry 404s rather than 403s - same cross-scope isolation
  pattern as the other apps in this workspace. `hr_admin` can
  create/edit/delete any entry, including department-restricted policies. A
  regular employee can only create/edit `entry_type=qna` entries with empty
  `visibility_departments` (public) - **enforced in
  `KnowledgeEntrySerializer.validate()`, not just a permission class**, so
  the wrong shape of request gets a 400 explaining why, and can only
  edit/delete entries they authored themselves.
- **Search** (`/api/search/knowledge/`, `/api/search/experts/`): knowledge
  search applies the same department-visibility rule as list/retrieve
  (public-or-matching-department), with `hr_admin` requests bypassing the
  filter entirely (sees everything, matching the list/detail "hr_admin sees
  everything" rule). Expert search has no visibility restriction at all -
  the employee directory is org-wide.

A dedicated test
(`apps/knowledge/tests/test_permissions_visibility.py`) proves an employee
in one department cannot see another department's restricted
`KnowledgeEntry` via `/api/search/knowledge/`, nor via the list/detail
endpoints, while `hr_admin` sees everything and a public entry is visible
regardless of department.

## Stub-by-default AI layer

No OpenAI API key is required to run or test this app.
`backend/apps/common/ai.py`'s `get_embedding(text)` calls OpenAI's
embeddings API (`OPENAI_EMBEDDING_MODEL`, default `text-embedding-3-large`,
truncated to `OPENAI_EMBEDDING_DIMENSIONS` via OpenAI's `dimensions` param,
default 1536) when `OPENAI_API_KEY` is set. Without a key, it returns a
**deterministic pseudo-random vector** seeded from a SHA-256 hash of the
text - reproducible and fully testable with no network access or API cost,
but **not semantically meaningful**: stub-embedding search results are not
real semantic matches, just a working pipeline. Real search quality
requires a real `OPENAI_API_KEY`.

## REST API

All endpoints except login/refresh require a JWT access token
(`Authorization: Bearer <token>`).

- `POST /api/auth/login/` - returns `{access, refresh}`
- `POST /api/auth/refresh/` - rotates the refresh token (rotation +
  blacklist enabled, see `SIMPLE_JWT` in `config/settings/base.py`)
- `POST /api/auth/logout/` - blacklists the given refresh token
- `GET /api/users/me/`
- `GET/POST /api/employees/`, `GET/PUT/PATCH/DELETE /api/employees/{id}/`
- `GET/POST /api/knowledge-entries/`,
  `GET/PUT/PATCH/DELETE /api/knowledge-entries/{id}/`
- `GET /api/search/knowledge/?q=...&top_k=5` - semantic search over
  `KnowledgeEntry`, returns `[{id, title, body, entry_type, score,
  expert_contact: {id, name, department}}]`
- `GET /api/search/experts/?q=...&top_k=5` - semantic search over
  `Employee`, returns `[{id, full_name, department, title, skills_summary,
  score}]`

## Running with Docker (Postgres + Qdrant, both real services)

```bash
cp .env.example .env
docker compose up --build
```

Frontend: http://localhost:5173 - Backend: http://localhost:8000/api -
Django admin: http://localhost:8000/admin/.

## Running the backend without Docker (dev-only SQLite + in-process Qdrant)

```bash
cd backend
python -m venv venv
source venv/Scripts/activate   # Windows Git Bash; use venv/bin/activate on macOS/Linux
pip install -r requirements.txt

export USE_SQLITE=True
export DJANGO_SETTINGS_MODULE=config.settings.dev

python manage.py migrate      # applies schema + seed data migration (Postgres AND Qdrant)
python manage.py test         # full test suite
python manage.py runserver
```

**After starting `runserver` this way**, run `python manage.py sync_vectors`
once in a separate terminal (hitting the running server isn't required -
any `manage.py` invocation against the same `USE_SQLITE=True` sqlite file
works, but note each `manage.py` invocation is its *own* process with its
*own* empty in-memory Qdrant store - see the caveat above. The cleanest way
to guarantee the running `runserver` process's in-memory store is
populated is to add a `python manage.py sync_vectors &&` step before
`runserver` in the same shell invocation, same as `docker-compose.yml`
does for the real-Postgres/real-Qdrant path.)

## Running the frontend

```bash
cd frontend
npm install
npm run dev     # http://localhost:5173
npm run build   # production build
```

## Demo login credentials

Seeded by `apps/knowledge/migrations/0002_seed_demo_data.py`:

| Email | Password | Role | Department |
|---|---|---|---|
| `employee@example.com` | `demo12345` | employee | Engineering |
| `hradmin@example.com` | `demo12345` | hr_admin | HR |

The same migration seeds 10 `Employee` directory profiles across four
departments (Engineering, HR, Finance, Sales) and 18 `KnowledgeEntry` rows
(a mix of `policy`/`qna`, mostly public, several restricted to specific
departments), embedding all of them into Qdrant as part of the migration.

## Verification status (this environment)

Verified locally (Python 3.12, Node 22, SQLite + in-process Qdrant
`:memory:` mode - no Docker/real Postgres/real Qdrant required for this):

| Check | Result |
|---|---|
| `pip install -r requirements.txt` | pass |
| `manage.py check` | pass, 0 issues |
| `manage.py makemigrations --check --dry-run` | pass, no changes detected |
| `manage.py migrate` | pass - creates schema + seeds 2 demo users, 10 employees, 18 knowledge entries, each synced into Qdrant |
| `manage.py migrate` (second run) | pass - idempotent, no duplicate rows |
| `manage.py test` (77 tests) | pass |
| `npm install` / `npm run build` | pass |

A real Postgres (`localhost:5432`, native default port - **different** from
the earlier six AI apps' pgvector-enabled Podman container on port 5433)
and a real Qdrant server (`localhost:6333`) are available in this
environment for manual verification against real services, but are **not**
required for `manage.py test`, which runs entirely on `USE_SQLITE=True` +
Qdrant `:memory:` mode.
