import { UserButton } from "@clerk/nextjs";
import Link from "next/link";
import { Search, Bookmark, Zap, Eye, Settings, Megaphone, CreditCard } from "lucide-react";
import { SavedProvider } from "@/components/SavedProvider";
import { UsageProvider } from "@/components/UsageProvider";
import { CreditMeter } from "@/components/CreditMeter";
import { AdminProvider } from "@/components/AdminProvider";
import { AdminNavLink } from "@/components/AdminNavLink";

const navItems = [
  { href: "/search", label: "Search", icon: Search },
  { href: "/brands", label: "Brand Spy", icon: Eye },
  { href: "/mediabuyer", label: "Media Buyer", icon: Megaphone },
  { href: "/ai", label: "AI Tools", icon: Zap },
  { href: "/saved", label: "Saved", icon: Bookmark },
  { href: "/pricing", label: "Pricing", icon: CreditCard },
  { href: "/settings", label: "Settings", icon: Settings },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <AdminProvider>
      <UsageProvider>
        <div className="flex h-screen bg-gray-50">
          <aside className="w-64 bg-white border-r border-gray-200 flex flex-col">
            <div className="p-6">
              <Link href="/search" className="text-xl font-bold text-gray-900">
                AdSpy
              </Link>
            </div>
            <nav className="flex-1 px-3">
              {navItems.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className="flex items-center gap-3 px-3 py-2.5 text-sm text-gray-700 rounded-lg hover:bg-gray-100 mb-1"
                >
                  <item.icon className="w-5 h-5" />
                  {item.label}
                </Link>
              ))}
              <AdminNavLink />
            </nav>
            <CreditMeter />
            <div className="p-4 border-t border-gray-200">
              <UserButton afterSignOutUrl="/" />
            </div>
          </aside>
          <main className="flex-1 overflow-auto">
            <SavedProvider>{children}</SavedProvider>
          </main>
        </div>
      </UsageProvider>
    </AdminProvider>
  );
}
