from typing import Literal

import streamlit as st


def navigate_to(page: Literal["home", "student", "teacher", "records"]) -> None:
    st.session_state["page"] = page
    if page in ("student", "teacher"):
        st.session_state["current_role"] = page
    elif page == "home":
        st.session_state["current_role"] = None
    st.session_state["login_type"] = None if page == "home" else page
    st.query_params["page"] = page
    st.rerun()
