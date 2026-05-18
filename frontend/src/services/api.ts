const API_BASE = "/api";

// ---------------------------------------------------------------------------
// Auth token helpers
// ---------------------------------------------------------------------------

const TOKEN_KEY = "aura_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

function authHeaders(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  return fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { ...authHeaders(), ...(init.headers as Record<string, string> || {}) },
  });
}

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

export async function register(username: string, password: string) {
  const res = await apiFetch("/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "注册失败" }));
    throw new Error(err.detail || "注册失败");
  }
  return res.json();
}

export async function login(username: string, password: string) {
  const form = new URLSearchParams({ username, password });
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: form.toString(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "登录失败" }));
    throw new Error(err.detail || "登录失败");
  }
  return res.json();
}

export async function fetchMe() {
  const res = await apiFetch("/auth/me");
  if (!res.ok) throw new Error("Unauthorized");
  return res.json();
}

// ---------------------------------------------------------------------------
// Onboarding
// ---------------------------------------------------------------------------

export async function submitOnboarding(data: {
  industry: string;
  role: string;
  pain_points: string[];
  ai_proficiency: string;
}) {
  const res = await apiFetch("/onboarding", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Onboarding failed");
  return res.json();
}

// ---------------------------------------------------------------------------
// Profile
// ---------------------------------------------------------------------------

export async function fetchProfile() {
  const res = await apiFetch("/profile");
  if (!res.ok) throw new Error("Failed to fetch profile");
  return res.json();
}

export async function patchProfile(updates: Record<string, unknown>) {
  const res = await apiFetch("/profile", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ updates }),
  });
  if (!res.ok) throw new Error("Failed to update profile");
  return res.json();
}

// ---------------------------------------------------------------------------
// Memories
// ---------------------------------------------------------------------------

export async function fetchMemories() {
  const res = await apiFetch("/memories");
  if (!res.ok) return { memories: [] };
  return res.json() as Promise<{ memories: Array<{ id: number; content: string; category: string; importance: number; created_at: string }> }>;
}

export async function deleteMemory(id: number) {
  await apiFetch(`/memories/${id}`, { method: "DELETE" });
}

// ---------------------------------------------------------------------------
// Suggestions
// ---------------------------------------------------------------------------

export async function fetchLatestSuggestions() {
  const res = await apiFetch("/suggestions/latest");
  if (!res.ok) return { suggestions: [], message_id: null };
  return res.json() as Promise<{
    suggestions: Array<{ type: "question" | "skill"; text: string; skill_key: string | null }>;
    message_id: string | null;
  }>;
}

// ---------------------------------------------------------------------------
// Skills
// ---------------------------------------------------------------------------

export interface SkillDef {
  skill_key: string;
  scenario_name: string;
  tagline: string | null;
  description: string;
  industry: string | null;
  role: string | null;
  input_schema: { fields: Array<{ name: string; type: "text" | "textarea" | "url"; label: string; required: boolean }> };
}

export interface MarketSkill extends SkillDef {
  is_added: boolean;
}

export interface MySkill extends SkillDef {
  is_pinned: boolean;
  use_count: number;
}

export async function fetchSkills(): Promise<SkillDef[]> {
  const res = await apiFetch("/skills");
  if (!res.ok) return [];
  const data = await res.json();
  return data.skills as SkillDef[];
}

export async function fetchMarketSkills(): Promise<MarketSkill[]> {
  const res = await apiFetch("/skills/market");
  if (!res.ok) return [];
  const data = await res.json();
  return data.skills as MarketSkill[];
}

export async function fetchMySkills(): Promise<MySkill[]> {
  const res = await apiFetch("/skills/my");
  if (!res.ok) return [];
  const data = await res.json();
  return data.skills as MySkill[];
}

export async function addSkill(skillKey: string): Promise<void> {
  await apiFetch(`/skills/${skillKey}/add`, { method: "POST" });
}

export async function removeSkill(skillKey: string): Promise<void> {
  await apiFetch(`/skills/${skillKey}/remove`, { method: "DELETE" });
}

export async function pinSkill(skillKey: string, pinned: boolean): Promise<{ ok: boolean }> {
  const res = await apiFetch(`/skills/${skillKey}/pin`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pinned }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "操作失败" }));
    throw new Error(err.detail || "操作失败");
  }
  return res.json();
}

export function executeSkillSSE(
  skillKey: string,
  inputData: Record<string, string>,
  onChunk: (text: string) => void,
  onDone: () => void,
  onError: (err: string) => void,
  options?: {
    conversationId?: string | null;
    userMessage?: string;
    onConversationId?: (id: string) => void;
    onQuotaExceeded?: () => void;
  },
): AbortController {
  const controller = new AbortController();

  fetch(`${API_BASE}/skills/${skillKey}/execute`, {
    method: "POST",
    headers: { ...authHeaders(), "Content-Type": "application/json" },
    body: JSON.stringify({
      input_data: inputData,
      conversation_id: options?.conversationId ?? null,
      user_message: options?.userMessage ?? null,
    }),
    signal: controller.signal,
  })
    .then(async (res) => {
      if (!res.ok) {
        if (res.status === 402) options?.onQuotaExceeded?.();
        onError(`HTTP ${res.status}`);
        return;
      }
      const reader = res.body?.getReader();
      if (!reader) { onError("No response body"); return; }

      const decoder = new TextDecoder();
      let buffer = "";
      let currentEvent = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("event:")) {
            currentEvent = line.slice(6).trim();
          } else if (line.startsWith("data:")) {
            try {
              const data = JSON.parse(line.slice(5).trim());
              if (currentEvent === "conversation_id" && options?.onConversationId) {
                options.onConversationId(data.conversation_id as string);
              }
              if (currentEvent === "text_delta") onChunk(data.text || "");
              if (currentEvent === "done") { onDone(); return; }
              if (currentEvent === "error") onError(data.message || "error");
            } catch { /* skip */ }
          }
        }
      }
      onDone();
    })
    .catch((err) => { if (err.name !== "AbortError") onError(err.message); });

  return controller;
}

// ---------------------------------------------------------------------------
// Existing endpoints
// ---------------------------------------------------------------------------

export async function fetchModels() {
  const res = await apiFetch("/models");
  if (!res.ok) throw new Error("Failed to fetch models");
  return res.json();
}

export async function fetchTools() {
  const res = await apiFetch("/tools");
  if (!res.ok) throw new Error("Failed to fetch tools");
  return res.json();
}

export async function fetchConversations() {
  const res = await apiFetch("/conversations");
  if (!res.ok) throw new Error("Failed to fetch conversations");
  return res.json();
}

export async function deleteConversation(id: string) {
  const res = await apiFetch(`/conversations/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to delete conversation");
  return res.json();
}

export async function fetchConversation(id: string) {
  const res = await apiFetch(`/conversations/${id}`);
  if (!res.ok) throw new Error("Failed to fetch conversation");
  return res.json();
}

export function chatSSE(
  message: string,
  model: string | null,
  conversationId: string | null,
  onEvent: (event: string, data: Record<string, unknown>) => void,
  onDone: () => void,
  onError: (error: string) => void,
  file?: File | null,
  onQuotaExceeded?: () => void,
): AbortController {
  const controller = new AbortController();

  const formData = new FormData();
  formData.append("message", message);
  if (model) formData.append("model", model);
  if (conversationId) formData.append("conversation_id", conversationId);
  if (file) formData.append("file", file);

  fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: authHeaders(),
    body: formData,
    signal: controller.signal,
  })
    .then(async (res) => {
      if (!res.ok) {
        if (res.status === 402) onQuotaExceeded?.();
        onError(`HTTP ${res.status}`);
        return;
      }

      const reader = res.body?.getReader();
      if (!reader) {
        onError("No response body");
        return;
      }

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        let currentEvent = "";
        for (const line of lines) {
          if (line.startsWith("event:")) {
            currentEvent = line.slice(6).trim();
          } else if (line.startsWith("data:")) {
            const dataStr = line.slice(5).trim();
            if (dataStr) {
              try {
                const data = JSON.parse(dataStr);
                onEvent(currentEvent, data);
                if (currentEvent === "done") {
                  onDone();
                  return;
                }
              } catch {
                // skip malformed JSON
              }
            }
          }
        }
      }
      onDone();
    })
    .catch((err) => {
      if (err.name !== "AbortError") {
        onError(err.message);
      }
    });

  return controller;
}
