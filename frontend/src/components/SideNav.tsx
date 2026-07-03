"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Search, Bookmark, Zap, Eye, Settings, Megaphone, CreditCard, ScanSearch } from "lucide-react";
import { AdminNavLink } from "@/components/AdminNavLink";

const navItems = [
  { href: "/search", label: "Search", icon: Search },
  { href: "/brands", label: "Brand Spy", icon: Eye },
  { href: "/intel", label: "Website Intel", icon: ScanSearch },
  { href: "/mediabuyer", label: "Media Buyer", icon: Megaphone },
  { href: "/ai", label: "AI Tools", icon: Zap },
  { href: "/saved", label: "Saved", icon: Bookmark },
  { href: "/pricing", label: "Pricing", icon: CreditCard },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function SideNav() {
  const pathname = usePathname();
  return (
    <nav className="flex-1 px-3">
      {navItems.map((item) => {
        const active = pathname === item.href || pathname.startsWith(item.href + "/");
        return (
          <Link
            key={item.href}
            href={item.href}
            className={`flex items-center gap-3 px-3 py-2.5 text-sm rounded-xl mb-1 transition ${
              active
                ? "bg-[#1d1d1f] text-white font-semibold"
                : "text-[#6e6e73] hover:bg-gray-100 hover:text-[#1d1d1f]"
            }`}
          >
            <item.icon className="w-5 h-5" />
            {item.label}
          </Link>
        );
      })}
      <AdminNavLink />
    </nav>
  );
}
