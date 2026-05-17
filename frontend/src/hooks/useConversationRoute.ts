import { useEffect, useCallback } from "react";

function parseConversationId(): string | null {
  const m = window.location.pathname.match(/^\/chat\/([^/]+)/);
  return m ? m[1] : null;
}

interface Options {
  onLoad: (id: string) => void;
}

export function useConversationRoute({ onLoad }: Options) {
  // Load conversation from URL on mount and on browser back/forward
  useEffect(() => {
    const id = parseConversationId();
    if (id) onLoad(id);

    const handler = () => {
      const nextId = parseConversationId();
      if (nextId) onLoad(nextId);
    };
    window.addEventListener("popstate", handler);
    return () => window.removeEventListener("popstate", handler);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const navigate = useCallback((id: string | null) => {
    const target = id ? `/chat/${id}` : "/";
    if (window.location.pathname !== target) {
      history.pushState({}, "", target);
    }
  }, []);

  return { navigate };
}
