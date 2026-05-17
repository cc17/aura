export interface FileAttachment {
  name: string;
  size: number;
}

export interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  toolCalls?: ToolCallInfo[];
  toolResults?: ToolResultInfo[];
  agentName?: string;
  attachment?: FileAttachment;
  thinkingSteps?: string[];   // internal progress lines from THINKING events
  timestamp: string;
}

export interface ToolCallInfo {
  toolCallId: string;
  name: string;
  arguments: Record<string, unknown>;
}

export interface ToolResultInfo {
  toolCallId: string;
  name: string;
  result: string;
}

export interface ModelInfo {
  id: string;
  name: string;
  provider: string;
}

export interface ToolInfo {
  name: string;
  description: string;
}

export interface Conversation {
  id: string;
  title: string;
  updated_at: string;
}

export interface User {
  id: number;
  username: string;
  onboarded: boolean;
  profile?: Record<string, unknown>;
}
