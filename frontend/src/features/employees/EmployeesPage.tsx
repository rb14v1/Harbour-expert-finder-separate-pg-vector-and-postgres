import { useEffect, useState, type FormEvent } from "react";

import { createEmployee, deleteEmployee, listEmployees, updateEmployee } from "../../api/employees";
import { extractErrorMessage } from "../../api/client";
import { useAuth } from "../../auth/AuthContext";
import type { Employee } from "../../types";

export function EmployeesPage() {
  const { user } = useAuth();
  const isHRAdmin = user?.role === "hr_admin";

  const [employees, setEmployees] = useState<Employee[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [fullName, setFullName] = useState("");
  const [department, setDepartment] = useState("");
  const [title, setTitle] = useState("");
  const [skillsSummary, setSkillsSummary] = useState("");
  const [bio, setBio] = useState("");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [creating, setCreating] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  async function refresh() {
    setLoading(true);
    try {
      const response = await listEmployees();
      setEmployees(response.data.results);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  function canEdit(employee: Employee) {
    return isHRAdmin || employee.user_id === user?.id;
  }

  function startEdit(employee: Employee) {
    setCreating(false);
    setEditingId(employee.id);
    setFullName(employee.full_name);
    setDepartment(employee.department);
    setTitle(employee.title);
    setSkillsSummary(employee.skills_summary);
    setBio(employee.bio);
  }

  function startCreate() {
    setEditingId(null);
    setCreating(true);
    setFullName("");
    setDepartment("");
    setTitle("");
    setSkillsSummary("");
    setBio("");
  }

  function cancelForm() {
    setEditingId(null);
    setCreating(false);
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      if (editingId) {
        await updateEmployee(editingId, {
          full_name: fullName,
          department,
          title,
          skills_summary: skillsSummary,
          bio,
        });
      } else {
        await createEmployee({
          full_name: fullName,
          department,
          title,
          skills_summary: skillsSummary,
          bio,
        });
      }
      cancelForm();
      await refresh();
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(id: number) {
    if (!window.confirm("Delete this employee profile?")) return;
    setError(null);
    try {
      await deleteEmployee(id);
      await refresh();
    } catch (err) {
      setError(extractErrorMessage(err));
    }
  }

  const showForm = creating || editingId !== null;

  return (
    <div className="employees-page">
      <h1>Employee Directory</h1>
      <p className="hint">
        {isHRAdmin
          ? "As an HR admin you can create, edit or remove any profile."
          : "You can edit your own profile's title, skills and bio. Only HR admins can add or remove directory entries."}
      </p>

      {error && <div className="form-error">{error}</div>}

      {isHRAdmin && !showForm && (
        <button onClick={startCreate}>Add employee</button>
      )}

      {showForm && (
        <form className="entry-form" onSubmit={handleSubmit}>
          <h2>{editingId ? "Edit profile" : "Add employee"}</h2>
          <label>
            Full name
            <input
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              required
              disabled={!isHRAdmin && editingId !== null}
            />
          </label>
          <label>
            Department
            <input
              type="text"
              value={department}
              onChange={(e) => setDepartment(e.target.value)}
              required
              disabled={!isHRAdmin && editingId !== null}
            />
          </label>
          <label>
            Title
            <input type="text" value={title} onChange={(e) => setTitle(e.target.value)} />
          </label>
          <label>
            Skills summary
            <textarea
              value={skillsSummary}
              onChange={(e) => setSkillsSummary(e.target.value)}
              rows={2}
            />
          </label>
          <label>
            Bio
            <textarea value={bio} onChange={(e) => setBio(e.target.value)} rows={3} />
          </label>
          <div className="form-actions">
            <button type="submit" disabled={submitting}>
              {submitting ? "Saving..." : editingId ? "Save changes" : "Add employee"}
            </button>
            <button type="button" className="secondary" onClick={cancelForm}>
              Cancel
            </button>
          </div>
        </form>
      )}

      {loading ? (
        <p>Loading...</p>
      ) : (
        <ul className="entry-list">
          {employees.map((employee) => (
            <li key={employee.id} className="entry-card">
              <div className="entry-card-title">
                {employee.full_name} - {employee.title}
              </div>
              <div className="entry-card-meta">{employee.department}</div>
              <div className="entry-card-body">{employee.skills_summary}</div>
              {canEdit(employee) && (
                <div className="entry-card-actions">
                  <button className="secondary" onClick={() => startEdit(employee)}>
                    Edit
                  </button>
                  {isHRAdmin && (
                    <button className="danger" onClick={() => handleDelete(employee.id)}>
                      Delete
                    </button>
                  )}
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
