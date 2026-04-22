import os
from supabase import create_client, Client


def get_supabase_client() -> Client:
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url:
        raise ValueError("SUPABASE_URL is missing in environment")

    if not supabase_service_role_key:
        raise ValueError("SUPABASE_SERVICE_ROLE_KEY is missing in environment")

    return create_client(supabase_url, supabase_service_role_key)