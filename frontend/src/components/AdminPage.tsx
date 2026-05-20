import { useEffect, useState } from "react";

const ADMIN_TOKEN_KEY = "aura_admin_token";
const API_BASE = "/api";

interface DashboardData {
  users: {
    total: number;
    dau: number;
    new_today: number;
    new_this_week: number;
    plan_distribution: Record<string, number>;
  };
  activity: {
    conversations_today: number;
    messages_today: number;
  };
  skills: {
    total: number;
    agents: number;
    top10_30d: Array<{ skill_key: string; name: string; clicked: number; completed: number; abandoned: number }>;
  top_agents_30d: Array<{ agent_key: string; clicked: number; used: number }>;
    funnel_30d: Record<string, number>;
    exec_success_rate_pct: number | null;
  };
  errors: {
    recent: string[];
  };
}

async function fetchDashboard(token: string): Promise<DashboardData> {
  const res = await fetch(`${API_BASE}/admin/dashboard`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (res.status === 403) throw new Error("Invalid token");
  if (!res.ok) throw new Error(`Server error: ${res.status}`);
  return res.json();
}

function StatCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="admin-card">
      <div className="admin-card-value">{value}</div>
      <div className="admin-card-label">{label}</div>
      {sub && <div className="admin-card-sub">{sub}</div>}
    </div>
  );
}

export function AdminPage() {
  const [token, setToken] = useState(() => localStorage.getItem(ADMIN_TOKEN_KEY) ?? "");
  const [input, setInput] = useState("");
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);

  useEffect(() => {
    document.body.style.overflow = "auto";
    return () => { document.body.style.overflow = ""; };
  }, []);

  const load = async (t: string) => {
    setLoading(true);
    setError("");
    try {
      const d = await fetchDashboard(t);
      setData(d);
      setLastRefresh(new Date());
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Unknown error");
      if (e instanceof Error && e.message === "Invalid token") {
        localStorage.removeItem(ADMIN_TOKEN_KEY);
        setToken("");
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (token) load(token);
  }, [token]);

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;
    localStorage.setItem(ADMIN_TOKEN_KEY, input.trim());
    setToken(input.trim());
  };

  if (!token) {
    return (
      <div className="admin-login-wrap">
        <div className="admin-login-box">
          <div className="admin-login-logo">⚙️</div>
          <h2 className="admin-login-title">Aura Admin</h2>
          <form onSubmit={handleLogin} className="admin-login-form">
            <input
              className="admin-login-input"
              type="password"
              placeholder="Enter admin token"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              autoFocus
            />
            <button className="admin-login-btn" type="submit">Enter Dashboard</button>
          </form>
          {error && <p className="admin-login-error">{error}</p>}
        </div>
      </div>
    );
  }

  return (
    <div className="admin-wrap">
      <header className="admin-header">
        <h1 className="admin-title">Aura Admin</h1>
        <div className="admin-header-right">
          {lastRefresh && (
            <span className="admin-refresh-time">
              Updated {lastRefresh.toLocaleTimeString("en-US")}
            </span>
          )}
          <button className="admin-btn-sm" onClick={() => load(token)} disabled={loading}>
            {loading ? "Loading…" : "Refresh"}
          </button>
          <button
            className="admin-btn-sm admin-btn-sm--danger"
            onClick={() => { localStorage.removeItem(ADMIN_TOKEN_KEY); setToken(""); setData(null); }}
          >
            Sign out
          </button>
        </div>
      </header>

      {error && <div className="admin-error-banner">{error}</div>}

      {data && (
        <div className="admin-content">
          {/* Users */}
          <section className="admin-section">
            <h2 className="admin-section-title">Users</h2>
            <div className="admin-cards">
              <StatCard label="Registered" value={data.users.total} />
              <StatCard label="DAU" value={data.users.dau} />
              <StatCard label="New today" value={data.users.new_today} />
              <StatCard label="New this week" value={data.users.new_this_week} />
            </div>
            <div className="admin-plan-dist">
              {Object.entries(data.users.plan_distribution).map(([plan, cnt]) => (
                <span key={plan} className={`admin-plan-badge admin-plan-badge--${plan}`}>
                  {plan.toUpperCase()} {cnt}
                </span>
              ))}
            </div>
          </section>

          {/* Activity */}
          <section className="admin-section">
            <h2 className="admin-section-title">Today's Activity</h2>
            <div className="admin-cards">
              <StatCard label="New conversations" value={data.activity.conversations_today} />
              <StatCard label="User messages" value={data.activity.messages_today} />
            </div>
          </section>

          {/* Skills */}
          <section className="admin-section">
            <h2 className="admin-section-title">Skills & Agents</h2>
            <div className="admin-cards">
              <StatCard label="Total skills" value={data.skills.total} />
              <StatCard label="Agents" value={data.skills.agents} />
              {data.skills.exec_success_rate_pct !== null && (
                <StatCard
                  label="Exec success rate"
                  value={`${data.skills.exec_success_rate_pct}%`}
                />
              )}
            </div>

            {/* Funnel */}
            <div className="admin-funnel">
              <h3 className="admin-funnel-title">Signal Funnel (last 30 days)</h3>
              <div className="admin-funnel-items">
                {["impressioned", "clicked", "started", "completed", "abandoned"].map((sig) => (
                  <div key={sig} className="admin-funnel-item">
                    <span className="admin-funnel-label">{sig}</span>
                    <span className="admin-funnel-val">{data.skills.funnel_30d[sig] ?? 0}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Top skills */}
            {data.skills.top10_30d.length > 0 && (
              <div className="admin-table-wrap">
                <h3 className="admin-funnel-title">Top Skills (last 30 days)</h3>
                <table className="admin-table">
                  <thead>
                    <tr>
                      <th>Skill</th>
                      <th>Clicked</th>
                      <th>Completed</th>
                      <th>Abandoned</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.skills.top10_30d.map((row) => (
                      <tr key={row.skill_key}>
                        <td>{row.name}</td>
                        <td>{row.clicked}</td>
                        <td>{row.completed}</td>
                        <td>{row.abandoned}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {data.skills.top_agents_30d.length > 0 && (
              <div className="admin-table-wrap">
                <h3 className="admin-funnel-title">Top Agents (last 30 days)</h3>
                <table className="admin-table">
                  <thead>
                    <tr>
                      <th>Agent</th>
                      <th>Clicked</th>
                      <th>Invoked</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.skills.top_agents_30d.map((row) => (
                      <tr key={row.agent_key}>
                        <td>{row.agent_key}</td>
                        <td>{row.clicked}</td>
                        <td>{row.used}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          {/* Errors */}
          <section className="admin-section">
            <h2 className="admin-section-title">Recent Errors (last 20)</h2>
            {data.errors.recent.length === 0 ? (
              <p className="admin-no-errors">No errors ✓</p>
            ) : (
              <div className="admin-error-log">
                {data.errors.recent.map((line, i) => (
                  <div key={i} className="admin-error-line">{line}</div>
                ))}
              </div>
            )}
          </section>
        </div>
      )}
    </div>
  );
}
