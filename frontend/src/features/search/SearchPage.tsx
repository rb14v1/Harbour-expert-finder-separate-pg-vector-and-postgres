import { useState, type FormEvent } from "react";

import { searchExperts, searchKnowledge } from "../../api/search";
import { extractErrorMessage } from "../../api/client";
import type { ExpertSearchResult, KnowledgeSearchResult } from "../../types";

type Mode = "knowledge" | "experts";

export function SearchPage() {
  const [mode, setMode] = useState<Mode>("knowledge");
  const [query, setQuery] = useState("");
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [knowledgeResults, setKnowledgeResults] = useState<KnowledgeSearchResult[] | null>(null);
  const [expertResults, setExpertResults] = useState<ExpertSearchResult[] | null>(null);

  async function handleSearch(e: FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    setError(null);
    setSearching(true);
    try {
      if (mode === "knowledge") {
        const response = await searchKnowledge(query);
        setKnowledgeResults(response.data);
        setExpertResults(null);
      } else {
        const response = await searchExperts(query);
        setExpertResults(response.data);
        setKnowledgeResults(null);
      }
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setSearching(false);
    }
  }

  return (
    <div className="search-page">
      <h1>Find a policy answer or an expert</h1>
      <p className="hint">
        Search the internal knowledge base for policies and Q&amp;As, or search the
        employee directory for people whose skills best match your question.
      </p>

      <div className="search-mode-toggle">
        <button
          type="button"
          className={mode === "knowledge" ? "" : "secondary"}
          onClick={() => setMode("knowledge")}
        >
          Knowledge base
        </button>
        <button
          type="button"
          className={mode === "experts" ? "" : "secondary"}
          onClick={() => setMode("experts")}
        >
          Find an expert
        </button>
      </div>

      <form className="search-form" onSubmit={handleSearch}>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={
            mode === "knowledge"
              ? "e.g. What's the remote work policy?"
              : "e.g. Who knows about Kubernetes security?"
          }
          required
        />
        <button type="submit" disabled={searching}>
          {searching ? "Searching..." : "Search"}
        </button>
      </form>

      {error && <div className="form-error">{error}</div>}

      {mode === "knowledge" && knowledgeResults && (
        <ul className="result-list">
          {knowledgeResults.length === 0 && <p>No matching knowledge entries found.</p>}
          {knowledgeResults.map((result) => (
            <li key={result.id} className="result-card">
              <div className="result-score">score: {result.score.toFixed(3)}</div>
              <div className="result-title">
                {result.title} <span className="entry-type-badge">{result.entry_type}</span>
              </div>
              <div className="result-body">{result.body}</div>
              <div className="result-contact">
                Expert to contact: <strong>{result.expert_contact.name}</strong> (
                {result.expert_contact.department})
              </div>
            </li>
          ))}
        </ul>
      )}

      {mode === "experts" && expertResults && (
        <ul className="result-list">
          {expertResults.length === 0 && <p>No matching experts found.</p>}
          {expertResults.map((result) => (
            <li key={result.id} className="result-card">
              <div className="result-score">score: {result.score.toFixed(3)}</div>
              <div className="result-title">
                {result.full_name} - {result.title}
              </div>
              <div className="result-meta">{result.department}</div>
              <div className="result-body">{result.skills_summary}</div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
