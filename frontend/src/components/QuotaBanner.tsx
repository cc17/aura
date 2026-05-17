interface Props {
  resetAt: string;
  plan: string;
  onUpgrade: () => void;
}

function formatReset(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
}

export function QuotaBanner({ resetAt, onUpgrade }: Props) {
  return (
    <div className="quota-banner">
      <div className="quota-banner-body">
        <div className="quota-banner-title">今日免费额度已用完</div>
        <div className="quota-banner-sub">
          将于明天 {formatReset(resetAt)} 重置 · 升级 Pro 每月 1000 次，Max 无限次
        </div>
      </div>
      <div className="quota-banner-actions">
        <button className="quota-upgrade-btn quota-upgrade-btn--pro" onClick={onUpgrade}>
          升级 Pro
        </button>
        <button className="quota-upgrade-btn quota-upgrade-btn--max" onClick={onUpgrade}>
          了解 Max
        </button>
      </div>
    </div>
  );
}
