import { useCallback, useEffect, useRef, useState } from "react";

interface Props {
  url: string;
  onClose: () => void;
}

export function PreviewPanel({ url, onClose }: Props) {
  const panelRef = useRef<HTMLDivElement>(null);
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const [srcdoc, setSrcdoc] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);

  const segments = url.split("/");
  const rawSegment = segments.length > 4 ? decodeURIComponent(segments[4]) : "Preview";
  const filename = rawSegment.split("?")[0];

  // Fetch HTML and inject via srcDoc — avoids iframe making its own network
  // request, which breaks under Vite proxy / cross-port setups.
  useEffect(() => {
    setSrcdoc(null);
    setLoadError(null);
    fetch(url)
      .then((res) => {
        if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
        return res.text();
      })
      .then((html) => setSrcdoc(html))
      .catch((err) => setLoadError(String(err)));
  }, [url]);

  // Give keyboard focus to the iframe's document so PPT arrow-key nav works.
  // Must be called after load and after any operation that steals focus (fullscreen toggle).
  const focusIframe = useCallback(() => {
    try {
      iframeRef.current?.contentWindow?.focus();
    } catch {
      // sandboxed iframe — silently ignore
    }
  }, []);

  // Track native fullscreen state; re-focus iframe after transition settles
  useEffect(() => {
    const handler = () => {
      setIsFullscreen(!!document.fullscreenElement);
      // Small delay so the browser finishes the fullscreen transition first
      setTimeout(focusIframe, 100);
    };
    document.addEventListener("fullscreenchange", handler);
    return () => document.removeEventListener("fullscreenchange", handler);
  }, [focusIframe]);

  // Esc: exit fullscreen first; only close panel when not in fullscreen
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !document.fullscreenElement) onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      panelRef.current?.requestFullscreen();
    } else {
      document.exitFullscreen();
    }
  };

  return (
    <div ref={panelRef} className="preview-panel" onClick={focusIframe}>
      <div className="preview-header">
        <span className="preview-title" title={filename}>{filename}</span>
        <div className="preview-actions">
          {/* Fullscreen toggle */}
          <button
            className="preview-icon-btn preview-icon-btn--accent"
            onClick={toggleFullscreen}
            title={isFullscreen ? "退出全屏 (Esc)" : "全屏预览"}
          >
            {isFullscreen ? (
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="4 14 10 14 10 20" />
                <polyline points="20 10 14 10 14 4" />
                <line x1="10" y1="14" x2="3" y2="21" />
                <line x1="21" y1="3" x2="14" y2="10" />
              </svg>
            ) : (
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="15 3 21 3 21 9" />
                <polyline points="9 21 3 21 3 15" />
                <line x1="21" y1="3" x2="14" y2="10" />
                <line x1="3" y1="21" x2="10" y2="14" />
              </svg>
            )}
          </button>

          {/* Open in new tab */}
          <a
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className="preview-icon-btn"
            title="在新标签页打开"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6" />
              <polyline points="15 3 21 3 21 9" />
              <line x1="10" y1="14" x2="21" y2="3" />
            </svg>
          </a>

          {/* Close */}
          <button className="preview-icon-btn" onClick={onClose} title="关闭 (Esc)">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>
      </div>

      {loadError ? (
        <div className="preview-error">
          <p>加载失败</p>
          <p className="preview-error-detail">{loadError}</p>
          <a href={url} target="_blank" rel="noopener noreferrer" className="preview-error-link">
            在新标签页中打开 ↗
          </a>
        </div>
      ) : srcdoc === null ? (
        <div className="preview-loading">
          <span className="preview-spinner" />
          <span>加载中…</span>
        </div>
      ) : (
        <iframe
          ref={iframeRef}
          srcDoc={srcdoc}
          className="preview-iframe"
          title={filename}
          sandbox="allow-scripts allow-same-origin allow-pointer-lock"
          onLoad={focusIframe}
        />
      )}
    </div>
  );
}
