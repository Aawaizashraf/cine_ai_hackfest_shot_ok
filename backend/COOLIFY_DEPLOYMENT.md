# Deploying Backend on Coolify (Dockerfile)

## 1. Create a new resource in Coolify

- **Type:** Application (or Docker Compose if you prefer)
- **Source:** Git repository → your repo (e.g. `Aawaizashraf/cine_ai_hackfest_shot_ok`)
- **Branch:** `main` (or your default branch)

## 2. Build settings

- **Build Pack:** Dockerfile
- **Dockerfile path:** `backend/Dockerfile`
- **Build context:** `backend`  
  (So Coolify runs the build with context = `backend/`; the Dockerfile’s `COPY . .` will only copy the backend folder.)

If Coolify only has “Dockerfile path” and no separate “Build context”:
- Set **Dockerfile path** to `backend/Dockerfile`
- Set **Root directory** or **Context** to `backend` if available.  
- If you can only set the repo root: move or duplicate the Dockerfile to the repo root and set `COPY backend/ .` and adjust paths, or use a build context of `backend` in the build command.

## 3. Port

- **Port:** `8000` (the app listens on 0.0.0.0:8000)

## 4. Environment variables

In Coolify → your application → **Environment Variables**, add:

| Variable | Required | Example / note |
|----------|----------|-----------------|
| `OPENROUTER_API_KEY` | Yes | Your OpenRouter API key |
| `QDRANT_URL` | Yes | `https://xxx.gcp.cloud.qdrant.io` or `http://localhost:6333` |
| `QDRANT_API_KEY` | If using Qdrant Cloud | Your Qdrant API key |
| `CORS_ORIGINS` | Yes (for deployed FE) | Your frontend URL, e.g. `https://your-app.vercel.app` (comma-separated if multiple) |
| `SILICONFLOW_API_KEY` | Yes (for rerank) | Your SiliconFlow API key |
| `VIDEO_PATH` | Yes (for clip playback) | Path **inside the container** where the video is mounted, e.g. `/data/video/movie.mp4` |
| `OPENAI_API_KEY` | Only for Telugu search | Your OpenAI API key if you use Telugu search |

Optional (have defaults):

- `LOG_LEVEL` (e.g. `INFO`)
- `COLLECTION_NAME`
- `SEARCH_RERANK_TOP`, `SEARCH_INITIAL_K`, etc.

## 5. Video file (persistent storage)

The image does **not** contain the movie file. You must make it available inside the container.

### Option A: Coolify “Storage” / “Volumes”

1. In Coolify → your application → **Storage** / **Volumes**.
2. Add a volume:
   - **Container path:** `/data/video`
   - **Host path:** Choose a path on the Coolify server where you will put the file (e.g. `/data/cine-ai/video`).
3. On the Coolify server (SSH or console), copy your movie file into that host path, e.g.:
   ```bash
   mkdir -p /data/cine-ai/video
   # Copy your file there, e.g.:
   cp /path/to/The.Godfather.1972....mp4 /data/cine-ai/video/movie.mp4
   ```
4. Set env var: **`VIDEO_PATH=/data/video/movie.mp4`** (must match the filename you used).

### Option B: Upload via Coolify file manager

If Coolify lets you upload files into a volume or a mounted path, upload the movie to the path that is mounted as `/data/video` in the container, then set **`VIDEO_PATH=/data/video/<filename>.mp4`**.

### Option C: No video (search only)

If you don’t need clip playback:

- Leave **`VIDEO_PATH`** unset or set it to a non-existent path.
- Search and metadata will work; the frontend may show 404 or “video not found” when playing clips.

## 6. Deploy

- Save the application and run **Deploy**.
- After deploy, open **https://your-coolify-domain** (or the URL Coolify gives you). You should see the API root message and be able to call e.g. `/api/v1/...`.

## 7. Frontend

- Set the frontend’s **`NEXT_PUBLIC_API_URL`** to your Coolify backend URL (e.g. `https://api.yourdomain.com`).
- Ensure **`CORS_ORIGINS`** on the backend includes that frontend origin exactly (e.g. `https://your-app.vercel.app`).

## Quick checklist

- [ ] Build: Dockerfile = `backend/Dockerfile`, context = `backend`
- [ ] Port 8000 exposed
- [ ] `OPENROUTER_API_KEY`, `QDRANT_URL`, `QDRANT_API_KEY` (if cloud), `CORS_ORIGINS`, `SILICONFLOW_API_KEY` set
- [ ] Video: volume mounted at `/data/video`, file copied/uploaded, `VIDEO_PATH=/data/video/<filename>.mp4`
- [ ] Frontend `NEXT_PUBLIC_API_URL` points to this backend URL
