import type { ToolCallInfo } from "../types";

interface Props {
  activeToolCalls: ToolCallInfo[];
}

export function ToolIndicator({ activeToolCalls }: Props) {
  if (activeToolCalls.length === 0) return null;

  return (
    <div className="tool-indicator">
      {activeToolCalls.map((tc) => (
        <div key={tc.toolCallId} className="tool-indicator-item">
          <span className="spinner" />
          <span>Running: {tc.name}</span>
        </div>
      ))}
    </div>
  );
}
