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
            "to Streamlit Secrets (or set both environment variables), then "
            "restart the app."
        )

    def table(self, *_args, **_kwargs):
        self._fail()

    def rpc(self, *_args, **_kwargs):
        self._fail()


supabase_url = _read_secret("SUPABASE_URL")
supabase_key = _read_secret("SUPABASE_KEY")
supabase_configured = bool(supabase_url and supabase_key)

if supabase_configured and supabase_key.startswith("sb_publishable_"):
    supabase_configured = False
    st.session_state["supabase_configuration_error"] = (
        "SUPABASE_KEY is a publishable key. Use a server-side Supabase "
        "secret/service-role key instead."
    )
elif not supabase_configured:
    st.session_state["supabase_configuration_error"] = (
        "Add SUPABASE_URL and SUPABASE_KEY to Streamlit Secrets, or set both "
        "as environment variables."
    )


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
        "use_tls": (_read_secret("SMTP_USE_TLS") or "true").lower() == "true",
    }


supabase: Client | SupabaseNotConfigured
if supabase_configured:
    supabase = create_client(supabase_url, supabase_key)
else:
    supabase = SupabaseNotConfigured()