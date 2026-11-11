export interface User {
  id: number;
  email: string;
  full_name: string;
  role: "employee" | "hr_admin";
  department: string;
  date_joined: string;
}

export interface Employee {
  id: number;
  user_id: number | null;
  user_email: string | null;
  full_name: string;
  department: string;
  title: string;
  skills_summary: string;
  bio: string;
  created_at: string;
  updated_at: string;
}

export interface KnowledgeEntry {
  id: number;
  title: string;
  body: string;
  entry_type: "policy" | "qna";
  author: number;
  author_name: string;
  author_department: string;
  visibility_departments: string[];
  created_at: string;
  updated_at: string;
}

export interface KnowledgeSearchResult {
  id: number;
  title: string;
  body: string;
  entry_type: "policy" | "qna";
  score: number;
  expert_contact: {
    id: number;
    name: string;
    department: string;
  };
}

export interface ExpertSearchResult {
  id: number;
  full_name: string;
  department: string;
  title: string;
  skills_summary: string;
  score: number;
}

export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}
