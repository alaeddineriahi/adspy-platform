"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Loader2, ShieldAlert, LayoutDashboard, Users, CreditCard, Database, ScrollText, Download } from "lucide-react";
import { useIsAdmin } from "@/components/AdminProvider";

const tabs = [
  { href: "/admin", label: "Overview", icon: LayoutDashboard, exact: true },
  { href: "/admin/users", label: "Users", icon: Users },
  { href: "/admin/billing", label: "Billing", icon: CreditCard },
  { href: "/admin/catalog", label: "Catalog", icon: Database },
  { href: "/admin/ingestion", label: "Ingestion", icon: Download },
  { href: "/admin/audit", label: "Audit log", icon: ScrollText },
];

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const { isAdmin, checked } = useIsAdmin();
  const pathname = usePathname();

  if (!checked) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
      </div>
    );
  }

  if (!isAdmin) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center px-8">
        <ShieldAlert className="w-12 h-12 text-red-400 mb-4" />
        <p className="text-lg font-semibold text-gray-900">Admins only</p>
        <p className="text-sm text-gray-500 mt-1 max-w-sm">
          This section is restricted. If you think you should have access, ask an existing
          admin to promote your account.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <div className="px-8 pt-6 border-b border-gray-200 bg-white">
        <h1 className="text-xl font-bold text-gray-900 mb-3">Backoffice</h1>
        <nav className="flex gap-1 -mb-px">
          {tabs.map((t) => {
            const active = t.exact ? pathname === t.href : pathname.startsWith(t.href);
            return (
              <Link
                key={t.href}
                href={t.href}
                className={`flex items-center gap-1.5 px-3.5 py-2.5 text-sm font-medium border-b-2 transition ${
                  active
                    ? "border-gray-900 text-gray-900"
                    : "border-transparent text-gray-500 hover:text-gray-800"
                }`}
              >
                <t.icon className="w-4 h-4" /> {t.label}
              </Link>
            );
          })}
        </nav>
      </div>
      <div className="flex-1 overflow-auto">{children}</div>
    </div>
  );
}
