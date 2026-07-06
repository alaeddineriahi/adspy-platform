"use client";

import { useEffect, useRef, useState } from "react";
import { Bookmark, ChevronDown, FolderPlus, Check } from "lucide-react";
import { useAuth } from "@clerk/nextjs";
import { authFetch } from "@/lib/api";
import { useSaved } from "@/components/SavedProvider";

interface Board {
  name: string;
  count: number;
}

/**
 * Split save control for detail pages: the main button is a one-click
 * bookmark (Default board / remove everywhere), the chevron opens a board
 * picker — pick an existing board or type a new one. Boards are created
 * implicitly by saving to them.
 */
export function SaveButton({ adId }: { adId: string }) {
  const { getToken } = useAuth();
  const { isSaved, toggle, saveTo } = useSaved();
  const saved = isSaved(adId);

  const [open, setOpen] = useState(false);
  const [boards, setBoards] = useState<Board[]>([]);
  const [newBoard, setNewBoard] = useState("");
  const [justSaved, setJustSaved] = useState<string | null>(null);
  const wrapRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!open) return;
    authFetch(getToken, "/api/user/saved")
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => setBoards(d?.boards || []))
      .catch(() => {});
    const onDoc = (e: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [open, getToken]);

  const pick = async (board: string) => {
    const ok = await saveTo(adId, board);
    if (ok) {
      setJustSaved(board);
      setTimeout(() => {
        setJustSaved(null);
        setOpen(false);
      }, 900);
    }
  };

  return (
    <div ref={wrapRef} className="relative flex-1 flex">
      <button
        onClick={() => toggle(adId)}
        className={`flex-1 flex items-center justify-center gap-2 py-2.5 border rounded-l-xl text-sm transition ${
          saved
            ? "bg-[#1d1d1f] text-white border-[#1d1d1f]"
            : "border-gray-300 hover:bg-gray-50"
        }`}
      >
        <Bookmark className={`w-4 h-4 ${saved ? "fill-current" : ""}`} />
        {saved ? "Saved" : "Save"}
      </button>
      <button
        onClick={() => setOpen((v) => !v)}
        title="Save to a board"
        className={`px-2 border border-l-0 rounded-r-xl transition ${
          saved ? "bg-[#1d1d1f] text-white border-[#1d1d1f]" : "border-gray-300 hover:bg-gray-50"
        }`}
      >
        <ChevronDown className="w-4 h-4" />
      </button>

      {open && (
        <div className="absolute bottom-full mb-2 left-0 right-0 min-w-[220px] bg-white border border-[#e6e6e7] rounded-xl shadow-xl p-2 z-20">
          <p className="text-[11px] font-semibold text-gray-400 uppercase px-2 pt-1 pb-2">
            Save to board
          </p>
          {boards.map((b) => (
            <button
              key={b.name}
              onClick={() => pick(b.name)}
              className="w-full flex items-center justify-between px-2.5 py-2 rounded-lg text-sm text-left hover:bg-gray-50"
            >
              <span className="truncate font-medium">{b.name}</span>
              {justSaved === b.name ? (
                <Check className="w-4 h-4 text-emerald-600" />
              ) : (
                <span className="text-xs text-gray-400">{b.count}</span>
              )}
            </button>
          ))}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              const name = newBoard.trim();
              if (name) {
                pick(name);
                setNewBoard("");
              }
            }}
            className="flex items-center gap-1.5 px-1.5 pt-1.5 mt-1 border-t border-[#f0f0f1]"
          >
            <FolderPlus className="w-4 h-4 text-gray-400 shrink-0" />
            <input
              value={newBoard}
              onChange={(e) => setNewBoard(e.target.value)}
              placeholder="New board…"
              maxLength={48}
              className="w-full py-1.5 text-sm outline-none placeholder:text-gray-400"
            />
          </form>
        </div>
      )}
    </div>
  );
}
