import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Re-evaluate the path to the api/.env file explicitly
# Since the script runs from various entry points, we make sure it finds /api/.env
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
load_dotenv(dotenv_path=env_path)

# =====================================================================
# SUPABASE CONFIGURATION
# Set your endpoints and API keys in the api/.env file.
# 1. Get these from your Supabase Dashboard -> Project Settings -> API
# =====================================================================

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

# Initialize the Supabase client
def get_supabase_client() -> Client:
    # If the URL and KEY are missing, gracefully return None
    # to avoid crashing if the user hasn't set them up yet
    if not SUPABASE_URL or not SUPABASE_KEY or "your_supabase" in SUPABASE_URL:
        print("WARNING: Supabase URL or Key is not configured in api/.env. Database logging will be disabled.")
        return None
        
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        return supabase
    except Exception as e:
        print(f"Failed to initialize Supabase client: {e}")
        return None
