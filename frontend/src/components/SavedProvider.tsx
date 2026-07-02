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
  const { userId: clerkId, getToken, isLoaded } = useAuth();
  const userId = clerkId ?? "anonymous";
  const [savedIds, setSavedIds] = useState<Set<string>>(new Set());

  const refresh = useCallback(async () => {
    if (!isLoaded) return;
    try {
      const res = await authFetch(getToken, "/api/user/saved/ids");
      if (!res.ok) return; // signed out → 401; keep whatever we have
      const data = await res.json();
      setSavedIds(new Set<string>(data.ad_ids || []));
    } catch {
      /* offline / backend down — leave as-is */
    }
  }, [isLoaded, getToken]);

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
        const res = await authFetch(getToken, `/api/user/${has ? "unsave" : "save"}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ ad_id: id }),
        });
        if (!res.ok) throw new Error(`save failed: ${res.status}`);
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
    [savedIds, getToken]
  );

  return (
    <Ctx.Provider
      value={{ savedIds, isSaved: (id) => savedIds.has(id), toggle, userId, refresh }}
    >
      {children}
    </Ctx.Provider>
  );
}
