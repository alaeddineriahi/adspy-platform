import { UserButton } from "@clerk/nextjs";
import Link from "next/link";
import { SavedProvider } from "@/components/SavedProvider";
import { UsageProvider } from "@/components/UsageProvider";
import { CreditMeter } from "@/components/CreditMeter";
import { AdminProvider } from "@/components/AdminProvider";
import { SideNav } from "@/components/SideNav";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <AdminProvider>
      <UsageProvider>
        <div className="flex h-screen bg-[#fbfbfb]">
          <aside className="w-64 bg-white border-r border-[#e6e6e7] flex flex-col">
            <div className="p-6">
              <Link href="/search" className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full holo-gradient" />
                <span className="text-xl font-black tracking-tight text-[#1d1d1f]">AdSpy</span>
              </Link>
            </div>
            <SideNav />
            <CreditMeter />
            <div className="p-4 border-t border-[#e6e6e7]">
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
