import re
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from config import supabase, ai_client

security_scheme = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security_scheme)):
    try:
        user_response = supabase.auth.get_user(credentials.credentials)
        if not user_response.user:
            raise HTTPException(status_code=401, detail="Unauthorized")
        # SECURITY UPGRADE: Return the user's secure email address instead of the raw UUID
        return user_response.user.email 
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

def scrub_pii(text: str) -> str:
    text = re.sub(r'\b(?:\d[ -]*?){13,16}\b', '[REDACTED CREDIT CARD]', text)
    text = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[REDACTED PHONE NUMBER]', text)
    text = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[REDACTED SSN]', text)
    return text

def get_embedding(text: str):
    response = ai_client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding