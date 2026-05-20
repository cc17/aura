interface Props {
  resetAt: string;
  plan: string;
  onUpgrade: () => void;
}

function formatReset(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });
}

export function QuotaBanner({ resetAt, onUpgrade }: Props) {
  return (
    <div className="quota-banner">
      <div className="quota-banner-body">
        <div className="quota-banner-title">Daily free quota reached</div>
        <div className="quota-banner-sub">
          Resets tomorrow at {formatReset(resetAt)} · Pro: 1,000/mo · Max: unlimited
        </div>
      </div>
      <div className="quota-banner-actions">
        <button className="quota-upgrade-btn quota-upgrade-btn--pro" onClick={onUpgrade}>
          Upgrade to Pro
        </button>
        <button className="quota-upgrade-btn quota-upgrade-btn--max" onClick={onUpgrade}>
          Learn about Max
        </button>
      </div>
    </div>
  );
}
