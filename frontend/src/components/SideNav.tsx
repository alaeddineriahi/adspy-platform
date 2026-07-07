"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Search, Bookmark, Zap, Eye, Settings, Megaphone, CreditCard, ScanSearch, Radar,
  Sparkles, LucideIcon,
} from "lucide-react";
import { AdminNavLink } from "@/components/AdminNavLink";

/** Grouped nav, radar design language: each item owns a stop of the holo
 * gradient (lights up as a tile when active), sections get whisper labels,
 * and the whole column staggers in. */
const SECTIONS: {
  label: string;
  items: { href: string; label: string; icon: LucideIcon; grad: string; live?: boolean }[];
}[] = [
  {
    label: "Discover",
    items: [
      { href: "/radar", label: "Trend Radar", icon: Radar, grad: "from-[#ec4492] to-[#ee4454]", live: true },
      { href: "/discovered", label: "Just Discovered", icon: Sparkles, grad: "from-[#f05427] to-[#ec4492]", live: true },
      { href: "/search", label: "Search", icon: Search, grad: "from-[#3e86c6] to-[#a666aa]" },
      { href: "/brands", label: "Brand Spy", icon: Eye, grad: "from-[#a666aa] to-[#ec4492]" },
    ],
  },
  {
    label: "Tools",
    items: [
      { href: "/intel", label: "Website Intel", icon: ScanSearch, grad: "from-[#ec4492] to-[#ee4454]" },
      { href: "/mediabuyer", label: "Media Buyer", icon: Megaphone, grad: "from-[#a666aa] to-[#3e86c6]" },
      { href: "/ai", label: "AI Tools", icon: Zap, grad: "from-[#ee4454] to-[#f05427]" },
    ],
  },
  {
    label: "Library",
    items: [
      { href: "/saved", label: "Saved", icon: Bookmark, grad: "from-[#f05427] to-[#3e86c6]" },
    ],
  },
  {
    label: "Account",
    items: [
      { href: "/pricing", label: "Pricing", icon: CreditCard, grad: "from-[#3e86c6] to-[#ec4492]" },
      { href: "/settings", label: "Settings", icon: Settings, grad: "from-[#1d1d1f] to-[#6e6e73]" },
    ],
  },
];

export function SideNav() {
  const pathname = usePathname();
  let idx = 0;
  return (
    <nav className="flex-1 px-3 overflow-y-auto">
      {SECTIONS.map((section) => (
        <div key={section.label} className="mb-3">
          <p
            className="fade-up px-3 pt-2 pb-1.5 text-[10px] font-bold uppercase tracking-[0.12em] text-gray-400"
            style={{ ["--delay" as string]: `${idx * 35}ms` }}
          >
            {section.label}
          </p>
          {section.items.map((item) => {
            const active = pathname === item.href || pathname.startsWith(item.href + "/");
            const delay = `${++idx * 35}ms`;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`fade-up group flex items-center gap-3 px-2.5 py-2 text-sm rounded-xl mb-0.5 transition-all duration-200 ${
                  active
                    ? "bg-[#1d1d1f] text-white font-semibold shadow-sm"
                    : "text-[#6e6e73] hover:bg-gray-100 hover:text-[#1d1d1f]"
                }`}
                style={{ ["--delay" as string]: delay }}
              >
                <span
                  className={`w-7 h-7 shrink-0 rounded-lg flex items-center justify-center transition-transform duration-200 group-hover:scale-105 ${
                    active
                      ? `bg-gradient-to-br ${item.grad} text-white`
                      : "bg-gray-100 text-[#6e6e73] group-hover:bg-white group-hover:text-[#1d1d1f]"
                  }`}
                >
                  <item.icon className="w-4 h-4" />
                </span>
                <span className="flex items-center gap-2">
                  {item.label}
                  {item.live && (
                    <span className={`radar-live-dot w-1.5 h-1.5 rounded-full ${active ? "bg-white" : "bg-[#ec4492]"}`} />
                  )}
                </span>
              </Link>
            );
          })}
        </div>
      ))}
      <AdminNavLink />
    </nav>
  );
}
