import { type ComponentPropsWithoutRef } from "react";
import ReactMarkdown from "react-markdown";
import type { Message } from "../types";

interface Props {
  message: Message;
  isStreaming?: boolean;
}

const AGENT_DISPLAY: Record<string, string> = {
  general_agent:  "Aura",
  resume_agent:   "Aura · Resume",
  ppt_agent:      "Aura · Slides",
  research_agent: "Aura · Research",
  gaokao_agent:   "Aura · Gaokao",
};

function MarkdownLink({ href, children, ...rest }: ComponentPropsWithoutRef<"a">) {
  if (href && href.startsWith("/api/files/")) {
    const segments = href.split("/");
    const filename = segments.length > 4 ? decodeURIComponent(segments[4]) : "file";
    return (
      <a href={href} className="download-btn" download={filename} {...rest}>
        {children}
      </a>
    );
  }
  return (
    <a href={href} target="_blank" rel="noopener noreferrer" {...rest}>
      {children}
    </a>
  );
}

const markdownComponents = { a: MarkdownLink };

export function MessageBubble({ message, isStreaming }: Props) {
  const isUser = message.role === "user";
  if (isUser) {
    return (
      <div className="message message-user">
        {message.attachment && (
          <div className="message-attachment">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
              <polyline points="14 2 14 8 20 8" />
            </svg>
            <span>{message.attachment.name}</span>
          </div>
        )}
        <div className="message-body">
          <p>{message.content}</p>
        </div>
      </div>
    );
  }

  const agentLabel = message.agentName
    ? (AGENT_DISPLAY[message.agentName] ?? "Aura")
    : "Aura";
  const hasThinking = (message.thinkingSteps?.length ?? 0) > 0;

  return (
    <div className="message message-assistant">
      <div className="message-header">
        <div className="message-avatar">A</div>
        <span className="message-name">{agentLabel}</span>
      </div>

      {hasThinking && (
        <div className="thinking-panel">
          <ul className="thinking-steps">
            {message.thinkingSteps!.map((step, i) => {
              const isLast = i === message.thinkingSteps!.length - 1;
              return (
                <li key={i} className={isLast && isStreaming ? "thinking-step-active" : ""}>
                  {step}
                  {isLast && isStreaming && <span className="thinking-spinner" />}
                </li>
              );
            })}
          </ul>
        </div>
      )}

      <div className="message-content">
        <ReactMarkdown components={markdownComponents}>
          {message.content || ""}
        </ReactMarkdown>
        {isStreaming && <span className="streaming-cursor" />}
      </div>

      {(message.toolCalls?.length ?? 0) > 0 && (
        <div className="tool-calls">
          {message.toolCalls!.map((tc) => (
            <div key={tc.toolCallId} className="tool-call-badge">
              <span className="tool-icon">⚙</span>
              <span>{tc.name}</span>
            </div>
          ))}
        </div>
      )}

      {(message.toolResults?.length ?? 0) > 0 && (
        <div className="tool-results">
          {message.toolResults!.map((tr) => (
            <div key={tr.toolCallId} className="tool-result-box">
              <div className="tool-result-header">{tr.name}</div>
              <pre>{tr.result}</pre>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
