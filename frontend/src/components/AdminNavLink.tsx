"use client";

import Link from "next/link";
import { ShieldCheck } from "lucide-react";
import { useIsAdmin } from "@/components/AdminProvider";

export function AdminNavLink() {
  const { isAdmin } = useIsAdmin();
  if (!isAdmin) return null;
  return (
    <Link
      href="/admin"
      className="flex items-center gap-3 px-3 py-2.5 text-sm text-gray-700 rounded-lg hover:bg-gray-100 mb-1 mt-2 pt-3 border-t border-gray-100"
    >
      <ShieldCheck className="w-5 h-5" />
      Admin
    </Link>
  );
}
