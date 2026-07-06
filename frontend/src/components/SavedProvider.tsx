"use client";

import {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  useCallback,
  ReactNode,
} from "react";
import Link from "next/link";
import { useAuth } from "@clerk/nextjs";
import { authFetch } from "@/lib/api";

interface SavedCtx {
  savedIds: Set<string>;
  isSaved: (id: string) => boolean;
  /** Bookmark toggle: save to Default, or remove from EVERY board. */
  toggle: (id: string) => Promise<void>;
  /** Save to a specific board (creates the board implicitly). */
  saveTo: (id: string, board: string) => Promise<boolean>;
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
  // One shared toast for save failures (free-tier cap, offline) — the bookmark
  // sits on every card, so feedback must not require per-page wiring.
  const [notice, setNotice] = useState<{ text: string; upgrade: boolean } | null>(null);
  const noticeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const showNotice = useCallback((text: string, upgrade = false) => {
    setNotice({ text, upgrade });
    if (noticeTimer.current) clearTimeout(noticeTimer.current);
    noticeTimer.current = setTimeout(() => setNotice(null), 5000);
  }, []);

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

  const failureMessage = useCallback(async (res: Response): Promise<[string, boolean]> => {
    try {
      const d = (await res.json())?.detail;
      if (d?.message) return [d.message, d.error === "saved_cap"];
    } catch {}
    return ["Couldn't save — try again.", false];
  }, []);

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
          // unsave without a board = remove from every board, so the bookmark
          // reliably clears an ad that was saved to a custom board.
          body: JSON.stringify({ ad_id: id }),
        });
        if (!res.ok) {
          const [msg, upgrade] = await failureMessage(res);
          showNotice(msg, upgrade);
          throw new Error(`save failed: ${res.status}`);
        }
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
    [savedIds, getToken, failureMessage, showNotice]
  );

  const saveTo = useCallback(
    async (id: string, board: string): Promise<boolean> => {
      if (!id) return false;
      try {
        const res = await authFetch(getToken, "/api/user/save", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ ad_id: id, board: board || "Default" }),
        });
        if (!res.ok) {
          const [msg, upgrade] = await failureMessage(res);
          showNotice(msg, upgrade);
          return false;
        }
        setSavedIds((prev) => new Set(prev).add(id));
        return true;
      } catch {
        showNotice("Couldn't save — check your connection.");
        return false;
      }
    },
    [getToken, failureMessage, showNotice]
  );

  return (
    <Ctx.Provider
      value={{ savedIds, isSaved: (id) => savedIds.has(id), toggle, saveTo, userId, refresh }}
    >
      {children}
      {notice && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 flex items-center gap-3 bg-[#1d1d1f] text-white text-sm font-medium px-5 py-3 rounded-full shadow-xl">
          <span>{notice.text}</span>
          {notice.upgrade && (
            <Link
              href="/pricing"
              onClick={() => setNotice(null)}
              className="shrink-0 px-3 py-1 rounded-full text-xs font-bold text-[#1d1d1f] bg-white hover:scale-[1.03] transition"
            >
              Upgrade
            </Link>
          )}
        </div>
      )}
    </Ctx.Provider>
  );
}
