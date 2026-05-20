import { useEffect, useState } from "react";
import type { MarketSkill, MySkill } from "../services/api";
import {
  addSkill,
  fetchMarketSkills,
  fetchMySkills,
  pinSkill,
  removeSkill,
} from "../services/api";
import { SkillDetailModal } from "./SkillDetailModal";

type MoreTab = "skill" | "connect";
type SkillTab = "my" | "market";

interface Props {
  onBack: () => void;
}

export function MoreView({ onBack }: Props) {
  const [tab, setTab] = useState<MoreTab>("skill");
  const [skillTab, setSkillTab] = useState<SkillTab>("my");
  const [mySkills, setMySkills] = useState<MySkill[]>([]);
  const [marketSkills, setMarketSkills] = useState<MarketSkill[]>([]);
  const [selectedSkill, setSelectedSkill] = useState<MarketSkill | null>(null);
  const [pinError, setPinError] = useState<string | null>(null);
  const [loadingPin, setLoadingPin] = useState<string | null>(null);

  useEffect(() => {
    if (tab !== "skill") return;
    fetchMySkills().then(setMySkills).catch(() => {});
    fetchMarketSkills().then(setMarketSkills).catch(() => {});
  }, [tab]);

  const handleAdd = async (skillKey: string) => {
    await addSkill(skillKey);
    const [my, market] = await Promise.all([fetchMySkills(), fetchMarketSkills()]);
    setMySkills(my);
    setMarketSkills(market);
  };

  const handleRemove = async (skillKey: string) => {
    await removeSkill(skillKey);
    const [my, market] = await Promise.all([fetchMySkills(), fetchMarketSkills()]);
    setMySkills(my);
    setMarketSkills(market);
  };

  const handlePin = async (skillKey: string, pinned: boolean) => {
    setLoadingPin(skillKey);
    setPinError(null);
    try {
      await pinSkill(skillKey, pinned);
      setMySkills(await fetchMySkills());
    } catch (e: unknown) {
      setPinError(e instanceof Error ? e.message : "Action failed");
    } finally {
      setLoadingPin(null);
    }
  };

  return (
    <div className="more-view">
      <div className="more-view-nav">
        <button className="more-view-back" onClick={onBack} title="Back to chat">
          <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
            <path d="M9 3L5 7.5L9 12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          Back
        </button>

        <div className="more-view-nav-section">
          <button
            className={`more-view-nav-item ${tab === "skill" ? "active" : ""}`}
            onClick={() => setTab("skill")}
          >
            <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
              <path d="M7.5 1.5L9.02 5.46L13.25 5.87L10.12 8.69L11.05 12.87L7.5 10.75L3.95 12.87L4.88 8.69L1.75 5.87L5.98 5.46L7.5 1.5Z"
                stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round"/>
            </svg>
            Skills
          </button>
          <button
            className={`more-view-nav-item ${tab === "connect" ? "active" : ""}`}
            onClick={() => setTab("connect")}
          >
            <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
              <circle cx="3" cy="7.5" r="2" stroke="currentColor" strokeWidth="1.3"/>
              <circle cx="12" cy="3" r="2" stroke="currentColor" strokeWidth="1.3"/>
              <circle cx="12" cy="12" r="2" stroke="currentColor" strokeWidth="1.3"/>
              <path d="M5 7.5L10 3.5M5 7.5L10 11.5" stroke="currentColor" strokeWidth="1.2"/>
            </svg>
            Connect
          </button>
        </div>
      </div>

      <div className="more-view-content">
        {tab === "connect" && (
          <div className="more-view-section">
            <h2 className="more-view-title">Connect</h2>
            <p className="more-view-desc">Connect your tools and bring Aura into your workflow.</p>
            <div className="more-view-empty">Coming soon</div>
          </div>
        )}

        {tab === "skill" && (
          <div className="more-view-section">
            <div className="skill-subtabs">
              <button
                className={`skill-subtab ${skillTab === "my" ? "active" : ""}`}
                onClick={() => setSkillTab("my")}
              >
                My Skills
                {mySkills.length > 0 && (
                  <span className="skill-subtab-count">{mySkills.length}</span>
                )}
              </button>
              <button
                className={`skill-subtab ${skillTab === "market" ? "active" : ""}`}
                onClick={() => setSkillTab("market")}
              >
                Skill Market
              </button>
            </div>

            {skillTab === "my" && (
              <div className="my-skills">
                {pinError && (
                  <div className="my-skills-error">{pinError}</div>
                )}
                {mySkills.length === 0 ? (
                  <div className="my-skills-empty">
                    <p>No skills added yet</p>
                    <button
                      className="my-skills-goto-market"
                      onClick={() => setSkillTab("market")}
                    >
                      Browse the Skill Market →
                    </button>
                  </div>
                ) : (
                  <>
                    {mySkills.some((s) => s.is_pinned) && (
                      <div className="my-skills-group-label">Pinned to home screen (max 4)</div>
                    )}
                    <div className="my-skills-list">
                      {mySkills.map((skill) => (
                        <div key={skill.skill_key} className="my-skill-item">
                          <div className="my-skill-info">
                            <span className="my-skill-name">{skill.scenario_name}</span>
                            {skill.tagline && (
                              <span className="my-skill-tagline">{skill.tagline}</span>
                            )}
                          </div>
                          <div className="my-skill-actions">
                            <button
                              className={`my-skill-pin-btn ${skill.is_pinned ? "active" : ""}`}
                              title={skill.is_pinned ? "Unpin" : "Pin to home screen"}
                              onClick={() => handlePin(skill.skill_key, !skill.is_pinned)}
                              disabled={loadingPin === skill.skill_key}
                            >
                              <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                                <path d="M5 2l7 7-2 2-2-2-3 3H3l2-3-2-2 2-2z" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round"/>
                              </svg>
                            </button>
                            <button
                              className="my-skill-remove-btn"
                              title="Remove"
                              onClick={() => handleRemove(skill.skill_key)}
                            >
                              <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                                <path d="M2 2l10 10M12 2L2 12" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/>
                              </svg>
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </>
                )}
              </div>
            )}

            {skillTab === "market" && (
              <div className="skill-market">
                <div className="skill-market-grid">
                  {marketSkills.map((skill) => (
                    <button
                      key={skill.skill_key}
                      className="market-skill-card"
                      onClick={() => setSelectedSkill(skill)}
                    >
                      {skill.is_added && (
                        <span className="market-skill-added-badge">Added</span>
                      )}
                      <div className="market-skill-name">{skill.scenario_name}</div>
                      {skill.tagline && (
                        <div className="market-skill-tagline">{skill.tagline}</div>
                      )}
                      <div className="market-skill-tags">
                        {skill.industry && (
                          <span className="skill-tag">{skill.industry}</span>
                        )}
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {selectedSkill && (
        <SkillDetailModal
          skill={selectedSkill}
          onAdd={async (key) => {
            await handleAdd(key);
            setSelectedSkill((prev) => prev ? { ...prev, is_added: true } : null);
          }}
          onRemove={async (key) => {
            await handleRemove(key);
            setSelectedSkill((prev) => prev ? { ...prev, is_added: false } : null);
          }}
          onClose={() => setSelectedSkill(null)}
        />
      )}
    </div>
  );
}
