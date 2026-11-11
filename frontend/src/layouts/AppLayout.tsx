import { NavLink, Outlet } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";

export function AppLayout() {
  const { user, logout } = useAuth();

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="app-header-title">Internal Expert &amp; Policy Finder</div>
        <nav className="app-nav">
          <NavLink to="/" end>
            Search
          </NavLink>
          <NavLink to="/knowledge-entries">Knowledge Entries</NavLink>
          <NavLink to="/employees">Directory</NavLink>
        </nav>
        <div className="app-header-user">
          <span>
            {user?.full_name || user?.email} <span className="role-badge">{user?.role}</span>
          </span>
          <button onClick={logout}>Log out</button>
        </div>
      </header>
      <main className="app-content">
        <Outlet />
      </main>
    </div>
  );
}
