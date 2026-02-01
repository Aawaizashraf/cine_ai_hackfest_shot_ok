# How to Get the Video Into Docker

The app needs the movie file to serve clip playback. You have two options.

---

## Option A: Bake the video into the image (build locally, then use in Coolify)

Use this when you want the video **inside** the image so you don’t need a volume.

### 1. Put the video in the build context

On your machine:

```bash
cd /path/to/cine_ai_hackathon/backend

# Copy your movie file into the video folder (name it movie.mp4)
cp "/path/to/your/The.Godfather.1972....mp4" video/movie.mp4
```

The file must be at **`backend/video/movie.mp4`**. It is gitignored so it won’t be committed.

### 2. Build the image

From the **backend** directory (so `video/` is in the build context):

```bash
cd /path/to/cine_ai_hackathon/backend
docker build -t cine-ai-backend:with-video .
```

### 3. Push to a registry

```bash
# Docker Hub (replace YOUR_USERNAME with your Docker Hub username)
docker tag cine-ai-backend:with-video YOUR_USERNAME/cine-ai-backend:with-video
docker push YOUR_USERNAME/cine-ai-backend:with-video

# Or GitHub Container Registry
docker tag cine-ai-backend:with-video ghcr.io/Aawaizashraf/cine-ai-backend:with-video
docker push ghcr.io/Aawaizashraf/cine-ai-backend:with-video
```

### 4. Use that image in Coolify

In Coolify:

- **Don’t** use “Build from Dockerfile” for this.
- Use **“Deploy pre-built image”** (or similar).
- Image: `YOUR_USERNAME/cine-ai-backend:with-video` (or your GHCR URL).
- Set env vars as usual (OPENROUTER_API_KEY, QDRANT_URL, CORS_ORIGINS, etc.).
- No need to set `VIDEO_PATH` if you used `movie.mp4` (default in the Dockerfile).

The video is inside the image; no volume needed.

---

## Option B: Volume mount (Coolify builds from Git)

Use this when Coolify **builds from Git** and you don’t want to build the image yourself.

1. In Coolify, add a **File Mount** or **Directory Mount** (e.g. host path → container path `/data/video`).
2. Copy the movie file **on the Coolify server** into that host path (e.g. with `scp`, `rsync`, or Coolify’s file manager).
3. Set env: **`VIDEO_PATH=/data/video/movie.mp4`** (match the filename you used).
4. Redeploy.

The video is on the server and mounted into the container; it is not in the image.

---

## Summary

| Goal                         | Do this                                                                 |
|-----------------------------|-------------------------------------------------------------------------|
| Video inside the image      | Put `movie.mp4` in `backend/video/`, build image locally, push, use in Coolify as pre-built image (Option A). |
| Coolify builds from Git     | Use a volume mount and put the video on the server (Option B).         |
