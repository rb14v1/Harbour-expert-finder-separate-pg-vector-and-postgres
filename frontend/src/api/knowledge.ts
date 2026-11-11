import { apiClient } from "./client";
import type { KnowledgeEntry, Paginated } from "../types";

export function listKnowledgeEntries() {
  return apiClient.get<Paginated<KnowledgeEntry>>("/knowledge-entries/");
}

export function createKnowledgeEntry(data: {
  title: string;
  body: string;
  entry_type: "policy" | "qna";
  visibility_departments?: string[];
}) {
  return apiClient.post<KnowledgeEntry>("/knowledge-entries/", data);
}

export function updateKnowledgeEntry(
  id: number,
  data: Partial<{ title: string; body: string; entry_type: "policy" | "qna"; visibility_departments: string[] }>
) {
  return apiClient.patch<KnowledgeEntry>(`/knowledge-entries/${id}/`, data);
}

export function deleteKnowledgeEntry(id: number) {
  return apiClient.delete(`/knowledge-entries/${id}/`);
}
