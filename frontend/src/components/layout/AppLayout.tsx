import React, { useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import {
  LayoutDashboard,
  ShieldCheck,
  Grid3X3,
  Layers,
  AlertTriangle,
  Flame,
  Wrench,
  FileText,
  FileSpreadsheet,
  Settings,
  LogOut,
  Menu,
  X,
  ShieldAlert,
  HardDrive,
  User as UserIcon,
} from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { WorkspaceSwitcher } from "./WorkspaceSwitcher";

interface NavItem {
  to: string;
  label: string;
  icon: React.ComponentType<{ size?: number; className?: string }>;
  end?: boolean;
}

const NAV_ITEMS: NavItem[] = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/controls", label: "Control Library", icon: ShieldCheck },
  { to: "/crosswalk", label: "Crosswalk Matrix", icon: Grid3X3 },
  { to: "/coverage", label: "Coverage Heatmap", icon: Layers },
  { to: "/risks", label: "Risk Register", icon: AlertTriangle },
  { to: "/risk-heatmap", label: "5×5 Heatmap", icon: Flame },
  { to: "/remediation", label: "Remediation", icon: Wrench },
  { to: "/evidence", label: "Evidence Library", icon: FileText },
  { to: "/import-export", label: "Import / Export", icon: FileSpreadsheet },
  { to: "/settings", label: "Settings", icon: Settings },
];

export function AppLayout() {
  const { user, currentWorkspace, google, logout } = useAuth();
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();

  const handleLogout = async () => {
    try {
      await logout();
      navigate("/login");
    } catch (err) {
      console.error("Failed to log out:", err);
    }
  };

  const currentNav = NAV_ITEMS.find((item) =>
    item.end ? location.pathname === item.to : location.pathname.startsWith(item.to)
  );

  return (
    <div className="app-container">
      {/* Mobile Top Header */}
      <header className="mobile-header">
        <button
          type="button"
          className="mobile-menu-btn"
          onClick={() => setMobileNavOpen((prev) => !prev)}
          aria-label={mobileNavOpen ? "Close menu" : "Open menu"}
        >
          {mobileNavOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
        <div className="mobile-brand">
          <span className="brand-dot" />
          <span className="mobile-brand-title">Meridian</span>
        </div>
      </header>

      {/* Backdrop for mobile */}
      {mobileNavOpen && (
        <div
          className="mobile-backdrop"
          onClick={() => setMobileNavOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Sidebar Navigation */}
      <aside className={`app-sidebar ${mobileNavOpen ? "mobile-open" : ""}`}>
        <div className="sidebar-brand">
          <div className="brand-badge">
            <ShieldCheck size={22} className="brand-icon" />
          </div>
          <div className="brand-text">
            <h1 className="brand-title">Meridian</h1>
            <span className="brand-subtitle">GRC Platform</span>
          </div>
        </div>

        <div className="sidebar-workspace">
          <WorkspaceSwitcher />
        </div>

        <nav className="sidebar-nav" aria-label="Main Navigation">
          <div className="nav-section-label">Core Views</div>
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  `sidebar-nav-item ${isActive ? "active" : ""}`
                }
                onClick={() => setMobileNavOpen(false)}
              >
                <Icon size={18} className="nav-item-icon" />
                <span className="nav-item-text">{item.label}</span>
              </NavLink>
            );
          })}
        </nav>

        <div className="sidebar-footer">
          {/* Google integration pill */}
          <div
            className={`google-status-pill ${
              google?.connected ? "connected" : "disconnected"
            }`}
            title={
              google?.connected
                ? `Google Drive connected (${google.granted_scopes.length} scopes)`
                : "Google Drive not connected"
            }
          >
            <HardDrive size={14} />
            <span className="google-status-text">
              {google?.connected ? "Drive Linked" : "Drive Disconnected"}
            </span>
            <span className="status-indicator-dot" />
          </div>

          {/* User profile and logout */}
          <div className="user-profile-section">
            <div className="user-profile-info">
              {user?.picture_url ? (
                <img
                  src={user.picture_url}
                  alt={user.name}
                  className="user-avatar"
                />
              ) : (
                <div className="user-avatar-fallback">
                  <UserIcon size={16} />
                </div>
              )}
              <div className="user-details">
                <span className="user-name">{user?.name || "User"}</span>
                <span className="user-email">{user?.email || ""}</span>
              </div>
            </div>
            <button
              type="button"
              className="logout-button"
              onClick={handleLogout}
              aria-label="Sign out"
              title="Sign out"
            >
              <LogOut size={16} />
            </button>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="app-main-wrapper">
        <header className="main-header">
          <div className="header-breadcrumbs">
            <span className="breadcrumb-root">Meridian</span>
            <span className="breadcrumb-separator">/</span>
            <span className="breadcrumb-current">
              {currentNav?.label || "Workspace"}
            </span>
          </div>
          {currentWorkspace && (
            <div className="header-workspace-tag">
              <span className="tag-label">Active Workspace:</span>
              <strong className="tag-name">{currentWorkspace.name}</strong>
            </div>
          )}
        </header>

        <main className="main-content">
          {!currentWorkspace && (
            <div className="no-workspace-banner" role="alert">
              <ShieldAlert size={20} className="banner-icon" />
              <div className="banner-content">
                <strong>No workspace selected</strong>
                <p>
                  You are not currently in an active workspace. Please choose an
                  existing workspace from the top switcher or create a new one to
                  view and manage your compliance items.
                </p>
              </div>
            </div>
          )}
          <Outlet />
        </main>
      </div>
    </div>
  );
}
