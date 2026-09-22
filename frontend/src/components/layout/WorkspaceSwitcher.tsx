import React, { useState, useRef, useEffect } from "react";
import { Building2, ChevronDown, Check, Plus, Loader2 } from "lucide-react";
import { useAuth } from "../../context/AuthContext";

export function WorkspaceSwitcher() {
  const { workspaces, currentWorkspace, currentRole, switchWorkspace, createWorkspace } =
    useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const [isSwitching, setIsSwitching] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [newWorkspaceName, setNewWorkspaceName] = useState("");
  const [createError, setCreateError] = useState<string | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
        setIsCreating(false);
        setCreateError(null);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleSwitch = async (workspaceId: string) => {
    if (workspaceId === currentWorkspace?.id) {
      setIsOpen(false);
      return;
    }
    try {
      setIsSwitching(true);
      await switchWorkspace(workspaceId);
      setIsOpen(false);
    } catch (err: any) {
      console.error("Failed to switch workspace:", err);
    } finally {
      setIsSwitching(false);
    }
  };

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = newWorkspaceName.trim();
    if (!trimmed) {
      setCreateError("Workspace name is required");
      return;
    }
    try {
      setIsSwitching(true);
      setCreateError(null);
      await createWorkspace(trimmed);
      setNewWorkspaceName("");
      setIsCreating(false);
      setIsOpen(false);
    } catch (err: any) {
      setCreateError(err.message || "Failed to create workspace");
    } finally {
      setIsSwitching(false);
    }
  };

  return (
    <div className="workspace-switcher" ref={dropdownRef}>
      <button
        type="button"
        className="workspace-trigger"
        onClick={() => setIsOpen((prev) => !prev)}
        aria-expanded={isOpen}
        aria-haspopup="listbox"
        aria-label="Switch workspace"
      >
        <div className="workspace-trigger-icon">
          <Building2 size={18} />
        </div>
        <div className="workspace-trigger-info">
          <span className="workspace-trigger-label">Workspace</span>
          <span className="workspace-trigger-name">
            {currentWorkspace ? currentWorkspace.name : "Select Workspace"}
          </span>
        </div>
        {currentRole && <span className="role-badge">{currentRole}</span>}
        <ChevronDown size={14} className={`chevron-icon ${isOpen ? "open" : ""}`} />
      </button>

      {isOpen && (
        <div className="workspace-dropdown" role="listbox">
          <div className="workspace-dropdown-header">
            <span>Your Workspaces</span>
            {isSwitching && <Loader2 size={14} className="spin-animate" />}
          </div>

          <div className="workspace-list">
            {workspaces.map((m) => {
              const isActive = m.workspace.id === currentWorkspace?.id;
              return (
                <button
                  key={m.workspace.id}
                  type="button"
                  role="option"
                  aria-selected={isActive}
                  className={`workspace-item ${isActive ? "active" : ""}`}
                  onClick={() => handleSwitch(m.workspace.id)}
                  disabled={isSwitching}
                >
                  <div className="workspace-item-details">
                    <span className="workspace-item-name">{m.workspace.name}</span>
                    <span className="workspace-item-role">{m.role}</span>
                  </div>
                  {isActive && <Check size={16} className="active-check" />}
                </button>
              );
            })}
          </div>

          <div className="workspace-dropdown-footer">
            {!isCreating ? (
              <button
                type="button"
                className="create-workspace-btn"
                onClick={() => setIsCreating(true)}
              >
                <Plus size={15} />
                <span>Create new workspace</span>
              </button>
            ) : (
              <form onSubmit={handleCreateSubmit} className="create-workspace-form">
                <input
                  type="text"
                  placeholder="Workspace name..."
                  value={newWorkspaceName}
                  onChange={(e) => setNewWorkspaceName(e.target.value)}
                  autoFocus
                  disabled={isSwitching}
                  className="workspace-input"
                />
                {createError && <p className="workspace-create-error">{createError}</p>}
                <div className="create-form-actions">
                  <button
                    type="button"
                    className="cancel-btn"
                    onClick={() => {
                      setIsCreating(false);
                      setCreateError(null);
                    }}
                    disabled={isSwitching}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="save-btn"
                    disabled={isSwitching || !newWorkspaceName.trim()}
                  >
                    {isSwitching ? "Creating..." : "Create"}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
