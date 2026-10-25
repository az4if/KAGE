#!/usr/bin/env python3
"""
KAGE Frontend Server  — port 6767
  • Serves app.html (with config.js injected + stream URLs auto-proxied)
  • GET /config.js        — dynamic JS config built from _KEY.txt
  • GET /proxy/hls?url=…  — HLS proxy (m3u8 rewrite + segment passthrough)
  • GET /proxy/sub?url=…  — Subtitle proxy (SRT / VTT)
"""

import atexit
import re
from pathlib import Path
from urllib.parse import urljoin, quote, urlparse

from curl_cffi import requests as curl_requests
from flask import Flask, request, Response, abort, send_from_directory

# ─── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR  = Path(__file__).parent
HTML_FILE = BASE_DIR / "app.html"
KEY_FILE  = BASE_DIR / "_KEY.txt"

# ─── Persistent curl_cffi client (Chrome TLS/HTTP2 fingerprint impersonation) ─
# Impersonating Chrome's TLS fingerprint bypasses Cloudflare bot detection that
# blocks standard Python HTTP clients regardless of User-Agent headers.
_CLIENT = curl_requests.Session(
    impersonate="chrome124",
    timeout=20.0,
    allow_redirects=True,
)
atexit.register(_CLIENT.close)

# ─── Proxy headers ────────────────────────────────────────────────────────────
_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
_PROXY_HEADERS = {
    "User-Agent":      _UA,
    "Accept":          "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin":          "https://flixcloud.cc",
    "Referer":         "https://flixcloud.cc/",
}

# Hosts allowed through the proxy (any sub-domain of these is also allowed)
_ALLOWED_HOSTS = {
    "flixcloud.cc",
    "reanime.to",
    "cdn.reanime.to",
    "ass.reanime.to",
    "fonts.gstatic.com",
    "overcdn.site",
    "slopnet.site",
}

app = Flask(__name__)

# ─── Helpers ──────────────────────────────────────────────────────────────────

def read_key_file() -> dict:
    """Parse KEY=VALUE pairs from _KEY.txt (ignores blank lines and # comments)."""
    cfg: dict = {}
    if KEY_FILE.exists():
        for raw in KEY_FILE.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                cfg[k.strip()] = v.strip()
    return cfg


def _proxy_url(absolute_url: str) -> str:
    """Wrap an absolute URL so it passes through the local HLS proxy."""
    return f"/proxy/hls?url={quote(absolute_url, safe='')}"


def _rewrite_m3u8(content: str, original_url: str) -> str:
    """
    Walk every line of an M3U8 and rewrite all embedded URLs to pass through
    the local proxy.  Handles:
      - Bare segment / sub-playlist URI lines
      - URI="…" attributes inside EXT tags  (#EXT-X-KEY, #EXT-X-MEDIA, etc.)
    """
    out: list[str] = []

    for raw_line in content.splitlines(keepends=False):
        line = raw_line.rstrip("\r\n")
        stripped = line.lstrip()

        if stripped.startswith("#") and 'URI="' in stripped:
            # Rewrite URI="…" in-place
            def _sub(m: re.Match) -> str:
                uri = m.group(1)
                abs_uri = uri if uri.startswith(("http://", "https://")) else urljoin(original_url, uri)
                return f'URI="{_proxy_url(abs_uri)}"'

            out.append(re.sub(r'URI="([^"]+)"', _sub, line))

        elif stripped and not stripped.startswith("#"):
            # Segment or sub-playlist URL
            abs_url = stripped if stripped.startswith(("http://", "https://")) else urljoin(original_url, stripped)
            out.append(_proxy_url(abs_url))

        else:
            out.append(line)

    return "\n".join(out)


def _host_allowed(url: str) -> bool:
    host = urlparse(url).hostname or ""
    return any(host == h or host.endswith("." + h) for h in _ALLOWED_HOSTS)


# ─── Static assets ────────────────────────────────────────────────────────────

@app.route("/favicons/<path:filename>")
def favicons(filename):
    """Serve favicon images from the favicons/ subfolder."""
    return send_from_directory(BASE_DIR / "favicons", filename)

@app.route("/site.webmanifest")
def webmanifest():
    return send_from_directory(BASE_DIR, "site.webmanifest",
                               mimetype="application/manifest+json")

@app.route("/browserconfig.xml")
def browserconfig():
    return send_from_directory(BASE_DIR, "browserconfig.xml",
                               mimetype="application/xml")


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    """
    Serve app.html with three automatic patches:
      1. Inject <script src="/config.js"> so the frontend reads BASE_API_URL.
      2. Seed the API variable from window.KAGE_CONFIG (no manual setup modal needed).
      3. Wrap the HLS stream URL through /proxy/hls so the browser never hits
         flixcloud CDN directly (which lacks Access-Control-Allow-Origin headers).
    Subtitles are already routed through /proxy/sub natively in app.html.
    """
    if not HTML_FILE.exists():
        abort(404, description="app.html not found — put it next to app.py")

    html = HTML_FILE.read_text(encoding="utf-8")

    # 1 ── config.js injection
    config_tag = '<script src="/config.js"></script>'
    if config_tag not in html:
        html = html.replace("</head>", f"  {config_tag}\n</head>", 1)

    # 2 ── API seed from KAGE_CONFIG (falls back to session storage → modal)
    html = html.replace(
        "let API = sessionStorage.getItem('reanime_api') || '';",
        "let API = sessionStorage.getItem('reanime_api') "
        "|| (window.KAGE_CONFIG && window.KAGE_CONFIG.BASE_API_URL) || '';",
    )

    # 3 ── Route HLS through /proxy/hls to fix CORS.
    html = html.replace(
        "initPlayer(streamData.url);",
        "initPlayer('/proxy/hls?url=' + encodeURIComponent(streamData.url));",
    )

    return Response(html, mimetype="text/html")


@app.route("/config.js")
def config_js():
    """Serve window.KAGE_CONFIG populated live from _KEY.txt."""
    cfg = read_key_file()
    base_api_url = cfg.get("BASE_API_URL", "")
    js = (
        "// Auto-generated by app.py from _KEY.txt\n"
        "// Edit BASE_API_URL in _KEY.txt and restart app.py to change the API endpoint.\n"
        f'window.KAGE_CONFIG = {{ "BASE_API_URL": "{base_api_url}" }};\n'
    )
    return Response(js, mimetype="application/javascript")


@app.route("/proxy/hls")
def hls_proxy():
    """
    HLS proxy — fetches any M3U8 or segment URL server-side using curl_cffi.

    Using curl_cffi with Chrome impersonation ensures the outbound TLS fingerprint
    matches a real browser, bypassing Cloudflare bot detection that blocks standard
    Python HTTP clients (httpx, requests) regardless of User-Agent headers.

    • M3U8 playlists → content rewritten so all child URLs also go through proxy.
    • TS / fMP4 segments → streamed straight through with CORS headers added.
    """
    url = request.args.get("url", "").strip()
    if not url:
        return Response("Missing ?url= parameter", status=400)

    if not _host_allowed(url):
        host = urlparse(url).hostname or url
        return Response(f"Host '{host}' is not in the proxy allowlist", status=403)

    # Forward the real client IP — flixcloud JWTs are IP-locked.
    # For a local setup the client is 127.0.0.1/::1, which is fine because
    # reanime.py and app.py run on the same machine; the outbound IP used
    # by curl_cffi is what flixcloud actually sees.
    # NOTE: X-Forwarded-For / X-Real-IP are intentionally omitted — Cloudflare's
    # WAF flags requests that inject these headers, especially with local/proxy IPs.
    proxy_headers = {**_PROXY_HEADERS}

    cors = {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "*"}

    is_m3u8_url = url.split("?")[0].lower().endswith(".m3u8")

    # ── M3U8 playlist (small text, safe to buffer fully) ──────────────────────
    if is_m3u8_url:
        try:
            resp = _CLIENT.get(url, headers=proxy_headers)
        except Exception as exc:
            return Response(f"Upstream error: {exc}", status=502)

        content_type = resp.headers.get("content-type", "").lower()
        is_m3u8 = "mpegurl" in content_type or is_m3u8_url

        if is_m3u8 and resp.ok:
            rewritten = _rewrite_m3u8(resp.text, url)
            return Response(
                rewritten,
                status=resp.status_code,
                mimetype="application/vnd.apple.mpegurl",
                headers=cors,
            )

        # Non-success or unexpected content: pass through as-is (lets HLS.js
        # handle the error rather than silently swallowing it)
        return Response(
            resp.content,
            status=resp.status_code,
            content_type=content_type or "application/vnd.apple.mpegurl",
            headers=cors,
        )

    # ── Binary segment passthrough (TS / AAC / fMP4) ──────────────────────────
    # curl_cffi uses standard requests stream=True syntax
    try:
        resp = _CLIENT.get(url, headers=proxy_headers, stream=True)
    except Exception as exc:
        return Response(f"Upstream error: {exc}", status=502)

    content_type = resp.headers.get("content-type", "video/MP2T")

    def _stream_gen():
        try:
            for chunk in resp.iter_content(chunk_size=65_536):
                if chunk:
                    yield chunk
        finally:
            resp.close()

    return Response(
        _stream_gen(),
        status=resp.status_code,
        content_type=content_type,
        headers=cors,
        direct_passthrough=True,
    )


@app.route("/proxy/sub")
def sub_proxy():
    """
    Subtitle proxy — fetches SRT / VTT / ASS files server-side so the browser
    never hits cross-origin subtitle CDNs directly.
    """
    url = request.args.get("url", "").strip()
    if not url:
        return Response("Missing ?url= parameter", status=400)

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return Response("Only http/https URLs are proxied", status=400)

    try:
        resp = _CLIENT.get(url, headers=_PROXY_HEADERS)
    except Exception as exc:
        return Response(f"Upstream error: {exc}", status=502)

    ct = resp.headers.get("content-type", "text/plain")
    return Response(
        resp.content,
        status=resp.status_code,
        content_type=ct,
        headers={"Access-Control-Allow-Origin": "*"},
    )


# ─── CORS pre-flight ──────────────────────────────────────────────────────────

@app.after_request
def _add_cors(response: Response) -> Response:
    response.headers.setdefault("Access-Control-Allow-Origin", "*")
    return response


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    cfg   = read_key_file()
    api   = cfg.get("BASE_API_URL", "")

    print()
    print("  ╔══════════════════════════════════════════════╗")
    print("  ║           KAGE  Frontend  Server             ║")
    print("  ╠══════════════════════════════════════════════╣")
    print(f"  ║  UI      →  http://localhost:6767            ║")
    print(f"  ║  API     →  {api:<32} ║")
    print(f"  ║  Config  →  _KEY.txt                         ║")
    print("  ╚══════════════════════════════════════════════╝")
    print()

    app.run(host="0.0.0.0", port=6767, debug=False, threaded=True)
