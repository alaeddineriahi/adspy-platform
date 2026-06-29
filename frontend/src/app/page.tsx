import Link from "next/link";

export default function Home() {
  return (
    <main className="min-h-screen bg-gradient-to-b from-gray-950 to-gray-900 text-white">
      <nav className="flex items-center justify-between px-6 py-4 max-w-7xl mx-auto">
        <h1 className="text-2xl font-bold">AdSpy</h1>
        <div className="flex gap-4">
          <Link href="/sign-in" className="px-4 py-2 text-sm text-gray-300 hover:text-white">
            Log in
          </Link>
          <Link href="/sign-up" className="px-4 py-2 text-sm bg-blue-600 rounded-lg hover:bg-blue-500">
            Start free trial
          </Link>
        </div>
      </nav>
      <section className="max-w-4xl mx-auto text-center pt-32 px-6">
        <h2 className="text-5xl font-bold leading-tight mb-6">
          Stop wasting ad spend.<br />Start scaling profitably.
        </h2>
        <p className="text-xl text-gray-400 mb-10 max-w-2xl mx-auto">
          Spy on competitor ads across Meta and TikTok. Generate winning scripts with AI.
          Built for MENA marketers.
        </p>
        <Link
          href="/sign-up"
          className="inline-block px-8 py-4 bg-blue-600 text-lg font-semibold rounded-xl hover:bg-blue-500 transition"
        >
          Try free for 7 days
        </Link>
        <p className="mt-4 text-sm text-gray-500">No credit card required</p>
      </section>
    </main>
  );
}
