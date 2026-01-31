const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/** URL for the movie file (clip playback). GET with Range for seeking. */
export const VIDEO_URL = `${API_BASE}/api/v1/video`;

export type SearchResult = {
  clip_id: string;
  video_id: string | null;
  start: number;
  end: number;
  text: string;
  score: number;
  match_score: number;
  confidence: string | null;
  metadata: Record<string, unknown> | null;
};

export type SearchStreamStatus = {
  id: string;
  status: "loading" | "done";
  message: string;
  intent_preview?: string;
  filters?: Record<string, unknown>;
};

export async function searchStream(
  query: string,
  limit: number = 10,
  onStatus: (data: SearchStreamStatus) => void,
  onResults: (data: SearchResult[]) => void,
  onError: (message: string) => void
): Promise<void> {
  const res = await fetch(`${API_BASE}/api/v1/search/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, limit }),
  });

  if (!res.ok) {
    onError(res.statusText || "Search failed");
    return;
  }

  const reader = res.body?.getReader();
  if (!reader) {
    onError("No response body");
    return;
  }

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

        for (const line of lines) {
      if (line.startsWith("data:")) {
        const payload = line.slice(5).trim();
        if (payload === "[DONE]") return;
        try {
          const data = JSON.parse(payload) as {
            type?: string;
            data?: unknown;
            errorText?: string;
          };
          if (data.type === "data-status" && data.data && typeof data.data === "object") {
            const d = data.data as SearchStreamStatus;
            onStatus(d);
          } else if (data.type === "results" && Array.isArray(data.data)) {
            onResults(data.data as SearchResult[]);
            return;
          } else if (data.type === "error" && data.errorText) {
            onError(data.errorText);
            return;
          }
        } catch {
          // skip malformed lines
        }
      }
    }
  }
  // Stream ended without results event (e.g. empty response)
  onResults([]);
}

/** Telugu/Tenglish search stream — same callback shape as searchStream. */
export async function teluguSearchStream(
  query: string,
  limit: number = 10,
  onStatus: (data: SearchStreamStatus) => void,
  onResults: (data: SearchResult[]) => void,
  onError: (message: string) => void
): Promise<void> {
  const res = await fetch(`${API_BASE}/api/v1/telugu-search/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, limit }),
  });

  if (!res.ok) {
    onError(res.statusText || "Telugu search failed");
    return;
  }

  const reader = res.body?.getReader();
  if (!reader) {
    onError("No response body");
    return;
  }

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    for (const line of lines) {
      if (line.startsWith("data:")) {
        const payload = line.slice(5).trim();
        if (payload === "[DONE]") return;
        try {
          const data = JSON.parse(payload) as {
            type?: string;
            data?: unknown;
            errorText?: string;
          };
          if (data.type === "data-status" && data.data && typeof data.data === "object") {
            onStatus(data.data as SearchStreamStatus);
          } else if (data.type === "results" && Array.isArray(data.data)) {
            onResults(data.data as SearchResult[]);
            return;
          } else if (data.type === "error" && data.errorText) {
            onError(data.errorText);
            return;
          }
        } catch {
          // skip
        }
      }
    }
  }
  onResults([]);
}
