"use client";

import Link from "next/link";
import { ShieldCheck } from "lucide-react";
import { useIsAdmin } from "@/components/AdminProvider";

export function AdminNavLink() {
  const { isAdmin } = useIsAdmin();
  if (!isAdmin) return null;
  return (
    <div className="mt-2 pt-2 border-t border-[#e6e6e7]">
      <Link
        href="/admin"
        className="flex items-center gap-3 px-3 py-2.5 text-sm text-[#6e6e73] rounded-xl hover:bg-gray-100 hover:text-[#1d1d1f] transition"
      >
        <ShieldCheck className="w-5 h-5" />
        Admin
      </Link>
    </div>
  );
}
