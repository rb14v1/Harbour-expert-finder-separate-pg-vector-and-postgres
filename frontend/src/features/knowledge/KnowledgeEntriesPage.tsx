import { useEffect, useState, type FormEvent } from "react";

import { extractErrorMessage } from "../../api/client";
import {
  createKnowledgeEntry,
  deleteKnowledgeEntry,
  listKnowledgeEntries,
  updateKnowledgeEntry,
} from "../../api/knowledge";
import { useAuth } from "../../auth/AuthContext";
import type { KnowledgeEntry } from "../../types";

export function KnowledgeEntriesPage() {
  const { user } = useAuth();
  const isHRAdmin = user?.role === "hr_admin";

  const [entries, setEntries] = useState<KnowledgeEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [entryType, setEntryType] = useState<"policy" | "qna">("qna");
  const [visibilityDepartments, setVisibilityDepartments] = useState("");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function refresh() {
    setLoading(true);
    try {
      const response = await listKnowledgeEntries();
      setEntries(response.data.results);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  function startEdit(entry: KnowledgeEntry) {
    setEditingId(entry.id);
    setTitle(entry.title);
    setBody(entry.body);
    setEntryType(entry.entry_type);
    setVisibilityDepartments(entry.visibility_departments.join(", "));
  }

  function cancelEdit() {
    setEditingId(null);
    setTitle("");
    setBody("");
    setEntryType("qna");
    setVisibilityDepartments("");
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    const departments = visibilityDepartments
      .split(",")
      .map((d) => d.trim())
      .filter(Boolean);
    try {
      if (editingId) {
        await updateKnowledgeEntry(editingId, {
          title,
          body,
          entry_type: entryType,
          visibility_departments: departments,
        });
      } else {
        await createKnowledgeEntry({
          title,
          body,
          entry_type: entryType,
          visibility_departments: departments,
        });
      }
      cancelEdit();
      await refresh();
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(id: number) {
    if (!window.confirm("Delete this knowledge entry?")) return;
    setError(null);
    try {
      await deleteKnowledgeEntry(id);
      await refresh();
    } catch (err) {
      setError(extractErrorMessage(err));
    }
  }

  return (
    <div className="knowledge-page">
      <h1>Knowledge Entries</h1>
      <p className="hint">
        {isHRAdmin
          ? "As an HR admin you can create or edit any entry, including policies restricted to specific departments."
          : "You can create or edit public Q&A entries. Only HR admins can create policy entries or restrict visibility to specific departments."}
      </p>

      {error && <div className="form-error">{error}</div>}

      <form className="entry-form" onSubmit={handleSubmit}>
        <h2>{editingId ? "Edit entry" : "Add entry"}</h2>
        <label>
          Title
          <input type="text" value={title} onChange={(e) => setTitle(e.target.value)} required />
        </label>
        <label>
          Body
          <textarea value={body} onChange={(e) => setBody(e.target.value)} required rows={4} />
        </label>
        <label>
          Entry type
          <select
            value={entryType}
            onChange={(e) => setEntryType(e.target.value as "policy" | "qna")}
            disabled={!isHRAdmin}
          >
            <option value="qna">Q&amp;A</option>
            <option value="policy">Policy</option>
          </select>
        </label>
        <label>
          Visibility departments (comma-separated, blank = public)
          <input
            type="text"
            value={visibilityDepartments}
            onChange={(e) => setVisibilityDepartments(e.target.value)}
            placeholder="e.g. Engineering, Finance"
            disabled={!isHRAdmin}
          />
        </label>
        <div className="form-actions">
          <button type="submit" disabled={submitting}>
            {submitting ? "Saving..." : editingId ? "Save changes" : "Add entry"}
          </button>
          {editingId && (
            <button type="button" className="secondary" onClick={cancelEdit}>
              Cancel
            </button>
          )}
        </div>
      </form>

      {loading ? (
        <p>Loading...</p>
      ) : entries.length === 0 ? (
        <p>No knowledge entries visible to you yet.</p>
      ) : (
        <ul className="entry-list">
          {entries.map((entry) => (
            <li key={entry.id} className="entry-card">
              <div className="entry-card-title">
                {entry.title} <span className="entry-type-badge">{entry.entry_type}</span>
                {entry.visibility_departments.length > 0 && (
                  <span className="visibility-badge">
                    {entry.visibility_departments.join(", ")} only
                  </span>
                )}
              </div>
              <div className="entry-card-body">{entry.body}</div>
              <div className="entry-card-meta">
                By {entry.author_name} ({entry.author_department})
              </div>
              <div className="entry-card-actions">
                <button className="secondary" onClick={() => startEdit(entry)}>
                  Edit
                </button>
                <button className="danger" onClick={() => handleDelete(entry.id)}>
                  Delete
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
