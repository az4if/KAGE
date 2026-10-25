# KAGE

KAGE is a self-hosted anime browsing and streaming web app. It provides a
browser UI for searching anime, viewing episode information, selecting
sub/dub servers, and playing HLS streams returned by the KAGE API.

The project is split into two services:

```text
Browser
   │
   ▼
Frontend: app.py  ── http://localhost:6767
   │
   ▼
API: KAGE_API/reanime.py  ── http://localhost:8787
   │
   ├── reanime.to       metadata and episode information
   └── flixcloud.cc     stream data and subtitles
```

> **Notice:** KAGE accesses third-party services and displays streams supplied
> by those services. Make sure your use complies with the laws and terms that
> apply to you. KAGE does not host or own the streamed content.

## Requirements

- Windows
- Python 3.11 or newer
- Node.js 20 or newer
- Internet access

The frontend uses Flask and `curl-cffi`. The API uses FastAPI, Uvicorn,
`curl-cffi`, and Node.js to run the stream decryption helper.

## Quick start on Windows

1. Open two Command Prompt or PowerShell windows in the project directory.
2. Start the API first:

   ```bat
   api.bat
   ```

3. Start the frontend in the second window:

   ```bat
   app.bat
   ```

4. Open <http://localhost:6767> in a browser.

The batch files check for Python and Node.js and install the primary Python
packages when they are missing. If a dependency error occurs, install the
complete set manually:

```powershell
python -m pip install flask curl-cffi fastapi "uvicorn[standard]" "httpx[http2]" pycryptodome
```

## Manual startup

If you prefer not to use the batch files:

```powershell
python -m pip install flask curl-cffi fastapi "uvicorn[standard]" "httpx[http2]" pycryptodome
```

Start the API:

```powershell
Set-Location .\KAGE_API
python reanime.py
```

In a second terminal, from the project root, start the frontend:

```powershell
python app.py
```

The services listen on all network interfaces:

| Service | Default URL | File |
| --- | --- | --- |
| Frontend | <http://localhost:6767> | `app.py` |
| API | <http://localhost:8787> | `KAGE_API/reanime.py` |

Press `Ctrl+C` in each terminal to stop a service.

## Configuration

The frontend reads the API address from [`_KEY.txt`](_KEY.txt):

```text
BASE_API_URL=http://localhost:8787
```

To use an API running on another machine or port, change the value and restart
the frontend. `app.py` generates the browser-facing `config.js` response from
this file; [`config.js`](config.js) is also the default client-side
configuration.

For a local setup, keep the API URL as `http://localhost:8787`. The frontend
also exposes proxy endpoints for HLS playlists, media segments, and subtitle
files so the browser can play the returned streams.

## Features

- Home page with current and popular anime
- Anime search
- Anime details and episode lists
- Weekly airing schedule
- Subbed and dubbed server selection
- HLS playback with Hls.js
- Subtitle and thumbnail support
- Intro/outro chapter metadata when available
- Responsive dark-themed UI
- Favicon and PWA assets

## Project structure

```text
KAGE/
├── app.html                 # KAGE browser UI
├── app.py                   # Frontend server and media proxy
├── app.bat                  # Windows frontend launcher
├── _KEY.txt                 # Frontend-to-API URL configuration
├── config.js                # Client-side API configuration default
├── api.bat                  # Windows API launcher
├── KAGE_API/
│   ├── reanime.py           # FastAPI API and upstream integrations
│   ├── decrypt.mjs          # Node.js stream decryption helper
│   └── README.md             # API-specific documentation
├── favicons/                # Browser, mobile, and Windows icon assets
├── site.webmanifest         # PWA manifest
└── KAGE_FLOW.svg            # Service connection diagram
```

## API endpoints

The API is available at the configured `BASE_API_URL`:

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/search?q=...&limit=20` | Search anime |
| `GET` | `/home?limit=20` | Latest anime and weekly picks |
| `GET` | `/top?period=week&limit=20` | Top anime by period |
| `GET` | `/schedule` | Weekly airing schedule |
| `GET` | `/info/{slug}` | Anime metadata and episodes |
| `GET` | `/episodes/{slug}` | Episode list |
| `GET` | `/servers/{slug}/{episode}` | Available sub/dub servers |
| `GET` | `/stream/{access_id}?v=2` | Resolve a stream |
| `GET` | `/stream/from-link?link={url}` | Resolve a full stream link |
| `GET` | `/thumbnails/{anilist_id}` | Episode thumbnail data |
| `GET` | `/recommendations/{slug}` | Related anime |

The API also provides automatic OpenAPI documentation at:

- <http://localhost:8787/docs>
- <http://localhost:8787/redoc>

## Troubleshooting

### The page cannot connect to the API

Confirm that `api.bat` is running and that
[`_KEY.txt`](_KEY.txt) points to the same host and port. Test the API
directly by opening <http://localhost:8787/docs>.

### Python or Node.js is not found

Install Python 3.11+ and Node.js 20+, then ensure both commands are available
on `PATH`:

```powershell
python --version
node --version
```

Restart the terminal after changing `PATH`.

### Stream resolution fails

Stream tokens and URLs supplied by the upstream service are short-lived and
may be single-use. Retry from the episode page and avoid reusing an old
stream URL. Upstream availability, rate limits, or changes to the third-party
sites can also prevent playback.

### Port already in use

Stop the process using port 6767 or 8787, or update the application launch
configuration and the corresponding `BASE_API_URL` value consistently.

## Development notes

- `app.py` serves the UI and proxies HLS/subtitle requests.
- `KAGE_API/reanime.py` exposes the metadata and stream API.
- `KAGE_API/decrypt.mjs` is invoked by the API for the upstream stream
  decryption flow.
- Do not commit private API keys, cookies, or other credentials to the
  repository.

