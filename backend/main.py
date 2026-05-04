import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from routes import router

ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5500,http://127.0.0.1:5500,http://localhost:5501,http://127.0.0.1:5501"
).split(",")

_docs_enabled = os.getenv("ENABLE_DOCS", "false").lower() == "true"

app = FastAPI(
    title="CloneCalls API",
    version="1.0",
    docs_url="/docs" if _docs_enabled else None,
    redoc_url="/redoc" if _docs_enabled else None,
    openapi_url="/openapi.json" if _docs_enabled else None,
)

# ── Security Headers Middleware ───────────────────────────────────────────────
# Fixes: X-Content-Type-Options Missing, Anti-clickjacking, CSP, Cache-Control
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    # Prevent MIME-type sniffing attacks
    response.headers["X-Content-Type-Options"] = "nosniff"
    # Block the API responses from being embedded in iframes (clickjacking)
    response.headers["X-Frame-Options"] = "DENY"
    # Minimal CSP for a JSON API — no resources should be loaded from our responses
    response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
    # Prevent caching of sensitive API responses
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    # Do not send referrer info to external services
    response.headers["Referrer-Policy"] = "no-referrer"
    # Restrict browser feature access
    response.headers["Permissions-Policy"] = "geolocation=(), camera=()"
    return response
# ─────────────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["POST", "GET"],
    allow_headers=["Authorization", "Content-Type"],
)

@app.get("/")
def health_check():
    return {"status": "ok"}

app.include_router(router)
