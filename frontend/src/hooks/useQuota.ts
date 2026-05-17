import { useCallback, useEffect, useState } from "react";
import { apiFetch } from "../services/api";

export interface QuotaInfo {
  plan: string;
  usage_count: number;
  quota_limit: number;
  remaining: number;
  period_start: string;
  reset_at: string;
  plan_expires_at: string | null;
}

export function useQuota(authenticated: boolean) {
  const [quota, setQuota] = useState<QuotaInfo | null>(null);

  const refreshQuota = useCallback(async () => {
    try {
      const res = await apiFetch("/quota");
      if (res.ok) setQuota(await res.json());
    } catch {
      // silent
    }
  }, []);

  useEffect(() => {
    if (authenticated) refreshQuota();
  }, [authenticated, refreshQuota]);

  return { quota, refreshQuota };
}
