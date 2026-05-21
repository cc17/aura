import { ChatWindow } from "./components/ChatWindow";
import { ChatInput } from "./components/ChatInput";
import { ModelSelector } from "./components/ModelSelector";
import { ToolIndicator } from "./components/ToolIndicator";
import { AgentIndicator } from "./components/AgentIndicator";
import { Sidebar } from "./components/Sidebar";
import { MoreView } from "./components/MoreView";
import { LoginPage } from "./components/LoginPage";
import { OnboardingModal } from "./components/OnboardingModal";
import { EmptyStateCards } from "./components/EmptyStateCards";
import { SkillPanel } from "./components/SkillPanel";
import { SuggestionsBar } from "./components/SuggestionsBar";
import { ProfilePage } from "./components/ProfilePage";
import { FeedbackButton } from "./components/FeedbackButton";
import { QuotaBanner } from "./components/QuotaBanner";
import { PricingModal } from "./components/PricingModal";
import { AdminPage } from "./components/AdminPage";
import { useChat } from "./hooks/useChat";
import { useModels } from "./hooks/useModels";
import { useAuth } from "./hooks/useAuth";
import { useQuota } from "./hooks/useQuota";
import { fetchConversation, fetchSkills, type SkillDef } from "./services/api";
import { useConversationRoute } from "./hooks/useConversationRoute";
import { useEffect, useMemo, useState, useCallback } from "react";

export default function App() {
  if (window.location.pathname === "/admin") return <AdminPage />;

  const { state, user, handleLogin, handleRegister, handleLogout, markOnboarded } = useAuth();
  const {
    messages,
    isStreaming,
    conversationId,
    activeToolCalls,
    activeAgent,
    pendingSkillKey,
    sendMessage,
    stopStreaming,
    newConversation,
    executeSkill,
    setPendingSkillKey,
    setMessages,
    setConversationId,
  } = useChat();
  const { models, selectedModel, setSelectedModel } = useModels();
  const { quota, refreshQuota } = useQuota(state === "authenticated");
  const [skillMap, setSkillMap] = useState<Record<string, SkillDef>>({});
  const [showProfile, setShowProfile] = useState(false);
  const [showPricing, setShowPricing] = useState(false);
  const [view, setView] = useState<"chat" | "more">("chat");
  const [sidebarOpen, setSidebarOpen] = useState<boolean>(
    () => localStorage.getItem("sidebar-collapsed") !== "true"
  );

  const toggleSidebar = useCallback(() => {
    setSidebarOpen((prev) => {
      const next = !prev;
      localStorage.setItem("sidebar-collapsed", next ? "false" : "true");
      return next;
    });
  }, []);

  // Track the last assistant message id for suggestion refresh
  const lastAssistantId = useMemo(() => {
    const assistantMsgs = messages.filter((m) => m.role === "assistant" && m.content);
    return assistantMsgs.length > 0 ? assistantMsgs[assistantMsgs.length - 1].id : null;
  }, [messages]);

  useEffect(() => {
    if (state === "authenticated") {
      fetchSkills()
        .then((skills) => {
          const map: Record<string, SkillDef> = {};
          skills.forEach((s) => { map[s.skill_key] = s; });
          setSkillMap(map);
        })
        .catch(() => {});
    }
  }, [state]);

  // Refresh quota after each completed stream
  useEffect(() => {
    if (!isStreaming && state === "authenticated") refreshQuota();
  }, [isStreaming, state, refreshQuota]);

  const loadConversation = useCallback(async (id: string) => {
    try {
      const data = await fetchConversation(id);
      setConversationId(id);
      setMessages(
        data.messages.map(
          (m: { role: string; content: string; timestamp: string }) => ({
            id: crypto.randomUUID(),
            role: m.role,
            content: m.content,
            timestamp: m.timestamp,
          }),
        ),
      );
    } catch (err) {
      console.error(err);
    }
  }, [setConversationId, setMessages]);

  const { navigate } = useConversationRoute({
    onLoad: (id) => { loadConversation(id); setView("chat"); },
  });

  // Loading state while checking token
  if (state === "loading") {
    return (
      <div className="app" style={{ alignItems: "center", justifyContent: "center" }}>
        <span style={{ color: "var(--text-sub)" }}>Loading…</span>
      </div>
    );
  }

  // Not logged in
  if (state === "unauthenticated") {
    return <LoginPage onLogin={handleLogin} onRegister={handleRegister} />;
  }

  const showOnboarding = user && !user.onboarded;

  const handleSend = (content: string, file?: File | null) => {
    sendMessage(content, selectedModel, file, refreshQuota);
  };

  const handleSelectConversation = (id: string) => {
    navigate(id);
    loadConversation(id);
  };

  return (
    <>
      <div className={`app ${sidebarOpen ? "" : "sidebar-collapsed"}`}>
        <Sidebar
          isOpen={sidebarOpen}
          onToggle={toggleSidebar}
          currentConversationId={conversationId}
          onSelect={(id) => { handleSelectConversation(id); setView("chat"); }}
          onNew={() => { newConversation(); navigate(null); setView("chat"); }}
          onMore={() => setView("more")}
          onDelete={newConversation}
          username={user?.username ?? ""}
          plan={quota?.plan ?? "free"}
          onProfile={() => setShowProfile(true)}
          onLogout={handleLogout}
          onUpgrade={() => setShowPricing(true)}
        />

        <div className="main-panel">
          {view === "more" ? (
            <MoreView onBack={() => setView("chat")} />
          ) : (
            <>
              <header className="top-bar">
                <div className="top-bar-title">Aura</div>
                <ModelSelector
                  models={models}
                  selectedModel={selectedModel}
                  onSelect={setSelectedModel}
                />
              </header>

              {messages.length === 0 && !pendingSkillKey ? (
                <div className="empty-state">
                  <div className="empty-state-greeting">
                    <div className="empty-state-avatar">A</div>
                    <h2 className="empty-state-title">Hello, {user?.username}</h2>
                    <p className="empty-state-sub">What can I help you with today?</p>
                  </div>
                  <EmptyStateCards
                    onSelectSkill={(skillKey) => setPendingSkillKey(skillKey)}
                    onSendMessage={(text) => sendMessage(text, selectedModel)}
                  />
                </div>
              ) : (
                <ChatWindow messages={messages} isStreaming={isStreaming} />
              )}

              <AgentIndicator activeAgent={activeAgent} />
              <ToolIndicator activeToolCalls={activeToolCalls} />

              {messages.length > 0 && !isStreaming && (
                <SuggestionsBar
                  refreshKey={lastAssistantId}
                  onSendQuestion={(text) => sendMessage(text, selectedModel)}
                  onOpenSkill={(skillKey) => setPendingSkillKey(skillKey)}
                />
              )}

              <div className="input-area">
                {pendingSkillKey && skillMap[pendingSkillKey] && (
                  <SkillPanel
                    skill={skillMap[pendingSkillKey]}
                    onSubmit={(skillKey, inputData) => {
                      const skill = skillMap[skillKey];
                      executeSkill(skillKey, inputData, skill?.scenario_name ?? skillKey, refreshQuota);
                    }}
                    onClose={() => setPendingSkillKey(null)}
                  />
                )}

                {quota?.plan === "free" && quota.remaining === 0 ? (
                  <QuotaBanner resetAt={quota.reset_at} plan={quota.plan} onUpgrade={() => setShowPricing(true)} />
                ) : (
                  <>
                    {quota?.plan === "free" && quota.remaining > 0 && quota.remaining <= 5 && (
                      <div className="quota-warning">
                        {quota.remaining} free conversations left today
                      </div>
                    )}
                    <ChatInput
                      onSend={handleSend}
                      isStreaming={isStreaming}
                      onStop={stopStreaming}
                    />
                  </>
                )}
              </div>
              <p className="chat-disclaimer">Aura can make mistakes. Verify important information.</p>
            </>
          )}
        </div>
      </div>

      {showOnboarding && <OnboardingModal onComplete={markOnboarded} />}
      {showProfile && <ProfilePage onClose={() => setShowProfile(false)} />}
      {showPricing && (
        <PricingModal
          currentPlan={quota?.plan ?? "free"}
          onClose={() => setShowPricing(false)}
        />
      )}
      <FeedbackButton />
    </>
  );
}
