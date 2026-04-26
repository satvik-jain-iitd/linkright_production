#!/usr/bin/env python3
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add repo root to path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(REPO_ROOT))

from worker.app.db import create_supabase

def map_role_to_bucket(role: str) -> str:
    role = role.lower()
    if any(k in role for k in ["engineer", "developer", "backend", "frontend", "fullstack", "architect"]):
        if "manager" in role: return "engineering_manager"
        return "software_engineer"
    if any(k in role for k in ["product manager", "pm", "apm", "po", "product owner"]):
        return "product_manager"
    if any(k in role for k in ["designer", "ux", "ui", "product design"]):
        return "ux_designer"
    if any(k in role for k in ["growth", "marketer", "marketing", "seo", "content"]):
        return "growth_marketer"
    if any(k in role for k in ["analyst", "business analyst", "ba", "strategy"]):
        return "business_analyst"
    if any(k in role for k in ["data scientist", "data science", "ml", "machine learning"]):
        return "data_scientist"
    if any(k in role for k in ["success", "account manager", "support", "csm"]):
        return "customer_success"
    if any(k in role for k in ["manager", "lead", "head", "director", "vp", "executive"]):
        return "engineering_manager"
    return "product_manager" # Default fallback

async def run():
    print("🚀 Starting User Journey Mapping...")
    sb = create_supabase()
    
    # 1. Fetch all users who don't have a journey_bucket_slug
    users = sb.table("users").select("id, journey_bucket_slug").execute()
    
    for u in users.data:
        # Fetch their latest application to detect role
        app = sb.table("applications").select("role").eq("user_id", u["id"]).order("created_at", desc=True).limit(1).execute()
        
        detected_role = "General"
        if app.data:
            detected_role = app.data[0]["role"]
        
        bucket = map_role_to_bucket(detected_role)
        
        print(f"User {u['id'][:8]}: Role '{detected_role}' -> Bucket '{bucket}'")
        
        sb.table("users").update({"journey_bucket_slug": bucket}).eq("id", u["id"]).execute()

    print("✅ Mapping Complete.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(run())
