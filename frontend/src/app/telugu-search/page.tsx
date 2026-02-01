"use client";

import Link from "next/link";
import { useState, useCallback } from "react";
import { Search, Loader2, Home } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ClipCard } from "@/components/ClipCard";
import {
  teluguSearchStream,
  type SearchResult,
  type SearchStreamStatus,
} from "@/lib/api";

export default function TeluguSearchPage() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [statuses, setStatuses] = useState<Record<string, SearchStreamStatus>>(
    {},
  );

  const onStatus = useCallback((data: SearchStreamStatus) => {
    setStatuses((prev) => ({ ...prev, [data.id]: data }));
  }, []);

  const onResults = useCallback((data: SearchResult[]) => {
    setResults(data);
    setLoading(false);
  }, []);

  const onError = useCallback((message: string) => {
    setError(message);
    setLoading(false);
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const q = query.trim();
    if (!q) return;
    setError(null);
    setResults([]);
    setStatuses({});
    setLoading(true);

    try {
      await teluguSearchStream(q, 10, onStatus, onResults, onError);
    } catch (err) {
      onError(err instanceof Error ? err.message : "Telugu search failed");
    }
  };

  const stepOrder = ["embedding", "vector_search"];

  return (
    <div className="grid-bg relative min-h-screen">
      <div className="relative z-10 flex min-h-screen flex-col">
        <header className="sticky top-0 z-20 border-b border-white/5 bg-black/40 backdrop-blur-2xl">
          <div className="mx-auto flex w-full max-w-6xl items-center justify-between gap-4 px-4 py-5 sm:px-6 lg:max-w-7xl">
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-white sm:text-3xl">
                Telugu Search
              </h1>
            </div>
            <Link href="/">
              <Button
                variant="outline"
                size="sm"
                className="rounded-xl border-white/15 bg-white/5 font-medium text-white hover:bg-white/15"
              >
                <Home className="size-4" />
                Home
              </Button>
            </Link>
          </div>
        </header>

        <main className="relative z-10 mx-auto w-full max-w-6xl flex-1 px-4 py-6 sm:px-6 lg:max-w-7xl">
          <div className="rounded-2xl border border-white/10 bg-white/5 p-6 shadow-2xl backdrop-blur-xl sm:p-8">
            <form
              onSubmit={handleSubmit}
              className="flex flex-col gap-4 sm:flex-row sm:items-stretch sm:gap-4"
            >
              <Input
                type="text"
                placeholder="e.g. wedding scene, anger or aggression..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="min-h-14 flex-1 rounded-xl border-white/10 bg-white/10 px-5 py-4 text-base text-white placeholder:text-zinc-500 focus-visible:border-indigo-500/50 focus-visible:ring-2 focus-visible:ring-indigo-500/30"
                disabled={loading}
              />
              <Button
                type="submit"
                disabled={loading}
                className="min-h-14 shrink-0 rounded-xl px-8 font-semibold text-white shadow-lg transition-all hover:scale-[1.02] active:scale-[0.98]"
                style={{
                  background:
                    "linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)",
                  boxShadow: "0 0 24px -4px rgba(99, 102, 241, 0.4)",
                }}
              >
                {loading ? (
                  <>
                    <Loader2 className="size-5 animate-spin" />
                    Searching
                  </>
                ) : (
                  <>
                    <Search className="size-5" />
                    Search
                  </>
                )}
              </Button>
            </form>
          </div>

          <div className="mt-6">
            <p className="mb-3 text-sm font-medium text-zinc-400">
              Suggested searches — click to use
            </p>
            <ul className="flex flex-wrap gap-2">
              {[
                "Friends having fun or comedy scene",
                "Wedding or celebration",
                "Emotional or serious conversation",
                "Road trip or travel",
                "Group of friends arguing or joking",
                "Romantic moment",
                "Someone giving advice",
                "Party or night out scene",
                "Karthink baitiki vellinappudu",
                "guys doing godawa",
                "guessing wine",
                "vivek attitude chupiyadam",
                "Agnry vivek",
              ].map((suggestion) => (
                <li key={suggestion}>
                  <button
                    type="button"
                    onClick={() => setQuery(suggestion)}
                    className="rounded-lg border border-white/15 bg-white/5 px-4 py-2 text-left text-sm text-zinc-300 transition-colors hover:bg-white/10 hover:text-white"
                  >
                    {suggestion}
                  </button>
                </li>
              ))}
            </ul>
          </div>

          {error && (
            <div className="mt-6 rounded-xl border border-red-500/30 bg-red-500/10 px-5 py-4 text-sm text-red-300">
              {error}
            </div>
          )}

          {loading && (
            <ul className="mt-8 grid gap-2 sm:grid-cols-2">
              {stepOrder.map((id) => {
                const s = statuses[id];
                if (!s) return null;
                return (
                  <li
                    key={id}
                    className="flex items-center gap-3 rounded-xl border border-white/5 bg-white/5 px-4 py-3 text-sm text-zinc-400"
                  >
                    {s.status === "loading" ? (
                      <Loader2 className="size-4 shrink-0 animate-spin text-indigo-400" />
                    ) : (
                      <span
                        className="size-2.5 shrink-0 rounded-full bg-emerald-500"
                        aria-hidden
                      />
                    )}
                    <span>{s.message}</span>
                  </li>
                );
              })}
            </ul>
          )}

          {!loading && results.length > 0 && (
            <section className="mt-6">
              <div className="mb-4 flex items-baseline justify-between">
                <h2 className="text-2xl font-bold text-white">
                  {results.length} result{results.length !== 1 ? "s" : ""}
                </h2>
              </div>
              <ul className="space-y-4">
                {results.map((r) => (
                  <li key={r.clip_id}>
                    <ClipCard result={r} hideVideo />
                  </li>
                ))}
              </ul>
            </section>
          )}

          {!loading && results.length === 0 && !error && query.trim() && (
            <p className="mt-16 text-center text-zinc-500">
              No clips found. Try a different query or ensure OPENAI_API_KEY and
              Telugu collection are set.
            </p>
          )}
        </main>
      </div>
    </div>
  );
}
