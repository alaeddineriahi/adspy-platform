import Link from "next/link";
import { ArrowRight, Search, Megaphone, Zap, Eye } from "lucide-react";

const features = [
  {
    icon: Search,
    title: "Spy the winners",
    text: "A curated library of long-running, scaling e-commerce ads across Tunisia, Morocco, Algeria, Egypt, KSA and the UAE — refreshed automatically.",
  },
  {
    icon: Eye,
    title: "Track any brand",
    text: "See every creative a competitor runs, how long it's been live, and how hard they're scaling it.",
  },
  {
    icon: Megaphone,
    title: "AI media buyer",
    text: "A senior-level co-pilot that turns any spied winner into a launch plan sized to your real budget, market and creatives.",
  },
  {
    icon: Zap,
    title: "Scripts in seconds",
    text: "Hooks, scene-by-scene video scripts and ad copy generated from proven ads — in French, Arabic or English.",
  },
];

export default function Home() {
  return (
    <main className="min-h-screen bg-[#fbfbfb] text-[#1d1d1f]">
      {/* Nav */}
      <nav className="flex items-center justify-between px-6 py-5 max-w-6xl mx-auto">
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full holo-gradient" />
          <span className="text-xl font-black tracking-tight">AdSpy</span>
        </div>
        <div className="flex items-center gap-3">
          <Link
            href="/sign-in"
            className="px-4 py-2 text-sm font-medium text-[#6e6e73] hover:text-[#1d1d1f] transition"
          >
            Log in
          </Link>
          <Link href="/sign-up" className="btn-holo px-5 py-2 text-sm">
            Start free
          </Link>
        </div>
      </nav>

      {/* Hero */}
      <section className="max-w-4xl mx-auto text-center pt-24 pb-16 px-6">
        {/* Gradient badge pill */}
        <div className="inline-flex holo-ring rounded-full mb-7">
          <span className="rounded-full bg-[#fbfbfb] px-5 py-1.5 text-sm font-semibold holo-text">
            Ad intelligence for MENA
          </span>
        </div>

        <h1 className="text-5xl md:text-7xl font-black tracking-tight leading-[1.05] mb-6 text-balance">
          Find the ads that
          <br />
          print money.
        </h1>
        <p className="text-lg md:text-xl text-[#6e6e73] mb-10 max-w-2xl mx-auto leading-relaxed">
          AdSpy watches the Meta Ad Library so you don&apos;t have to — surfacing the
          long-running, scaling winners in your market, then helping you launch your own
          with an AI media buyer.
        </p>

        <div className="flex items-center justify-center gap-4">
          <Link href="/sign-up" className="btn-holo px-8 py-3.5 text-base">
            Start spying free <ArrowRight className="w-4 h-4" />
          </Link>
          <Link
            href="/sign-in"
            className="inline-flex items-center gap-2 px-6 py-3.5 text-base font-semibold text-[#1d1d1f] rounded-full border border-[#e6e6e7] hover:border-[#1d1d1f] transition"
          >
            See the library
          </Link>
        </div>
        <p className="mt-5 text-sm text-[#6e6e73]">
          Free plan included · Pay in TND · No credit card required
        </p>
      </section>

      {/* Social-proof-style strip */}
      <section className="flex justify-center px-6 pb-20">
        <div className="flex flex-wrap items-center justify-center gap-x-8 gap-y-2 border border-[#e6e6e7] rounded-full px-8 py-3 text-sm text-[#6e6e73] bg-white">
          <span>
            <strong className="text-[#1d1d1f] font-bold">6</strong> MENA markets
          </span>
          <span className="hidden sm:inline text-[#e6e6e7]">·</span>
          <span>
            <strong className="text-[#1d1d1f] font-bold">Auto-refreshed</strong> every 12h
          </span>
          <span className="hidden sm:inline text-[#e6e6e7]">·</span>
          <span>
            <strong className="text-[#1d1d1f] font-bold">Winners only</strong> — spam filtered out
          </span>
        </div>
      </section>

      {/* Features */}
      <section className="max-w-6xl mx-auto px-6 pb-28">
        <div className="text-center mb-12">
          <h2 className="text-3xl md:text-4xl font-black tracking-tight mb-3">
            Everything between <span className="holo-text">spying</span> and{" "}
            <span className="holo-text">scaling</span>
          </h2>
          <p className="text-[#6e6e73] max-w-xl mx-auto">
            One tool for the whole loop: find what works, understand why, and launch your
            version — sized to your budget.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {features.map((f) => (
            <div
              key={f.title}
              className="bg-white border border-[#e6e6e7] rounded-2xl p-7 hover:shadow-lg hover:shadow-gray-200/60 transition"
            >
              <div className="w-10 h-10 rounded-xl holo-gradient p-px mb-4">
                <div className="w-full h-full rounded-[11px] bg-white flex items-center justify-center">
                  <f.icon className="w-5 h-5 text-[#1d1d1f]" />
                </div>
              </div>
              <h3 className="text-lg font-bold mb-1.5">{f.title}</h3>
              <p className="text-sm text-[#6e6e73] leading-relaxed">{f.text}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Bottom CTA */}
      <section className="max-w-4xl mx-auto text-center px-6 pb-24">
        <div className="holo-ring rounded-3xl">
          <div className="rounded-[23px] bg-white px-8 py-14">
            <h2 className="text-3xl md:text-4xl font-black tracking-tight mb-3">
              Your competitors&apos; best ads.
              <br />
              Your next campaign.
            </h2>
            <p className="text-[#6e6e73] mb-8">
              Join the marketers who stopped guessing.
            </p>
            <Link href="/sign-up" className="btn-holo px-8 py-3.5 text-base">
              Start free <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </div>
      </section>

      <footer className="border-t border-[#e6e6e7] py-8 text-center text-sm text-[#6e6e73]">
        AdSpy — built for MENA marketers.
      </footer>
    </main>
  );
}
