"""
CloneCall — Dynamic Security Test Suite
Run with: python test_security.py

Requires the server to be running:
  uvicorn main:app --reload

Fill in REAL_EMAIL and REAL_PASSWORD below before running.
"""

import requests
import io
import json

BASE = "http://127.0.0.1:8000"

# ── Fill these in with a real account you created via the frontend ──
REAL_EMAIL    = "yashfafatima717@gmail.com"
REAL_PASSWORD = "Muhammadsas786"
# ───────────────────────────────────────────────────────────────────

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"

results = []

def check(name, passed, expected="", got=""):
    tag = PASS if passed else FAIL
    print(f"  [{tag}] {name}")
    if not passed:
        print(f"         expected: {expected}")
        print(f"         got:      {got}")
    results.append((name, passed))

def section(title):
    print(f"\n{'─'*55}")
    print(f"  {title}")
    print(f"{'─'*55}")


# ════════════════════════════════════════════════════
# 1. AUTHENTICATION
# ════════════════════════════════════════════════════
section("1. AUTHENTICATION")

# 1a. Valid login returns a token
r = requests.post(f"{BASE}/login", json={"email": REAL_EMAIL, "password": REAL_PASSWORD})
token = r.json().get("access_token") if r.ok else None
check("Valid login returns 200 + access_token", r.status_code == 200 and bool(token),
      "status 200 + token", f"status {r.status_code}")

# 1b. Wrong password returns 401
r = requests.post(f"{BASE}/login", json={"email": REAL_EMAIL, "password": "wrongpassword99"})
check("Wrong password returns 401", r.status_code == 401,
      "401", r.status_code)

# 1c. Login error message does NOT reveal whether email or password is wrong
r = requests.post(f"{BASE}/login", json={"email": REAL_EMAIL, "password": "wrongpassword99"})
detail = r.json().get("detail", "")
check("Login error is generic (no field discrimination)",
      "invalid email or password" in detail.lower(),
      "'Invalid email or password'", detail)

# 1d. No token → 403
r = requests.post(f"{BASE}/upload_briefing", json={"text": "hello world", "allowed_caller": "a@b.com"})
check("Missing token returns 403", r.status_code == 403,
      "403", r.status_code)

# 1e. Fake token → 401
r = requests.post(f"{BASE}/upload_briefing",
                  headers={"Authorization": "Bearer fake.token.here"},
                  json={"text": "hello world", "allowed_caller": "a@b.com"})
check("Forged token returns 401", r.status_code == 401,
      "401", r.status_code)


# ════════════════════════════════════════════════════
# 2. INPUT VALIDATION
# ════════════════════════════════════════════════════
section("2. INPUT VALIDATION")

# 2a. Password too short → 422
r = requests.post(f"{BASE}/signup", json={"email": "new@test.com", "password": "short", "full_name": "Test User"})
check("Password < 8 chars rejected (422)", r.status_code == 422,
      "422", r.status_code)

# 2b. Invalid email format → 422
r = requests.post(f"{BASE}/signup", json={"email": "notanemail", "password": "validpass123", "full_name": "Test"})
check("Invalid email format rejected (422)", r.status_code == 422,
      "422", r.status_code)

# 2c. Briefing text too short → 422 (needs auth token)
if token:
    r = requests.post(f"{BASE}/upload_briefing",
                      headers={"Authorization": f"Bearer {token}"},
                      json={"text": "Hi", "allowed_caller": REAL_EMAIL})
    check("Briefing text < 5 chars rejected (422)", r.status_code == 422,
          "422", r.status_code)

# 2d. Briefing text too long → 422
if token:
    r = requests.post(f"{BASE}/upload_briefing",
                      headers={"Authorization": f"Bearer {token}"},
                      json={"text": "x" * 1001, "allowed_caller": REAL_EMAIL})
    check("Briefing text > 1000 chars rejected (422)", r.status_code == 422,
          "422", r.status_code)

# 2e. allowed_caller must be valid email → 422
if token:
    r = requests.post(f"{BASE}/upload_briefing",
                      headers={"Authorization": f"Bearer {token}"},
                      json={"text": "Valid briefing text here", "allowed_caller": "notanemail"})
    check("Non-email allowed_caller rejected (422)", r.status_code == 422,
          "422", r.status_code)

# 2f. Audio file > 10 MB rejected → 413
if token:
    big_file = io.BytesIO(b"0" * (10 * 1024 * 1024 + 1))
    r = requests.post(f"{BASE}/voice_call",
                      headers={"Authorization": f"Bearer {token}"},
                      data={"target_email": REAL_EMAIL},
                      files={"audio_file": ("big.webm", big_file, "audio/webm")})
    check("Audio file > 10 MB rejected (413)", r.status_code == 413,
          "413", r.status_code)


# ════════════════════════════════════════════════════
# 3. PII SCRUBBING
# ════════════════════════════════════════════════════
section("3. PII SCRUBBING")

if token:
    pii_text = "My SSN is 123-45-6789 and my card is 4111111111111111 call me at 555-867-5309"
    r = requests.post(f"{BASE}/upload_briefing",
                      headers={"Authorization": f"Bearer {token}"},
                      json={"text": pii_text, "allowed_caller": REAL_EMAIL})
    if r.ok:
        sanitized = r.json().get("sanitized_text", "")
        check("SSN redacted before storage",
              "[REDACTED SSN]" in sanitized, "[REDACTED SSN]", sanitized[:80])
        check("Credit card redacted before storage",
              "[REDACTED CREDIT CARD]" in sanitized, "[REDACTED CREDIT CARD]", sanitized[:80])
        check("Phone number redacted before storage",
              "[REDACTED PHONE NUMBER]" in sanitized, "[REDACTED PHONE NUMBER]", sanitized[:80])
        check("Raw PII not present in stored text",
              "123-45-6789" not in sanitized and "4111111111111111" not in sanitized,
              "no raw PII", sanitized[:80])
    else:
        print(f"  [SKIP] Could not upload briefing: {r.status_code} {r.text[:100]}")


# ════════════════════════════════════════════════════
# 4. INFORMATION DISCLOSURE
# ════════════════════════════════════════════════════
section("4. INFORMATION DISCLOSURE")

# 4a. Swagger UI disabled
r = requests.get(f"{BASE}/docs")
check("Swagger UI (/docs) disabled → 404", r.status_code == 404,
      "404", r.status_code)

# 4b. ReDoc disabled
r = requests.get(f"{BASE}/redoc")
check("ReDoc (/redoc) disabled → 404", r.status_code == 404,
      "404", r.status_code)

# 4c. Health check returns minimal info
r = requests.get(f"{BASE}/")
body = r.json()
check("Health check returns only {'status': 'ok'}",
      list(body.keys()) == ["status"] and body["status"] == "ok",
      "{'status': 'ok'}", body)

# 4d. Signup error is generic
r = requests.post(f"{BASE}/signup",
                  json={"email": REAL_EMAIL, "password": "testpass123", "full_name": "Test"})
detail = r.json().get("detail", "")
check("Signup error does not confirm email exists",
      "signup failed" in detail.lower() or "email may already" in detail.lower(),
      "generic message", detail)


# ════════════════════════════════════════════════════
# 5. CORS
# ════════════════════════════════════════════════════
section("5. CORS")

# 5a. Allowed origin gets CORS header
r = requests.options(f"{BASE}/login",
                     headers={"Origin": "http://127.0.0.1:5501",
                               "Access-Control-Request-Method": "POST"})
check("Allowed origin receives Access-Control-Allow-Origin",
      "access-control-allow-origin" in r.headers,
      "header present", "header missing")

# 5b. Disallowed origin gets no CORS header
r = requests.options(f"{BASE}/login",
                     headers={"Origin": "http://evil.com",
                               "Access-Control-Request-Method": "POST"})
acao = r.headers.get("access-control-allow-origin", "")
check("Disallowed origin receives no Access-Control-Allow-Origin",
      acao != "http://evil.com" and acao != "*",
      "no header or non-matching", acao or "not present")


# ════════════════════════════════════════════════════
# RESULTS SUMMARY
# ════════════════════════════════════════════════════
print(f"\n{'═'*55}")
passed = sum(1 for _, ok in results if ok)
total  = len(results)
print(f"  RESULTS: {passed}/{total} tests passed")
if passed == total:
    print(f"  \033[92mAll security controls verified.\033[0m")
else:
    failed = [name for name, ok in results if not ok]
    print(f"  \033[91mFailed:\033[0m")
    for name in failed:
        print(f"    - {name}")
print(f"{'═'*55}\n")
