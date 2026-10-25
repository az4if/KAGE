// ─── KAGE Config ──────────────────────────────────────────────────────────────
// This file is served dynamically by app.py — it reads BASE_API_URL from _KEY.txt.
// To change the API endpoint:
//   1. Edit  BASE_API_URL=  in  _KEY.txt
//   2. Restart  app.py  (or app.bat)
//
// You can also override at runtime in the browser console:
//   window.KAGE_CONFIG.BASE_API_URL = "http://my-server:8000"
// ─────────────────────────────────────────────────────────────────────────────

window.KAGE_CONFIG = {
  BASE_API_URL: "http://localhost:8000"
};
