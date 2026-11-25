import streamlit as st


from supabase import create_client, Client
from streamlit.errors import StreamlitSecretNotFoundError


SUPABASE_CONFIG_ERROR = None


class _DisabledSupabase:
    def table(self, _name):
        raise RuntimeError(SUPABASE_CONFIG_ERROR)

    def rpc(self, _name, _params=None):
        raise RuntimeError(SUPABASE_CONFIG_ERROR)


try:
    supabase_url = st.secrets["SUPABASE_URL"]
    supabase_key = st.secrets["SUPABASE_KEY"]
except (KeyError, StreamlitSecretNotFoundError):
    SUPABASE_CONFIG_ERROR = (
        "Supabase secrets are missing. Create .streamlit/secrets.toml with "
        "SUPABASE_URL and SUPABASE_KEY, then restart Streamlit."
    )
    supabase: Client = _DisabledSupabase()
else:
    if supabase_key.startswith("sb_publishable_"):
        SUPABASE_CONFIG_ERROR = (
            "SUPABASE_KEY is a publishable key. Configure a Supabase "
            "server-side secret/service_role key in Streamlit secrets."
        )
        supabase = _DisabledSupabase()
    else:
        supabase = create_client(supabase_url, supabase_key)