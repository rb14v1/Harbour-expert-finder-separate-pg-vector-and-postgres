import { apiClient } from "./client";
import type { Employee, Paginated } from "../types";

export function listEmployees() {
  return apiClient.get<Paginated<Employee>>("/employees/");
}

export function updateEmployee(id: number, data: Partial<Pick<Employee, "title" | "skills_summary" | "bio" | "department" | "full_name">>) {
  return apiClient.patch<Employee>(`/employees/${id}/`, data);
}

export function createEmployee(data: { full_name: string; department: string; title?: string; skills_summary?: string; bio?: string; user_id?: number | null }) {
  return apiClient.post<Employee>("/employees/", data);
}

export function deleteEmployee(id: number) {
  return apiClient.delete(`/employees/${id}/`);
}
