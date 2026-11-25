import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../auth";
import { Icon } from "./Icon";

export default function Layout() {
  const { user, logout } = useAuth();

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="logo">snip<span>.</span></div>
        <nav>
          <NavLink to="/" end className="nav-item">
            <Icon name="grid" /> Dashboard
          </NavLink>
          <NavLink to="/links" className="nav-item">
            <Icon name="link" /> Links
          </NavLink>
        </nav>
        <div className="sidebar-foot">
          <div className="who" title={user.email}>{user.email}</div>
          <button className="nav-item as-button" onClick={logout}>
            <Icon name="logout" /> Log out
          </button>
        </div>
      </aside>
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}
