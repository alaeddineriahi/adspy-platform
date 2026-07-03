import Link from "next/link";

/** Shared shell for sign-in/sign-up: light canvas, brand mark, soft orbs. */
export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="relative min-h-screen flex flex-col items-center justify-center bg-[#fbfbfb] overflow-hidden px-4">
      <div className="orb float-slow w-[380px] h-[380px] -top-20 -left-28" style={{ background: "#3e86c6" }} />
      <div className="orb float-slow w-[340px] h-[340px] bottom-0 -right-24" style={{ background: "#ec4492", animationDelay: "1.5s" }} />
      <Link href="/" className="relative flex items-center gap-2 mb-8">
        <span className="w-2.5 h-2.5 rounded-full holo-gradient" />
        <span className="text-2xl font-black tracking-tight text-[#1d1d1f]">AdSpy</span>
      </Link>
      <div className="relative">{children}</div>
      <p className="relative mt-8 text-xs text-[#6e6e73]">Ad intelligence for MENA marketers.</p>
    </div>
  );
}
