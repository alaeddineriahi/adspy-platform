"use client";

import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  ReactNode,
} from "react";
import { useUser } from "@clerk/nextjs";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface SavedCtx {
  savedIds: Set<string>;
  isSaved: (id: string) => boolean;
  toggle: (id: string) => Promise<void>;
  userId: string;
  refresh: () => void;
}

const Ctx = createContext<SavedCtx | null>(null);

export function useSaved(): SavedCtx {
  const c = useContext(Ctx);
  if (!c) throw new Error("useSaved must be used within <SavedProvider>");
  return c;
}

export function SavedProvider({ children }: { children: ReactNode }) {
  const { user } = useUser();
  const userId = user?.id ?? "anonymous";
  const [savedIds, setSavedIds] = useState<Set<string>>(new Set());

  const refresh = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/user/saved/ids`, {
        headers: { "X-User-Id": userId },
      });
      const data = await res.json();
      setSavedIds(new Set<string>(data.ad_ids || []));
    } catch {
      /* offline / backend down — leave as-is */
    }
  }, [userId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const toggle = useCallback(
    async (id: string) => {
      if (!id) return;
      const has = savedIds.has(id);
      // optimistic
      setSavedIds((prev) => {
        const next = new Set(prev);
        if (has) next.delete(id);
        else next.add(id);
        return next;
      });
      try {
        await fetch(`${API_URL}/api/user/${has ? "unsave" : "save"}`, {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-User-Id": userId },
          body: JSON.stringify({ ad_id: id }),
        });
      } catch {
        // revert on failure
        setSavedIds((prev) => {
          const next = new Set(prev);
          if (has) next.add(id);
          else next.delete(id);
          return next;
        });
      }
    },
    [savedIds, userId]
  );

  return (
    <Ctx.Provider
      value={{ savedIds, isSaved: (id) => savedIds.has(id), toggle, userId, refresh }}
    >
      {children}
    </Ctx.Provider>
  );
}
