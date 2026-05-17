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
    price_label: "¥0",
    period: "",
    features: ["20 次对话 / 天", "近 30 天历史记录", "标准模型（Doubao）", "全部 24 个技能", "记忆功能"],
    cta: "当前计划",
    recommended: false,
  },
  {
    key: "pro",
    name: "Pro",
    price_label: "¥39",
    period: "/ 月",
    features: ["1000 次对话 / 月", "永久历史记录", "标准 + 高级模型", "全部 24 个技能", "记忆功能"],
    cta: "立即升级",
    recommended: true,
  },
  {
    key: "max",
    name: "Max",
    price_label: "¥99",
    period: "/ 月",
    features: ["无限次对话", "永久历史记录", "全部模型含最新版", "全部 24 个技能", "记忆功能"],
    cta: "升级 Max",
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
        <button className="pricing-modal-close" onClick={onClose} title="关闭">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M3 3l10 10M13 3L3 13" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/>
          </svg>
        </button>

        <h2 className="pricing-modal-title">选择适合你的计划</h2>
        <p className="pricing-modal-sub">升级后额度立即生效，随时可取消</p>

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
                {plan.recommended && <div className="pricing-badge">推荐</div>}
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
                    当前计划
                  </button>
                ) : upgrading === plan.key ? (
                  <div className="pricing-contact-info">
                    请发送邮件至 <strong>hi@useaura.ai</strong> 说明升级计划，我们将在 24 小时内处理
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
          有疑问？发邮件至 <a href="mailto:hi@useaura.ai">hi@useaura.ai</a>
        </p>
      </div>
    </div>
  );
}
