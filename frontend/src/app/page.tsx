import Link from "next/link";

export default function Home() {
  return (
    <div className="grid-bg relative h-screen overflow-hidden">
      <div className="relative z-10 flex h-full flex-col items-center px-4 py-4">
        <div className="absolute inset-0 flex items-center justify-center overflow-hidden">
          <div className="h-[600px] w-[600px] rounded-full bg-indigo-500/20 blur-[120px]" />
          <div className="absolute right-1/4 top-1/3 h-80 w-80 rounded-full bg-violet-500/15 blur-[100px]" />
          <div className="absolute bottom-1/4 left-1/3 h-72 w-72 rounded-full bg-fuchsia-500/10 blur-[80px]" />
        </div>

        <main className="relative z-10 flex flex-1 flex-col items-center justify-center w-full max-w-5xl space-y-4 text-center">
          <div className="space-y-2">
            <p className="text-base font-semibold uppercase tracking-[0.3em] text-indigo-400/90">
              The Semantic Cut
            </p>
            <h1 className="text-5xl font-bold tracking-tight text-white sm:text-6xl md:text-7xl">
              Find the
              <span className="block bg-gradient-to-r from-indigo-300 via-violet-300 to-fuchsia-300 bg-clip-text text-transparent">
                Perfect Clips
              </span>
            </h1>
            <p className="mx-auto max-w-xl text-base text-zinc-400">
              Describe what you want in plain language. Get back precise moments
              with timestamps and dialogue.
            </p>
          </div>

          <div className="flex flex-col items-center gap-3 sm:flex-row sm:justify-center sm:gap-6">
            <Link
              href="/search"
              className="group relative inline-flex h-16 min-w-[220px] items-center justify-center gap-3 rounded-2xl px-10 text-base font-semibold text-white shadow-2xl transition-all duration-300 hover:scale-[1.03] hover:shadow-indigo-500/30 active:scale-[0.98]"
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
              className="group relative inline-flex h-16 min-w-[220px] items-center justify-center gap-3 rounded-2xl border border-white/15 bg-white/5 px-10 text-base font-semibold text-white transition-all duration-300 hover:scale-[1.03] hover:bg-white/10 active:scale-[0.98]"
            >
              <span className="absolute inset-0 rounded-2xl bg-white/0 transition-colors group-hover:bg-white/5" />
              Telugu Search
            </Link>
          </div>

          <div className="flex flex-wrap justify-center gap-6 pt-2 text-base text-zinc-500">
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

          <div className="relative z-10 mt-4 grid w-full max-w-5xl grid-cols-1 gap-4 md:grid-cols-5">
            <section className="rounded-xl border border-white/10 bg-white/5 px-5 py-4 backdrop-blur-sm text-left md:col-span-4">
              <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
              <p className="text-xs font-semibold uppercase tracking-widest text-indigo-400/90">
                Problem Statement 4
              </p>
              <h2 className="text-lg font-semibold text-white">
                Semantic Footage Search Engine
              </h2>
            </div>
            <p className="mb-4 mt-2 text-sm leading-snug text-zinc-400">
              Editors struggle to find footage using intent-based queries like
              &ldquo;hesitant reaction before answering.&rdquo; We built a
              semantic search engine: index from transcripts, natural language
              search, ranked clips with timestamps and confidence scores.
              </p>
              <div className="grid grid-cols-2 gap-x-6 gap-y-3 sm:grid-cols-4">
              <div>
                <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-zinc-500">
                  Functional
                </p>
                <ul className="space-y-1 text-sm text-zinc-400">
                  <li className="flex items-center gap-2">
                    <span className="size-1.5 rounded-full bg-emerald-500/80" />
                    Index from transcripts
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="size-1.5 rounded-full bg-emerald-500/80" />
                    Natural language queries
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="size-1.5 rounded-full bg-emerald-500/80" />
                    Ranked clips + timestamps
                  </li>
                </ul>
              </div>
              <div>
                <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-zinc-500">
                  AI
                </p>
                <ul className="space-y-1 text-sm text-zinc-400">
                  <li className="flex items-center gap-2">
                    <span className="size-1.5 rounded-full bg-violet-500/80" />
                    Text embeddings
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="size-1.5 rounded-full bg-violet-500/80" />
                    Vector DB / similarity
                  </li>
                  <li className="flex items-center gap-2">
                    <span className="size-1.5 rounded-full bg-violet-500/80" />
                    Semantic ranking
                  </li>
                </ul>
              </div>
              <div className="col-span-2 flex flex-wrap items-center gap-x-4 gap-y-1 border-l border-white/10 pl-4 text-xs text-zinc-500 sm:pl-4">
                <span><strong className="text-zinc-400">Inputs:</strong> Transcripts, natural language query</span>
                <span><strong className="text-zinc-400">Outputs:</strong> Ranked clips, timestamps, confidence</span>
                <span><strong className="text-zinc-400">Scope:</strong> Text-only, max 20 clips, 24h</span>
              </div>
              </div>
            </section>

            <aside className="rounded-xl border border-white/10 bg-white/5 px-5 py-4 backdrop-blur-sm text-left md:col-span-1">
              <p className="mb-3 text-xs font-semibold uppercase tracking-widest text-indigo-400/80">
                Team Shot Ok
              </p>
              <ul className="space-y-2 text-sm text-zinc-400">
                <li>Syed Aawaiz Ashraf</li>
                <li>Rahul Tej Mora</li>
                <li>Sai Siddhartha Surineni</li>
              </ul>
            </aside>
          </div>
        </main>
      </div>
    </div>
  );
}
