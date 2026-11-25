
import base64
import binascii
import json
import os

import streamlit as st
from supabase import create_client, Client


def _read_secret(name):
    try:
        value = st.secrets.get(name)
    except Exception:
        value = None

    if value is None:
        value = os.getenv(name)

    return str(value).strip() if value is not None else ""


class SupabaseNotConfigured:
    def _fail(self):
        raise RuntimeError(
            "Supabase is not configured. Add SUPABASE_URL and SUPABASE_KEY "
            "to Streamlit Secrets or set both environment variables."
        )

    def table(self, *_args, **_kwargs):
        self._fail()

    def rpc(self, *_args, **_kwargs):
        self._fail()


def _validate_server_side_key(key):
    if key.startswith("sb_publishable_"):
        raise RuntimeError(
            "SUPABASE_KEY is a publishable key. Configure a Supabase "
            "server-side secret/service_role key."
        )

    token_parts = key.split(".")

    if len(token_parts) != 3:
        return

    payload = token_parts[1]
    payload += "=" * (-len(payload) % 4)

    try:
        claims = json.loads(
            base64.urlsafe_b64decode(payload).decode("utf-8")
        )
    except (ValueError, UnicodeDecodeError, binascii.Error):
        return

    role = claims.get("role")

    if role and role != "service_role":
        raise RuntimeError(
            "SUPABASE_KEY is not a service_role key. "
            "Configure a server-side Supabase key."
        )


supabase_url = _read_secret("SUPABASE_URL")
supabase_key = _read_secret("SUPABASE_KEY")

supabase_configured = bool(supabase_url and supabase_key)

if supabase_configured:
    _validate_server_side_key(supabase_key)
    supabase: Client | SupabaseNotConfigured = create_client(
        supabase_url,
        supabase_key
    )
else:
    st.session_state["supabase_configuration_error"] = (
        "Add SUPABASE_URL and SUPABASE_KEY to Streamlit Secrets "
        "or set both environment variables."
    )
    supabase = SupabaseNotConfigured()


def get_vision_api_key():
    return _read_secret("GEMINI_API_KEY")


def get_vision_model():
    return _read_secret("GEMINI_MODEL") or "gemini-3.5-flash-lite"


def get_smtp_config():
    return {
        "host": _read_secret("SMTP_HOST"),
        "port": int(_read_secret("SMTP_PORT") or "587"),
        "username": _read_secret("SMTP_USERNAME"),
        "password": _read_secret("SMTP_PASSWORD"),
        "from_email": _read_secret("SMTP_FROM_EMAIL"),
        "use_tls": (
            _read_secret("SMTP_USE_TLS") or "true"
        ).lower() == "true",
    }
