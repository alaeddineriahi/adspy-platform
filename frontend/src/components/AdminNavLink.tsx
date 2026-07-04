"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ShieldCheck } from "lucide-react";
import { useIsAdmin } from "@/components/AdminProvider";

export function AdminNavLink() {
  const { isAdmin } = useIsAdmin();
  const pathname = usePathname();
  if (!isAdmin) return null;
  const active = pathname.startsWith("/admin");
  return (
    <div className="mt-2 pt-2 border-t border-[#e6e6e7]">
      <Link
        href="/admin"
        className={`group flex items-center gap-3 px-2.5 py-2 text-sm rounded-xl transition-all duration-200 ${
          active
            ? "bg-[#1d1d1f] text-white font-semibold shadow-sm"
            : "text-[#6e6e73] hover:bg-gray-100 hover:text-[#1d1d1f]"
        }`}
      >
        <span
          className={`w-7 h-7 shrink-0 rounded-lg flex items-center justify-center transition-transform duration-200 group-hover:scale-105 ${
            active
              ? "bg-gradient-to-br from-[#6e6e73] to-[#1d1d1f] text-white"
              : "bg-gray-100 text-[#6e6e73] group-hover:bg-white group-hover:text-[#1d1d1f]"
          }`}
        >
          <ShieldCheck className="w-4 h-4" />
        </span>
        Admin
      </Link>
    </div>
  );
}
