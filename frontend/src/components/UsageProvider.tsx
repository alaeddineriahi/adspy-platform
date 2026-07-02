"use client";

import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  ReactNode,
} from "react";
import { useAuth } from "@clerk/nextjs";
import { authFetch } from "@/lib/api";

export interface Usage {
  plan: "free" | "pro" | "agency";
  period: string;
  credits_used: number;
  credits_limit: number;
  credits_remaining: number;
}

interface UsageCtx {
  usage: Usage | null;
  refresh: () => Promise<void>;
}

const Ctx = createContext<UsageCtx>({ usage: null, refresh: async () => {} });

export function useUsage(): UsageCtx {
  return useContext(Ctx);
}

/** Fetches /api/user/usage once on load; call refresh() after any AI action. */
export function UsageProvider({ children }: { children: ReactNode }) {
  const { getToken, isLoaded, isSignedIn } = useAuth();
  const [usage, setUsage] = useState<Usage | null>(null);

  const refresh = useCallback(async () => {
    if (!isLoaded || !isSignedIn) return;
    try {
      const res = await authFetch(getToken, "/api/user/usage");
      if (res.ok) setUsage(await res.json());
    } catch {
      /* backend down — keep last known value */
    }
  }, [isLoaded, isSignedIn, getToken]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return <Ctx.Provider value={{ usage, refresh }}>{children}</Ctx.Provider>;
}
