import { useState } from "react";

interface Plan {
  key: string;
  name: string;
  price_label: string;
  period: string;
  features: string[];
  cta: string;
  recommended: boolean;
}

const PLANS: Plan[] = [
  {
    key: "free",
    name: "Free",
    price_label: "$0",
    period: "",
    features: ["20 conversations / day", "30-day history", "Standard model (Doubao)", "All 24 skills", "Memory"],
    cta: "Current plan",
    recommended: false,
  },
  {
    key: "pro",
    name: "Pro",
    price_label: "$9",
    period: "/ mo",
    features: ["1,000 conversations / month", "Unlimited history", "Standard + advanced models", "All 24 skills", "Memory"],
    cta: "Upgrade now",
    recommended: true,
  },
  {
    key: "max",
    name: "Max",
    price_label: "$19",
    period: "/ mo",
    features: ["Unlimited conversations", "Unlimited history", "All models incl. latest", "All 24 skills", "Memory"],
    cta: "Upgrade to Max",
    recommended: false,
  },
];

interface Props {
  currentPlan: string;
  onClose: () => void;
}

export function PricingModal({ currentPlan, onClose }: Props) {
  const [upgrading, setUpgrading] = useState<string | null>(null);

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="pricing-modal" onClick={(e) => e.stopPropagation()}>
        <button className="pricing-modal-close" onClick={onClose} title="Close">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M3 3l10 10M13 3L3 13" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/>
          </svg>
        </button>

        <h2 className="pricing-modal-title">Choose your plan</h2>
        <p className="pricing-modal-sub">Quota takes effect immediately. Cancel anytime.</p>

        <div className="pricing-cards">
          {PLANS.map((plan) => {
            const isCurrent = plan.key === currentPlan;
            return (
              <div
                key={plan.key}
                className={[
                  "pricing-card",
                  plan.recommended ? "pricing-card--recommended" : "",
                  isCurrent ? "pricing-card--current" : "",
                ].join(" ").trim()}
              >
                {plan.recommended && <div className="pricing-badge">Recommended</div>}
                <div className="pricing-card-name">{plan.name}</div>
                <div className="pricing-card-price">
                  <span className="pricing-price-main">{plan.price_label}</span>
                  {plan.period && (
                    <span className="pricing-price-period">{plan.period}</span>
                  )}
                </div>
                <ul className="pricing-features">
                  {plan.features.map((f) => (
                    <li key={f}>
                      <span className="pricing-check">✓</span>
                      {f}
                    </li>
                  ))}
                </ul>
                {isCurrent ? (
                  <button className="pricing-cta pricing-cta--current" disabled>
                    Current plan
                  </button>
                ) : upgrading === plan.key ? (
                  <div className="pricing-contact-info">
                    Email <strong>hi@useaura.ai</strong> to upgrade — we'll process it within 24 hours.
                  </div>
                ) : (
                  <button
                    className="pricing-cta pricing-cta--upgrade"
                    onClick={() => setUpgrading(plan.key)}
                  >
                    {plan.cta}
                  </button>
                )}
              </div>
            );
          })}
        </div>

        <p className="pricing-footer">
          Questions? Email <a href="mailto:hi@useaura.ai">hi@useaura.ai</a>
        </p>
      </div>
    </div>
  );
}
