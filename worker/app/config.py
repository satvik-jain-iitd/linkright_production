import os

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

# Optional: shared secret so only our Vercel API can trigger jobs
WORKER_SECRET = os.environ.get("WORKER_SECRET", "")

# Render assigns PORT automatically
PORT = int(os.environ.get("PORT", "8000"))
