"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { Play } from "lucide-react";
import { Button } from "@/components/ui/button";
import { VIDEO_URL, type SearchResult } from "@/lib/api";
import { cn } from "@/lib/utils";

type DialogueLine = { actor?: string; text?: string };

function formatTime(sec: number): string {
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function formatIntExtTime(intExt: string, timeOfDay: string): string {
  const parts: string[] = [];
  const intExtMap: Record<string, string> = {
    INT: "Interior",
    EXT: "Exterior",
    MIXED: "Mixed",
  };
  const timeMap: Record<string, string> = {
    DAY: "Day",
    NIGHT: "Night",
    EVENING: "Evening",
    MORNING: "Morning",
    DUSK: "Dusk",
    DAWN: "Dawn",
  };
  const ie = (intExt || "").trim().toUpperCase();
  const to = (timeOfDay || "").trim().toUpperCase();
  if (ie && intExtMap[ie]) parts.push(intExtMap[ie]);
  else if (ie) parts.push(ie.charAt(0) + ie.slice(1).toLowerCase());
  if (to && timeMap[to]) parts.push(timeMap[to]);
  else if (to) parts.push(to.charAt(0) + to.slice(1).toLowerCase());
  return parts.join(", ") || "";
}

const DEFAULT_VIDEO_DURATION_SEC = 10500;

type ClipCardProps = { result: SearchResult; hideVideo?: boolean };

export function ClipCard({ result, hideVideo = false }: ClipCardProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const meta = result.metadata as {
    scene_id?: string;
    location?: string;
    int_ext?: string;
    time_of_day?: string;
    start_display?: string;
    end_display?: string;
    actors?: string[];
    dialogue?: DialogueLine[];
  } | undefined;
  const sceneId = meta?.scene_id ?? result.video_id ?? "";
  const location = meta?.location ?? "";
  const intExt = meta?.int_ext ?? "";
  const timeOfDay = meta?.time_of_day ?? "";
  const rawStart = Number(result.start) || 0;
  const rawEnd = Number(result.end) || 0;
  const hasValidTimestamps = rawEnd > rawStart && rawStart >= 0;
  const [randomFallbackStart] = useState(() => {
    if (hasValidTimestamps) return 0;
    const maxStart = Math.max(0, DEFAULT_VIDEO_DURATION_SEC - 60);
    return Math.floor(Math.random() * maxStart);
  });
  const start = hasValidTimestamps ? rawStart : randomFallbackStart;
  const end = hasValidTimestamps ? rawEnd : randomFallbackStart + 60;
  const startDisplay = meta?.start_display ?? formatTime(start);
  const endDisplay = meta?.end_display ?? formatTime(end);
  const timeLabel = `${Math.floor(start)}s – ${Math.floor(end)}s`;
  const actorsList = meta?.actors ?? [];
  const dialogue = meta?.dialogue ?? [];
  const isFallbackClip = !hasValidTimestamps;
  const matchScore = result.match_score ?? result.score ?? 0;

  const playClip = useCallback(() => {
    const video = videoRef.current;
    if (!video) return;
    video.currentTime = start;
    video.play().catch(() => {});
  }, [start]);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;
    const onTimeUpdate = () => {
      if (video.currentTime >= end) video.pause();
    };
    video.addEventListener("timeupdate", onTimeUpdate);
    return () => video.removeEventListener("timeupdate", onTimeUpdate);
  }, [end]);

  const onLoadedMetadata = useCallback(() => {
    const video = videoRef.current;
    if (video) video.currentTime = start;
  }, [start]);

  const dialoguePreview = dialogue.slice(0, 4);
  const hasMoreDialogue = dialogue.length > 4;

  return (
    <article
      className={cn(
        "grid min-w-0 grid-cols-1 overflow-hidden rounded-xl border border-white/10 bg-zinc-900/80 shadow-xl backdrop-blur-sm",
        !hideVideo && "sm:grid-cols-2"
      )}
      style={{ boxShadow: "0 0 0 1px rgba(255,255,255,0.05), 0 16px 32px -12px rgba(0,0,0,0.4)" }}
    >
      <div className={cn("scrollbar-styled flex min-h-0 min-w-0 flex-col overflow-y-auto", !hideVideo && "sm:col-start-1 sm:row-start-1")}>
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/5 px-5 py-3">
          <div className="flex flex-wrap items-center gap-2">
            {sceneId && (
              <span className="rounded px-2.5 py-1 text-xs font-semibold text-amber-400/95 bg-amber-500/20">
                {sceneId}
              </span>
            )}
            {location && (
              <span className="rounded px-2.5 py-1 text-xs font-semibold text-indigo-400/95 bg-indigo-500/20">
                {location}
              </span>
            )}
            {formatIntExtTime(intExt, timeOfDay) && (
              <span className="rounded px-2.5 py-1 text-xs font-medium text-zinc-300 bg-zinc-500/20">
                {formatIntExtTime(intExt, timeOfDay)}
              </span>
            )}
          </div>
          <span
            className={cn(
              "shrink-0 rounded-full px-2.5 py-1 text-xs font-medium",
              result.confidence === "High" && "bg-emerald-500/20 text-emerald-400",
              result.confidence === "Medium" && "bg-amber-500/20 text-amber-400",
              (result.confidence === "Low" || !result.confidence) && "bg-zinc-500/20 text-zinc-400"
            )}
          >
            {result.confidence === "High"
              ? "High"
              : result.confidence === "Medium"
                ? "Medium"
                : "Relevant"}
            {typeof matchScore === "number" && matchScore !== 0 ? ` ${matchScore.toFixed(2)}` : ""}
          </span>
        </div>
        <div className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-2 border-b border-white/5 px-5 py-4 text-sm">
          <span className="text-xs font-semibold uppercase tracking-wider text-zinc-500">Clip ID</span>
          <span className="truncate font-medium text-white">{result.clip_id}</span>
          <span className="text-xs font-semibold uppercase tracking-wider text-zinc-500">Actors</span>
          <div className="flex flex-wrap gap-1.5">
            {actorsList.length > 0
              ? actorsList.map((a, i) => (
                  <span key={i} className="rounded-full border border-white/10 bg-white/5 px-2.5 py-0.5 text-xs text-zinc-300">
                    {a}
                  </span>
                ))
              : "—"}
          </div>
          <span className="text-xs font-semibold uppercase tracking-wider text-zinc-500">Time</span>
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-white">{timeLabel}</span>
            {isFallbackClip && (
              <span className="rounded bg-amber-500/20 px-2 py-0.5 text-xs font-medium text-amber-400">
                Random 1-min clip
              </span>
            )}
          </div>
        </div>
        <div className="border-b border-white/5 px-5 py-4">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-zinc-500">Visual action</p>
          <div className="scrollbar-styled max-h-24 overflow-y-auto rounded-lg border border-white/5 bg-black/30 px-3 py-2">
            <p className="text-sm leading-relaxed text-zinc-300">{result.text || "—"}</p>
          </div>
        </div>
        {dialogue.length > 0 && (
          <div className={hideVideo ? "px-5 py-4" : "border-b border-white/5 px-5 py-4"}>
            <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-zinc-500">Dialogue</p>
            <ul className="space-y-1.5 text-sm text-zinc-300">
              {dialoguePreview.map((line, i) => (
                <li key={i} className="flex gap-2">
                  {line.actor && (
                    <span className="shrink-0 font-semibold text-indigo-400/90">{line.actor}:</span>
                  )}
                  <span>{line.text ?? "—"}</span>
                </li>
              ))}
              {hasMoreDialogue && <li className="text-zinc-500">+{dialogue.length - 4} more</li>}
            </ul>
          </div>
        )}
        {!hideVideo && (
          <div className="flex flex-wrap items-center gap-2 px-5 py-3">
            <Button
              type="button"
              size="sm"
              onClick={playClip}
              className="gap-2 rounded-xl font-semibold text-white transition-all hover:scale-[1.02] active:scale-[0.98]"
              style={{
                background: "linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)",
                boxShadow: "0 0 20px -4px rgba(99, 102, 241, 0.4)",
              }}
            >
              <Play className="size-4" />
              Play {startDisplay} – {endDisplay}
            </Button>
            {isFallbackClip && (
              <span className="rounded bg-amber-500/20 px-1.5 py-0.5 text-xs text-amber-400/90">Random 1-min</span>
            )}
          </div>
        )}
      </div>
      {!hideVideo && (
        <div className="min-w-0 aspect-video w-full overflow-hidden bg-black sm:col-start-2 sm:row-start-1 sm:aspect-auto sm:min-h-[200px]">
          <video
            ref={videoRef}
            src={VIDEO_URL}
            className="h-full w-full object-contain"
            controls
            preload="metadata"
            playsInline
            onLoadedMetadata={onLoadedMetadata}
          />
        </div>
      )}
    </article>
  );
}
