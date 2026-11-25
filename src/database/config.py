import base64
import binascii
import json
import os

import streamlit as st


from supabase import create_client, Client

supabase_key = st.secrets["SUPABASE_KEY"]


def _validate_server_side_key(key):
    if key.startswith("sb_publishable_"):
        raise RuntimeError(
            "SUPABASE_KEY is a publishable key. Configure a Supabase server-side "
            "secret/service_role key in Streamlit secrets; voice attendance RPCs "
            "are intentionally restricted to service_role."
        )

    token_parts = key.split(".")
    if len(token_parts) != 3:
        return
    payload = token_parts[1]
    payload += "=" * (-len(payload) % 4)
    try:
        claims = json.loads(base64.urlsafe_b64decode(payload).decode("utf-8"))
    except (ValueError, UnicodeDecodeError, binascii.Error):
        return
    role = claims.get("role")
    if role and role != "service_role":
        raise RuntimeError(
            "SUPABASE_KEY is an anon/publishable JWT, not a server-side key. "
            "Set a Supabase secret/service_role key in Streamlit secrets; "
            "student profile updates are blocked by row-level security otherwise."
        )


_validate_server_side_key(supabase_key)

supabase: Client = create_client(
    st.secrets["SUPABASE_URL"],
    supabase_key
)


def get_vision_api_key():
    return os.getenv("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY", "")


def get_vision_model():
    return (
        os.getenv("GEMINI_MODEL")
        or st.secrets.get("GEMINI_MODEL")
        or "gemini-3.5-flash-lite"
    )