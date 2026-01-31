import Link from "next/link";

export default function Home() {
  return (
    <div className="grid-bg relative min-h-screen overflow-hidden">
      <div className="relative z-10 flex min-h-screen flex-col items-center justify-center px-4 py-20">
        <div className="absolute inset-0 flex items-center justify-center overflow-hidden">
          <div className="h-[600px] w-[600px] rounded-full bg-indigo-500/20 blur-[120px]" />
          <div className="absolute right-1/4 top-1/3 h-80 w-80 rounded-full bg-violet-500/15 blur-[100px]" />
          <div className="absolute bottom-1/4 left-1/3 h-72 w-72 rounded-full bg-fuchsia-500/10 blur-[80px]" />
        </div>

        <main className="relative z-10 w-full max-w-2xl space-y-12 text-center">
          <div className="space-y-5">
            <p className="text-sm font-semibold uppercase tracking-[0.3em] text-indigo-400/90">
              The Semantic Cut
            </p>
            <h1 className="text-5xl font-bold tracking-tight text-white sm:text-7xl md:text-8xl">
              Find the
              <span className="block bg-gradient-to-r from-indigo-300 via-violet-300 to-fuchsia-300 bg-clip-text text-transparent">
                Perfect Clips
              </span>
            </h1>
            <p className="mx-auto max-w-md text-lg text-zinc-400">
              Describe what you want in plain language. Get back precise moments
              with timestamps and dialogue.
            </p>
            <p className="mx-auto max-w-md text-lg text-zinc-400">
              Team - Shot Ok
            </p>
          </div>

          <div className="flex flex-col items-center gap-4 sm:flex-row sm:justify-center sm:gap-6">
            <Link
              href="/search"
              className="group relative inline-flex h-16 min-w-[220px] items-center justify-center gap-3 rounded-2xl px-10 text-lg font-semibold text-white shadow-2xl transition-all duration-300 hover:scale-[1.03] hover:shadow-indigo-500/30 active:scale-[0.98]"
              style={{
                background:
                  "linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #a855f7 100%)",
                boxShadow:
                  "0 0 40px -8px rgba(99, 102, 241, 0.5), 0 20px 40px -20px rgba(0,0,0,0.4)",
              }}
            >
              <span className="absolute inset-0 rounded-2xl bg-white/0 transition-colors group-hover:bg-white/10" />
              <svg
                className="size-5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                />
              </svg>
              Open search
            </Link>
            <Link
              href="/telugu-search"
              className="group relative inline-flex h-16 min-w-[220px] items-center justify-center gap-3 rounded-2xl border border-white/15 bg-white/5 px-10 text-lg font-semibold text-white transition-all duration-300 hover:scale-[1.03] hover:bg-white/10 active:scale-[0.98]"
            >
              <span className="absolute inset-0 rounded-2xl bg-white/0 transition-colors group-hover:bg-white/5" />
              Telugu Search
            </Link>
          </div>

          <div className="flex flex-wrap justify-center gap-8 pt-8 text-sm text-zinc-500">
            <span className="flex items-center gap-2">
              <span className="size-2 rounded-full bg-emerald-500/80" />
              Natural language
            </span>
            <span className="flex items-center gap-2">
              <span className="size-2 rounded-full bg-violet-500/80" />
              Timestamps & dialogue
            </span>
            <span className="flex items-center gap-2">
              <span className="size-2 rounded-full bg-indigo-500/80" />
              Instant playback
            </span>
          </div>
        </main>
      </div>
    </div>
  );
}
