import os
from dotenv import load_dotenv
from supabase import create_client, Client
from openai import OpenAI
from pinecone import Pinecone

# Force environment variables to load
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")

if not all([SUPABASE_URL, SUPABASE_KEY, OPENAI_API_KEY, PINECONE_API_KEY, ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID]):
    raise RuntimeError("CRITICAL: Missing API keys in .env file")

# Initialize global clients
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
ai_client = OpenAI(api_key=OPENAI_API_KEY)
pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(PINECONE_INDEX_NAME)