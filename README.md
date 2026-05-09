# CloneCall

An AI-powered asynchronous communication platform that lets you create a secure voice clone of yourself to answer calls when you're unavailable. Instead of voicemail, callers have a natural conversation with your AI twin — trained on a daily briefing you provide — and hear a response in your synthesized voice.

---

## How It Works

1. **Leave a Clone** — You record a daily briefing (text) with context, your schedule, and a list of callers you authorize. The briefing is PII-scrubbed and stored as vector embeddings.
2. **Make a Call** — An authorized caller checks if you have a briefing active, then records a voice question via their microphone.
3. **AI Response** — The system transcribes the audio (Whisper), retrieves relevant context from your briefing (RAG via Pinecone), generates a reply (GPT-4o-mini), and synthesizes speech in your voice (ElevenLabs).
4. **Hear the Response** — The caller hears your AI clone respond in real time.

Briefings are scoped to a single day and restrict responses strictly to briefed context, preventing hallucination.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Vanilla HTML/CSS/JS (SPA) |
| Backend | FastAPI + Uvicorn (Python) |
| Auth & Database | Supabase (PostgreSQL + JWT) |
| Vector Store | Pinecone |
| Transcription | OpenAI Whisper |
| Language Model | OpenAI GPT-4o-mini |
| Embeddings | OpenAI text-embedding-3-small |
| Voice Synthesis | ElevenLabs |
| Rate Limiting | SlowAPI |

---

## Project Structure

```
CloneCall/
├── index.html                    # Frontend SPA
├── backend/
│   ├── main.py                   # FastAPI app & middleware
│   ├── routes.py                 # API endpoints
│   ├── config.py                 # Third-party service setup
│   ├── security.py               # Auth, PII scrubbing, embeddings
│   ├── schemas.py                # Pydantic request/response models
│   ├── limiter.py                # Rate limiting config
│   └── requirements.txt
├── Diagrams/                     # System architecture & flow diagrams
├── Documenta/                    # Project deliverables & security reports
└── CloneCall_Security_Tests.postman_collection.json
```

---

## API Endpoints

| Method | Route | Description |
|---|---|---|
| `POST` | `/signup` | Create a new account |
| `POST` | `/login` | Authenticate (rate-limited: 5 req/min) |
| `POST` | `/upload_briefing` | Store today's briefing with authorized callers |
| `GET` | `/check_status` | Check if a target user has an active briefing |
| `GET` | `/simulate_call` | Text-based call simulation |
| `POST` | `/voice_call` | Full voice call: transcribe → RAG → synthesize |
| `GET` | `/` | Health check |

All protected routes require a Supabase Bearer token.

---

## Setup

### Prerequisites

- Python 3.10+
- A [Supabase](https://supabase.com) project with a `profiles` table
- [Pinecone](https://www.pinecone.io) index named `clonecalls-memory`
- OpenAI API key
- ElevenLabs API key and a cloned voice ID

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create `backend/.env`:

```env
SUPABASE_URL=<your_supabase_url>
SUPABASE_KEY=<your_supabase_key>
OPENAI_API_KEY=<your_openai_key>
PINECONE_API_KEY=<your_pinecone_key>
PINECONE_INDEX_NAME=clonecalls-memory
ELEVENLABS_API_KEY=<your_elevenlabs_key>
ELEVENLABS_VOICE_ID=<your_voice_id>
ALLOWED_ORIGINS=http://localhost:5500
```

Start the server:

```bash
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

### Frontend

Serve `index.html` on port 5500 (e.g., VS Code Live Server). The frontend auto-connects to `http://localhost:8000`.

---

## Security

- **Auth**: Supabase JWT bearer tokens on all protected routes
- **Access control**: Callers are validated against an email allowlist per briefing
- **PII scrubbing**: Credit card numbers, SSNs, and phone numbers are stripped before storage
- **Input validation**: Pydantic schemas enforce email format, text length (5–1000 chars), and 10 MB audio limit
- **Rate limiting**: Login endpoint capped at 5 requests/minute
- **Security headers**: CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy
- **Auditing**: Bandit (static analysis) and pip-audit (dependency CVEs) reports in `Documenta/`

To run the Postman security test suite, import `CloneCall_Security_Tests.postman_collection.json` and set your base URL variable to `http://localhost:8000`.

---

## Architecture

System architecture, security controls, and call flow diagrams are in [Diagrams/](Diagrams/).

---

## Deliverables

Academic deliverables and a full risk-controls report (OWASP-based) are in [Documenta/](Documenta/).
