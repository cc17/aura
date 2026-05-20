import { useEffect, useRef, useState } from "react";
import type { Conversation } from "../types";
import { fetchConversations, deleteConversation } from "../services/api";
import logoUrl from "../assets/logo.svg";

const PLAN_LABELS: Record<string, string> = {
  free: "Free",
  pro: "Pro",
  max: "Max",
};

interface Props {
  isOpen: boolean;
  onToggle: () => void;
  currentConversationId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
  onMore: () => void;
  onDelete?: (id: string) => void;
  username: string;
  plan?: string;
  onProfile: () => void;
  onLogout: () => void;
  onUpgrade: () => void;
}

export function Sidebar({
  isOpen, onToggle, currentConversationId, onSelect, onNew, onMore, onDelete,
  username, plan = "free", onProfile, onLogout, onUpgrade,
}: Props) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchConversations()
      .then((data) => setConversations(data.conversations))
      .catch(console.error);
  }, [currentConversationId]);

  useEffect(() => {
    if (!menuOpen) return;
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [menuOpen]);

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    try {
      await deleteConversation(id);
      setConversations((prev) => prev.filter((c) => c.id !== id));
      if (id === currentConversationId) onDelete?.(id);
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <>
      {!isOpen && (
        <button className="sidebar-float-toggle" onClick={onToggle} title="Expand sidebar">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <rect x="2" y="3.5" width="12" height="1.2" rx="0.6" fill="currentColor"/>
            <rect x="2" y="7.4" width="8" height="1.2" rx="0.6" fill="currentColor"/>
            <rect x="2" y="11.3" width="10" height="1.2" rx="0.6" fill="currentColor"/>
          </svg>
        </button>
      )}

      <div className={`sidebar ${isOpen ? "sidebar-open" : ""}`}>
        <div className="sidebar-top">
          <span className="sidebar-brand">
            <img src={logoUrl} alt="Aura" className="sidebar-logo" />
            Aura
          </span>
          <button className="sidebar-collapse-btn" onClick={onToggle} title="Collapse sidebar">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M10 3L6 8L10 13" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </button>
        </div>

        <button className="sidebar-action-btn" onClick={onNew}>
          <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
            <path d="M7.5 2v11M2 7.5h11" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/>
          </svg>
          New Chat
        </button>

        <button className="sidebar-action-btn sidebar-action-btn--secondary">
          <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
            <rect x="2" y="2" width="11" height="11" rx="2" stroke="currentColor" strokeWidth="1.4"/>
            <path d="M5 5.5h5M5 7.5h5M5 9.5h3" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round"/>
          </svg>
          Knowledge
        </button>

        <button className="sidebar-action-btn sidebar-action-btn--secondary" onClick={onMore}>
          <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
            <circle cx="7.5" cy="7.5" r="1.2" fill="currentColor"/>
            <circle cx="2.5" cy="7.5" r="1.2" fill="currentColor"/>
            <circle cx="12.5" cy="7.5" r="1.2" fill="currentColor"/>
          </svg>
          More
        </button>

        <div className="sidebar-section-label">History</div>
        <div className="sidebar-list">
          {conversations.map((conv) => (
            <div
              key={conv.id}
              className={`sidebar-item ${conv.id === currentConversationId ? "active" : ""}`}
            >
              <button className="sidebar-item-title" onClick={() => onSelect(conv.id)}>
                {conv.title}
              </button>
              <button
                className="sidebar-item-delete"
                onClick={(e) => handleDelete(e, conv.id)}
                title="Delete"
              >
                &#215;
              </button>
            </div>
          ))}
          {conversations.length === 0 && (
            <p className="sidebar-empty">No conversations yet</p>
          )}
        </div>

        <div className="user-menu-wrap" ref={menuRef}>
          {menuOpen && (
            <div className="user-menu-popover">
              <button
                className="user-menu-item"
                onClick={() => { setMenuOpen(false); onProfile(); }}
              >
                <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
                  <circle cx="7.5" cy="5" r="2.5" stroke="currentColor" strokeWidth="1.3"/>
                  <path d="M2 13c0-2.5 2.5-4.5 5.5-4.5S13 10.5 13 13" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/>
                </svg>
                My Profile
              </button>
              {plan === "free" && (
                <>
                  <div className="user-menu-divider" />
                  <button
                    className="user-menu-item user-menu-item--upgrade"
                    onClick={() => { setMenuOpen(false); onUpgrade(); }}
                  >
                    <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
                      <path d="M7.5 2v8M4 7l3.5-4L11 7" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/>
                      <path d="M2 13h11" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/>
                    </svg>
                    Upgrade Plan
                  </button>
                </>
              )}
              <div className="user-menu-divider" />
              <button
                className="user-menu-item user-menu-item--danger"
                onClick={() => { setMenuOpen(false); onLogout(); }}
              >
                <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
                  <path d="M5.5 2H3a1 1 0 0 0-1 1v9a1 1 0 0 0 1 1h2.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/>
                  <path d="M10 10l3-2.5L10 5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/>
                  <path d="M13 7.5H6" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/>
                </svg>
                Sign out
              </button>
            </div>
          )}
          <button
            className={`user-menu-btn ${menuOpen ? "user-menu-btn--active" : ""}`}
            onClick={() => setMenuOpen((v) => !v)}
          >
            <span className="user-menu-avatar">
              {username.charAt(0).toUpperCase()}
            </span>
            <span className="user-menu-info">
              <span className="user-menu-name">{username}</span>
              <span className="user-menu-plan-label">
                <span className={`user-menu-plan-dot user-menu-plan-dot--${plan}`} />
                {PLAN_LABELS[plan] ?? plan} Plan
              </span>
            </span>
          </button>
        </div>
      </div>
    </>
  );
}
