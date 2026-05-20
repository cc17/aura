import { useCallback, useRef, useState } from "react";
import type { FileAttachment, Message, ToolCallInfo, ToolResultInfo } from "../types";
import { chatSSE, executeSkillSSE } from "../services/api";

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [activeToolCalls, setActiveToolCalls] = useState<ToolCallInfo[]>([]);
  const [activeAgent, setActiveAgent] = useState<string | null>(null);
  // skill_match: emitted by backend when intent routes to a skill
  const [pendingSkillKey, setPendingSkillKey] = useState<string | null>(null);
  const controllerRef = useRef<AbortController | null>(null);
  const generationRef = useRef(0);

  const sendMessage = useCallback(
    (content: string, model: string | null, file?: File | null, onQuotaExceeded?: () => void) => {
      const attachment: FileAttachment | undefined = file
        ? { name: file.name, size: file.size }
        : undefined;

      const userMsg: Message = {
        id: crypto.randomUUID(),
        role: "user",
        content,
        attachment,
        timestamp: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, userMsg]);
      setIsStreaming(true);
      setActiveToolCalls([]);

      // Capture generation number before creating callbacks.
      // If stopStreaming() or another sendMessage() runs first, generationRef
      // will have advanced and all callbacks below will no-op.
      const myGeneration = ++generationRef.current;
      const isCurrentGen = () => generationRef.current === myGeneration;

      // Placeholder for assistant response
      const assistantId = crypto.randomUUID();
      const assistantMsg: Message = {
        id: assistantId,
        role: "assistant",
        content: "",
        toolCalls: [],
        toolResults: [],
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMsg]);

      controllerRef.current = chatSSE(
        content,
        model,
        conversationId,
        (event, data) => {
          if (!isCurrentGen()) return; // stale callback — a newer request has started

          switch (event) {
            case "conversation_id":
              setConversationId(data.conversation_id as string);
              break;

            case "text_delta":
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId
                    ? { ...m, content: m.content + (data.text as string) }
                    : m,
                ),
              );
              break;

            case "tool_call": {
              const tc: ToolCallInfo = {
                toolCallId: data.tool_call_id as string,
                name: data.name as string,
                arguments: data.arguments as Record<string, unknown>,
              };
              setActiveToolCalls((prev) => [...prev, tc]);
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId
                    ? { ...m, toolCalls: [...(m.toolCalls || []), tc] }
                    : m,
                ),
              );
              break;
            }

            case "tool_result": {
              const tr: ToolResultInfo = {
                toolCallId: data.tool_call_id as string,
                name: data.name as string,
                result: data.result as string,
              };
              setActiveToolCalls((prev) =>
                prev.filter((tc) => tc.toolCallId !== tr.toolCallId),
              );
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId
                    ? { ...m, toolResults: [...(m.toolResults || []), tr] }
                    : m,
                ),
              );
              break;
            }

            case "agent_start":
              setActiveAgent(data.agent as string);
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId
                    ? { ...m, agentName: data.agent as string }
                    : m,
                ),
              );
              break;

            case "agent_end":
              setActiveAgent(null);
              break;

            case "thinking":
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId
                    ? {
                        ...m,
                        thinkingSteps: [...(m.thinkingSteps || []), data.text as string],
                      }
                    : m,
                ),
              );
              break;

            case "skill_match":
              // Backend detected a skill intent; open the skill panel
              setPendingSkillKey(data.skill_key as string);
              // Remove the empty placeholder assistant message
              setMessages((prev) => prev.filter((m) => m.id !== assistantId));
              break;

            case "error":
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === assistantId
                    ? {
                        ...m,
                        content:
                          m.content +
                          `\n\n**Error:** ${data.message as string}`,
                      }
                    : m,
                ),
              );
              break;
          }
        },
        () => {
          if (!isCurrentGen()) return;
          setIsStreaming(false);
          setActiveToolCalls([]);
          setActiveAgent(null);
        },
        (error) => {
          if (!isCurrentGen()) return;
          setIsStreaming(false);
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId
                ? { ...m, content: m.content + `\n\n**Error:** ${error}` }
                : m,
            ),
          );
        },
        file,
        onQuotaExceeded,
      );
    },
    [conversationId],
  );

  const stopStreaming = useCallback(() => {
    generationRef.current++; // invalidate any in-flight callbacks immediately
    controllerRef.current?.abort();
    setIsStreaming(false);
  }, []);

  const newConversation = useCallback(() => {
    setMessages([]);
    setConversationId(null);
    setActiveToolCalls([]);
    setActiveAgent(null);
    setPendingSkillKey(null);
  }, []);

  const executeSkill = useCallback(
    (skillKey: string, inputData: Record<string, string>, scenarioName: string, onQuotaExceeded?: () => void) => {
      setPendingSkillKey(null);

      const userContent = `[Skill: ${scenarioName}]\n${Object.entries(inputData)
        .filter(([, v]) => v)
        .map(([k, v]) => `${k}: ${v.slice(0, 60)}${v.length > 60 ? "…" : ""}`)
        .join("\n")}`;

      const userMsg: Message = {
        id: crypto.randomUUID(),
        role: "user",
        content: userContent,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMsg]);
      setIsStreaming(true);

      const myGeneration = ++generationRef.current;
      const isCurrentGen = () => generationRef.current === myGeneration;

      const assistantId = crypto.randomUUID();
      setMessages((prev) => [
        ...prev,
        { id: assistantId, role: "assistant", content: "", timestamp: new Date().toISOString() },
      ]);

      controllerRef.current = executeSkillSSE(
        skillKey,
        inputData,
        (text) => {
          if (!isCurrentGen()) return;
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId ? { ...m, content: m.content + text } : m,
            ),
          );
        },
        () => {
          if (!isCurrentGen()) return;
          setIsStreaming(false);
        },
        (err) => {
          if (!isCurrentGen()) return;
          setIsStreaming(false);
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId
                ? { ...m, content: m.content + `\n\n**Error:** ${err}` }
                : m,
            ),
          );
        },
        {
          conversationId,
          userMessage: userContent,
          onConversationId: (id) => {
            if (isCurrentGen()) setConversationId(id);
          },
          onQuotaExceeded,
        },
      );
    },
    [conversationId],
  );

  return {
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
  };
}
