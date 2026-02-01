"use client";

import Link from "next/link";
import { useState } from "react";
import { FileJson, Loader2, Home, Copy, Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { screenplayToJson } from "@/lib/api";

export default function ScreenplayPage() {
  const [transcript, setTranscript] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<unknown>(null);
  const [copied, setCopied] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const text = transcript.trim();
    if (!text) return;
    setError(null);
    setResult(null);
    setLoading(true);
    try {
      const data = await screenplayToJson(text);
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Conversion failed");
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = async () => {
    if (!result) return;
    try {
      await navigator.clipboard.writeText(JSON.stringify(result, null, 2));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  };

  return (
    <div className="grid-bg relative min-h-screen">
      <div className="relative z-10 flex min-h-screen flex-col">
        <header className="sticky top-0 z-20 border-b border-white/5 bg-black/40 backdrop-blur-2xl">
          <div className="mx-auto flex w-full max-w-6xl items-center justify-between gap-4 px-4 py-5 sm:px-6 lg:max-w-7xl">
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-white sm:text-3xl">
                Screenplay to JSON
              </h1>
              <p className="mt-0.5 text-sm text-zinc-400">
                Paste a screenplay scene; get structured JSON (scene_id, clips, dialogue)
              </p>
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
            <form onSubmit={handleSubmit} className="flex flex-col gap-4">
              <label htmlFor="transcript" className="text-sm font-medium text-zinc-300">
                Screenplay / transcript
              </label>
              <textarea
                id="transcript"
                placeholder="e.g.&#10;5 INT. OFFICE - DAY 5&#10;KARTHIK enters the room, looking anxious. His BOSS sits behind the desk.&#10;BOSS&#10;(without looking up)&#10;You're late again.&#10;KARTHIK&#10;Sorry sir, traffic was bad."
                value={transcript}
                onChange={(e) => setTranscript(e.target.value)}
                rows={12}
                className="w-full resize-y rounded-xl border border-white/10 bg-white/10 px-4 py-3 text-sm text-white placeholder:text-zinc-500 focus:border-indigo-500/50 focus:outline-none focus:ring-2 focus:ring-indigo-500/30"
                disabled={loading}
              />
              <Button
                type="submit"
                disabled={loading}
                className="shrink-0 self-start rounded-xl px-8 font-semibold text-white shadow-lg transition-all hover:scale-[1.02] active:scale-[0.98]"
                style={{
                  background: "linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)",
                  boxShadow: "0 0 24px -4px rgba(99, 102, 241, 0.4)",
                }}
              >
                {loading ? (
                  <>
                    <Loader2 className="size-5 animate-spin" />
                    Converting…
                  </>
                ) : (
                  <>
                    <FileJson className="size-5" />
                    Convert to JSON
                  </>
                )}
              </Button>
            </form>
          </div>

          {error && (
            <div className="mt-6 rounded-xl border border-red-500/30 bg-red-500/10 px-5 py-4 text-sm text-red-300">
              {error}
            </div>
          )}

          {result !== null && !error && (
            <section className="mt-6">
              <div className="mb-3 flex items-center justify-between">
                <h2 className="text-lg font-semibold text-white">Structured JSON</h2>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={handleCopy}
                  className="inline-flex gap-2 rounded-lg border-white/15 bg-white/5 text-zinc-300 hover:bg-white/10"
                >
                  {copied ? (
                    <>
                      <Check className="size-4" />
                      Copied
                    </>
                  ) : (
                    <>
                      <Copy className="size-4" />
                      Copy
                    </>
                  )}
                </Button>
              </div>
              <pre className="max-h-[60vh] overflow-auto rounded-xl border border-white/10 bg-zinc-900/80 p-4 text-left text-sm text-zinc-300">
                <code>{JSON.stringify(result, null, 2)}</code>
              </pre>
            </section>
          )}
        </main>
      </div>
    </div>
  );
}
