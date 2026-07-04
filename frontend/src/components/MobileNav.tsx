"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu, X } from "lucide-react";
import { UserButton } from "@clerk/nextjs";
import { SideNav } from "@/components/SideNav";
import { CreditMeter } from "@/components/CreditMeter";

/** Top bar + slide-over drawer for < lg screens (the sidebar is hidden there). */
export function MobileNav() {
  const [open, setOpen] = useState(false);
  const pathname = usePathname();

  // Close the drawer whenever navigation happens.
  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  return (
    <>
      <header className="lg:hidden sticky top-0 z-40 flex items-center justify-between bg-white/90 backdrop-blur border-b border-[#e6e6e7] px-4 py-3">
        <Link href="/search" className="flex items-center gap-2">
          <span className="radar-live-dot w-2.5 h-2.5 rounded-full holo-gradient" />
          <span className="text-lg font-black tracking-tight text-[#1d1d1f]">AdSpy</span>
        </Link>
        <button
          onClick={() => setOpen(true)}
          aria-label="Open menu"
          className="p-2 rounded-full border border-[#e6e6e7] hover:border-[#1d1d1f] transition"
        >
          <Menu className="w-5 h-5 text-[#1d1d1f]" />
        </button>
      </header>

      {open && (
        <div className="lg:hidden fixed inset-0 z-50">
          <div className="absolute inset-0 bg-black/30" onClick={() => setOpen(false)} />
          <div className="absolute inset-y-0 left-0 w-72 bg-white flex flex-col shadow-2xl">
            <div className="flex items-center justify-between p-5">
              <Link href="/search" className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full holo-gradient" />
                <span className="text-lg font-black tracking-tight text-[#1d1d1f]">AdSpy</span>
              </Link>
              <button
                onClick={() => setOpen(false)}
                aria-label="Close menu"
                className="p-2 rounded-full hover:bg-gray-100 transition"
              >
                <X className="w-5 h-5 text-[#6e6e73]" />
              </button>
            </div>
            <SideNav />
            <CreditMeter />
            <div className="p-4 border-t border-[#e6e6e7]">
              <UserButton afterSignOutUrl="/" />
            </div>
          </div>
        </div>
      )}
    </>
  );
}
