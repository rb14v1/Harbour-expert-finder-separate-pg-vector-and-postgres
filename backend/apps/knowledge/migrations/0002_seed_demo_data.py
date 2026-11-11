# Idempotent data migration: creates two demo user accounts, an employee
# directory spanning four departments, and a knowledge base of policy/Q&A
# entries (a mix of public and department-restricted), then seeds both into
# their matching Qdrant collections so semantic search works immediately
# after a fresh `migrate` - no separate `sync_vectors` run needed.
#
# Safe to run repeatedly: every row is created via `get_or_create` keyed on a
# stable natural key (email / full_name / title), so a second `migrate`
# never duplicates rows.
#
# Qdrant sync is best-effort here: if Qdrant is briefly unreachable at
# migrate time (e.g. the real server isn't up yet), the sync step logs a
# warning and the migration still succeeds for the Postgres side - run
# `python manage.py sync_vectors` afterwards to repair. See
# apps/common/qdrant_store.py and apps/common/management/commands/sync_vectors.py.

import logging

from django.db import migrations

logger = logging.getLogger(__name__)

DEMO_PASSWORD = "demo12345"

DEMO_USERS = [
    # (email, role, department, full_name)
    ("employee@example.com", "employee", "Engineering", "Alex Carter"),
    ("hradmin@example.com", "hr_admin", "HR", "Morgan Lee"),
]

# (full_name, department, title, skills_summary, bio, linked_user_email_or_None)
EMPLOYEES = [
    (
        "Alex Carter",
        "Engineering",
        "Senior Backend Engineer",
        "Python, Django, PostgreSQL, Kubernetes, distributed systems design",
        "Builds and operates the core platform services. Go-to person for "
        "backend architecture questions and service design reviews.",
        "employee@example.com",
    ),
    (
        "Morgan Lee",
        "HR",
        "HR Business Partner",
        "Employee relations, policy design, conflict resolution, performance management",
        "Partners with engineering and finance leadership on people "
        "policy and handles escalated employee relations cases.",
        "hradmin@example.com",
    ),
    (
        "Priya Nair",
        "Engineering",
        "Security Engineer",
        "Security audits, penetration testing, threat modeling, Python, incident response",
        "Runs the company's security review program and leads "
        "post-incident reviews for any security-relevant outage.",
        None,
    ),
    (
        "Jordan Smith",
        "Engineering",
        "DevOps Lead",
        "Kubernetes, CI/CD pipelines, Terraform, AWS, on-call incident response",
        "Owns the deployment pipeline and on-call rotation tooling. "
        "First escalation point for infrastructure incidents.",
        None,
    ),
    (
        "Jamie Patel",
        "Engineering",
        "Data Engineer",
        "ETL pipelines, SQL, Python, Airflow, data warehousing",
        "Maintains the analytics data warehouse and the pipelines that "
        "feed it from production systems.",
        None,
    ),
    (
        "Sam Okafor",
        "Finance",
        "Financial Analyst",
        "Financial modeling, budgeting, forecasting, Excel, SAP",
        "Builds quarterly forecasts and departmental budgets, and "
        "reviews large expense requests before approval.",
        None,
    ),
    (
        "Taylor Brooks",
        "Finance",
        "Controller",
        "GAAP compliance, financial reporting, audits, tax filings",
        "Oversees month-end and quarter-end close and is the primary "
        "contact for external audit requests.",
        None,
    ),
    (
        "Casey Kim",
        "Sales",
        "Account Executive",
        "Enterprise sales, contract negotiation, Salesforce, pipeline management",
        "Manages the largest enterprise accounts and mentors new "
        "account executives on negotiation strategy.",
        None,
    ),
    (
        "Riley Chen",
        "Sales",
        "Sales Operations Manager",
        "Sales analytics, territory planning, Salesforce administration, commission tracking",
        "Keeps the Salesforce instance running and assigns sales "
        "territories each planning cycle.",
        None,
    ),
    (
        "Dana Rodriguez",
        "HR",
        "Technical Recruiter",
        "Technical recruiting, sourcing, interview design, offer negotiation",
        "Leads engineering hiring end to end, from sourcing through "
        "offer, and designs interview loops for new roles.",
        None,
    ),
]

# (title, body, entry_type, author_full_name, visibility_departments)
KNOWLEDGE_ENTRIES = [
    (
        "Remote Work Policy",
        "Employees may work remotely up to 3 days per week with manager approval. "
        "Fully remote arrangements require VP sign-off and are reviewed every 6 months.",
        "policy",
        "Morgan Lee",
        [],
    ),
    (
        "Expense Reimbursement Policy",
        "Submit expense reports within 30 days of purchase via the finance portal, with "
        "an itemized receipt attached. Reimbursements over $500 require manager approval "
        "before submission.",
        "policy",
        "Taylor Brooks",
        [],
    ),
    (
        "Code Review Guidelines",
        "Every pull request needs at least one approval before merging to main. Prefer "
        "small, focused PRs; large changes should be split or pre-discussed in a design doc.",
        "policy",
        "Jordan Smith",
        [],
    ),
    (
        "Incident Response Runbook",
        "On a Sev1 page, acknowledge within 5 minutes, open an incident channel, and page "
        "the secondary on-call if unresolved after 15 minutes. Full postmortem required "
        "within 3 business days.",
        "policy",
        "Jordan Smith",
        ["Engineering"],
    ),
    (
        "Employee Referral Bonus Program",
        "Refer a candidate who is hired and stays 90 days to receive a $2,000 bonus "
        "($3,500 for hard-to-fill engineering roles). Submit referrals through the careers "
        "portal before the candidate applies.",
        "policy",
        "Dana Rodriguez",
        [],
    ),
    (
        "Sales Commission Structure",
        "Base commission is 8% of closed-won annual contract value, rising to 12% once a "
        "rep exceeds 110% of quarterly quota. Commissions are paid the month after the "
        "invoice is collected.",
        "policy",
        "Riley Chen",
        ["Sales"],
    ),
    (
        "Annual Performance Review Process",
        "Reviews run every March: self-assessment, manager assessment, and a calibration "
        "session across each department before ratings are finalized and shared.",
        "policy",
        "Morgan Lee",
        [],
    ),
    (
        "Data Classification & Handling Policy",
        "Classify data as Public, Internal, Confidential, or Restricted. Confidential and "
        "Restricted data must be encrypted at rest and never copied to a personal device.",
        "policy",
        "Priya Nair",
        ["Engineering"],
    ),
    (
        "Travel & Expense Approval Limits",
        "Domestic travel under $1,500 needs manager approval; international travel or any "
        "trip over $1,500 needs director approval before booking.",
        "policy",
        "Sam Okafor",
        ["Finance"],
    ),
    (
        "Quarter-End Close Checklist",
        "Internal finance checklist for closing the books: reconcile sub-ledgers, review "
        "accruals, confirm intercompany balances, then lock the period before reporting.",
        "policy",
        "Sam Okafor",
        ["Finance"],
    ),
    (
        "How do I request parental leave?",
        "Submit a leave request through the HR portal at least 30 days before the "
        "expected start date. Eligible employees get 12 weeks paid leave; HR will confirm "
        "eligibility and coordinate the return-to-work date.",
        "qna",
        "Morgan Lee",
        [],
    ),
    (
        "How do I reset my VPN access?",
        "Open a ticket in the IT queue tagged 'VPN'; DevOps resets access within one "
        "business day. For urgent access needs, ping #devops-oncall directly.",
        "qna",
        "Jordan Smith",
        [],
    ),
    (
        "What's our on-call rotation policy?",
        "On-call rotates weekly across the platform team, with a primary and secondary "
        "engineer each week. Swaps are fine as long as both engineers confirm in the "
        "on-call calendar.",
        "qna",
        "Jordan Smith",
        [],
    ),
    (
        "How do I submit a reimbursement for a conference?",
        "Keep the registration receipt and any travel receipts, then file one expense "
        "report covering the whole trip within 30 days of returning.",
        "qna",
        "Taylor Brooks",
        [],
    ),
    (
        "How do I escalate a security vulnerability report?",
        "Email security@ or post in #security-escalations with details and reproduction "
        "steps. Critical vulnerabilities get triaged within 4 hours.",
        "qna",
        "Priya Nair",
        [],
    ),
    (
        "How are sales territories assigned?",
        "Territories are reassigned each planning cycle based on account size and region; "
        "sales ops publishes the updated map two weeks before the new quarter starts.",
        "qna",
        "Casey Kim",
        [],
    ),
    (
        "What tools do we use for data warehousing?",
        "The warehouse runs on a cloud data warehouse with Airflow-orchestrated ETL jobs "
        "pulling from production Postgres replicas and third-party APIs.",
        "qna",
        "Jamie Patel",
        [],
    ),
    (
        "How do I request a new Salesforce license?",
        "File a request with sales ops including the new hire's role and team; licenses "
        "are provisioned within two business days of a signed offer letter.",
        "qna",
        "Riley Chen",
        ["Sales"],
    ),
]


def seed_demo_data(apps, schema_editor):
    from django.contrib.auth.hashers import make_password

    User = apps.get_model("accounts", "User")
    Employee = apps.get_model("directory", "Employee")
    KnowledgeEntry = apps.get_model("knowledge", "KnowledgeEntry")

    users_by_email = {}
    for email, role, department, full_name in DEMO_USERS:
        user, _created = User.objects.get_or_create(
            email=email,
            defaults={
                "password": make_password(DEMO_PASSWORD),
                "full_name": full_name,
                "role": role,
                "department": department,
                "is_active": True,
            },
        )
        users_by_email[email] = user

    employees_by_name = {}
    for full_name, department, title, skills_summary, bio, user_email in EMPLOYEES:
        employee, _created = Employee.objects.get_or_create(
            full_name=full_name,
            defaults={
                "department": department,
                "title": title,
                "skills_summary": skills_summary,
                "bio": bio,
                "user": users_by_email.get(user_email) if user_email else None,
            },
        )
        employees_by_name[full_name] = employee

    entries = []
    for title, body, entry_type, author_name, visibility_departments in KNOWLEDGE_ENTRIES:
        entry, _created = KnowledgeEntry.objects.get_or_create(
            title=title,
            defaults={
                "body": body,
                "entry_type": entry_type,
                "author": employees_by_name[author_name],
                "visibility_departments": visibility_departments,
            },
        )
        entries.append(entry)

    _sync_seed_data_to_qdrant(employees_by_name.values(), entries)


def _sync_seed_data_to_qdrant(employees, entries):
    try:
        from apps.common import qdrant_store
        from apps.common.ai import get_embedding
    except Exception as exc:  # pragma: no cover - defensive only
        logger.warning("Qdrant sync skipped during seed migration: %s", exc)
        return

    try:
        for employee in employees:
            text = f"{employee.skills_summary} {employee.bio}".strip() or employee.full_name
            vector = get_embedding(text)
            qdrant_store.upsert_point(
                qdrant_store.EMPLOYEE_COLLECTION,
                employee.id,
                vector,
                {"department": employee.department},
            )
        for entry in entries:
            text = f"{entry.title} {entry.body}"
            vector = get_embedding(text)
            qdrant_store.upsert_point(
                qdrant_store.KNOWLEDGE_COLLECTION,
                entry.id,
                vector,
                {
                    "visibility_departments": entry.visibility_departments or [],
                    "entry_type": entry.entry_type,
                    "author_id": entry.author_id,
                },
            )
    except Exception as exc:
        logger.warning(
            "Qdrant sync during seed migration failed (%s); the Postgres-side demo data "
            "was still created. Run `python manage.py sync_vectors` once Qdrant is "
            "reachable to repair search.",
            exc,
        )


def remove_demo_data(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    Employee = apps.get_model("directory", "Employee")
    KnowledgeEntry = apps.get_model("knowledge", "KnowledgeEntry")

    KnowledgeEntry.objects.filter(title__in=[row[0] for row in KNOWLEDGE_ENTRIES]).delete()
    Employee.objects.filter(full_name__in=[row[0] for row in EMPLOYEES]).delete()
    User.objects.filter(email__in=[row[0] for row in DEMO_USERS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("knowledge", "0001_initial"),
        ("directory", "0001_initial"),
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_demo_data, remove_demo_data),
    ]
