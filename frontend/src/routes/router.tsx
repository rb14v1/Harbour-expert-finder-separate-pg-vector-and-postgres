import { createBrowserRouter, Navigate } from "react-router-dom";

import { ProtectedRoute } from "../auth/ProtectedRoute";
import { EmployeesPage } from "../features/employees/EmployeesPage";
import { KnowledgeEntriesPage } from "../features/knowledge/KnowledgeEntriesPage";
import { SearchPage } from "../features/search/SearchPage";
import { AppLayout } from "../layouts/AppLayout";
import { LoginPage } from "../pages/LoginPage";

export const router = createBrowserRouter([
  { path: "/login", element: <LoginPage /> },
  {
    element: <ProtectedRoute />,
    children: [
      {
        element: <AppLayout />,
        children: [
          { path: "/", element: <SearchPage /> },
          { path: "/knowledge-entries", element: <KnowledgeEntriesPage /> },
          { path: "/employees", element: <EmployeesPage /> },
        ],
      },
    ],
  },
  { path: "*", element: <Navigate to="/" replace /> },
]);
