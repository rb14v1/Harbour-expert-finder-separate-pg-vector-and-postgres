import { apiClient } from "./client";
import type { ExpertSearchResult, KnowledgeSearchResult } from "../types";

export function searchKnowledge(query: string, topK = 5) {
  return apiClient.get<KnowledgeSearchResult[]>("/search/knowledge/", {
    params: { q: query, top_k: topK },
  });
}

export function searchExperts(query: string, topK = 5) {
  return apiClient.get<ExpertSearchResult[]>("/search/experts/", {
    params: { q: query, top_k: topK },
  });
}
