import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import router

ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5500,http://127.0.0.1:5500,http://localhost:5501,http://127.0.0.1:5501"
).split(",")

# Swagger UI and ReDoc are off unless explicitly enabled (e.g. ENABLE_DOCS=true in .env)
_docs_enabled = os.getenv("ENABLE_DOCS", "false").lower() == "true"

app = FastAPI(
    title="CloneCalls API",
    version="1.0",
    docs_url="/docs" if _docs_enabled else None,
    redoc_url="/redoc" if _docs_enabled else None,
)

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
