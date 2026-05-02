import os
import tempfile
import uuid
import requests
import io
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, File, UploadFile, Form
from fastapi.responses import StreamingResponse

from schemas import UserSignup, UserLogin, DailyBriefing
from security import get_current_user, scrub_pii, get_embedding
from config import supabase, index, ai_client, ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID

router = APIRouter()

@router.post("/signup", tags=["Authentication"])
def signup(user: UserSignup):
    try:
        auth_response = supabase.auth.sign_up({"email": user.email, "password": user.password})
        if auth_response.user:
            supabase.table("profiles").insert({
                "id": auth_response.user.id,
                "full_name": user.full_name
            }).execute()
        return {"message": "Account created successfully."}
    except Exception:
        raise HTTPException(status_code=400, detail="Signup failed. The email may already be in use.")

@router.post("/login", tags=["Authentication"])
def login(user: UserLogin):
    try:
        auth_response = supabase.auth.sign_in_with_password({"email": user.email, "password": user.password})
        return {
            "message": "Login successful",
            "access_token": auth_response.session.access_token, 
            "token_type": "bearer"
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid email or password")

@router.post("/upload_briefing", tags=["Memory Vault"])
def upload_briefing(briefing: DailyBriefing, current_email: str = Depends(get_current_user)):
    safe_text = scrub_pii(briefing.text)
    vector_data = get_embedding(safe_text)
    memory_id = str(uuid.uuid4())
    
    current_time = datetime.now().strftime("%Y-%m-%d %I:%M %p")
    current_date = datetime.now().strftime("%Y-%m-%d") # Extract just the date
    
    index.upsert(
        vectors=[
            {
                "id": memory_id,
                "values": vector_data,
                "metadata": {
                    "owner": current_email.lower(),
                    "text": safe_text,
                    "timestamp": current_time,
                    "date": current_date, # Save today's date
                    "allowed_caller": briefing.allowed_caller.lower() # Save the dad's email
                }
            }
        ]
    )
    return {
        "message": f"Memory securely stored for {current_email}",
        "memory_id": memory_id,
        "timestamp": current_time,
        "date": current_date,
        "sanitized_text": safe_text
    }

@router.get("/check_status", tags=["Call Routing"])
def check_status(target_email: str, current_email: str = Depends(get_current_user)):
    search_vector = get_embedding("latest status update")
    
    # 1. Get today's date
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    # 2. Update the query to include the new filters
    search_results = index.query(
        vector=search_vector,
        top_k=1,  # Keep this at 1 for check_status
        include_metadata=True,
        filter={
            "owner": target_email.lower(),
            "allowed_caller": current_email.lower(), # Ensures only the authorized person (e.g., your dad) can see it
            "date": current_date # Ensures they only see today's status
        } 
    )
    
    if not search_results.matches:
        return {
            "has_briefing": False,
            "message": f"{target_email} has not uploaded any briefings for you today.",
            "last_updated": None
        }
        
    latest_memory = search_results.matches[0].metadata
    last_updated = latest_memory.get("timestamp", "Unknown time")
    
    return {
        "has_briefing": True,
        "message": f"{target_email}'s AI Clone is ready to take your call.",
        "last_updated": last_updated
    }

@router.get("/simulate_call", tags=["Call Routing (Text)"])
def simulate_call(target_email: str, message: str, current_email: str = Depends(get_current_user)):
    message_vector = get_embedding(message) 
    search_results = index.query(
        vector=message_vector,
        top_k=3,
        include_metadata=True,
        filter={
            "owner": target_email.lower(),
            "allowed_caller": current_email.lower(),
            "date": datetime.now().strftime("%Y-%m-%d")
        }
    )
    
    retrieved_memories = [match.metadata.get("text", "") for match in search_results.matches if "text" in match.metadata]
    context = "\n- ".join(retrieved_memories) if retrieved_memories else "No memories found."
    
    system_prompt = f"""
    You are the AI clone of {target_email}. You are answering a phone call from {current_email}.
    Respond directly to {current_email} on behalf of {target_email}. 
    
    CRITICAL SECURITY RULE: You may ONLY use the information provided in the 'Memories' section below. 
    If the answer is not in the memories, politely tell {current_email} that {target_email} hasn't briefed you on that.
    Keep your answer conversational and brief.
    
    Memories of {target_email}:
    - {context}
    """
    
    gpt_response = ai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message}
        ],
        temperature=0.3
    )
    
    ai_text_answer = gpt_response.choices[0].message.content

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": ELEVENLABS_API_KEY
    }
    data = {
        "text": ai_text_answer,
        "model_id": "eleven_turbo_v2", 
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}
    }
    
    audio_response = requests.post(url, json=data, headers=headers, timeout=30)
    if audio_response.status_code != 200:
        raise HTTPException(status_code=502, detail="Voice synthesis failed.")

    return StreamingResponse(io.BytesIO(audio_response.content), media_type="audio/mpeg")


@router.post("/voice_call", tags=["Call Routing (Voice)"])
async def voice_call(
    target_email: str = Form(...),
    audio_file: UploadFile = File(...),
    current_email: str = Depends(get_current_user)
):
    MAX_AUDIO_BYTES = 10 * 1024 * 1024  # 10 MB
    audio_bytes = await audio_file.read(MAX_AUDIO_BYTES + 1)
    if len(audio_bytes) > MAX_AUDIO_BYTES:
        raise HTTPException(status_code=413, detail="Audio file too large (max 10 MB).")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_audio:
        temp_audio.write(audio_bytes)
        temp_audio_path = temp_audio.name

    try:
        with open(temp_audio_path, "rb") as audio_file_read:
            transcription = ai_client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file_read
            )
        message = transcription.text
    finally:
        os.remove(temp_audio_path)

    message_vector = get_embedding(message) 
    
    # --- UPDATED FILTERING LOGIC HERE ---
    search_results = index.query(
        vector=message_vector,
        top_k=3,
        include_metadata=True,
        filter={
            "owner": target_email.lower(),
            "allowed_caller": current_email.lower(),
            "date": datetime.now().strftime("%Y-%m-%d")
        }
    )
    # ------------------------------------
    
    retrieved_memories = [match.metadata.get("text", "") for match in search_results.matches if "text" in match.metadata]
    context = "\n- ".join(retrieved_memories) if retrieved_memories else "No memories found."
    
    system_prompt = f"""
    You are the AI clone of {target_email}. You are answering a voice call from {current_email}.
    Respond directly to {current_email} on behalf of {target_email}. 
    
    CRITICAL SECURITY RULE: You may ONLY use the information provided in the 'Memories' section below. 
    If the answer is not in the memories, politely tell {current_email} that {target_email} hasn't briefed you on that.
    Keep your answer conversational, brief, and natural for spoken dialogue.
    
    Memories of {target_email}:
    - {context}
    """
    
    gpt_response = ai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message}
        ],
        temperature=0.3
    )
    
    ai_text_answer = gpt_response.choices[0].message.content

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": ELEVENLABS_API_KEY
    }
    data = {
        "text": ai_text_answer,
        "model_id": "eleven_turbo_v2", 
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}
    }
    
    audio_response = requests.post(url, json=data, headers=headers, timeout=30)
    if audio_response.status_code != 200:
        raise HTTPException(status_code=502, detail="Voice synthesis failed.")

    return StreamingResponse(io.BytesIO(audio_response.content), media_type="audio/mpeg")