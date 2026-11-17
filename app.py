
import streamlit as st

from src.screens.home_screen import home_screen
from src.ui.base_layout import render_top_navigation, style_base_layout

def main():
    st.set_page_config(
        page_title='SmartAttend',
        page_icon="🎓",
        layout="wide",
    )
    st.session_state.setdefault("theme", "light")
    st.session_state.setdefault("login_type", None)
    st.session_state.setdefault("current_role", None)

    requested_page = st.query_params.get("page")
    if requested_page not in ("home", "student", "teacher", "records"):
        requested_page = (
            "student"
            if st.query_params.get("join-code")
            or st.query_params.get("session-code")
            else st.session_state.get("page", "home")
        )
    page = requested_page
    st.session_state["page"] = page
    if page in ("student", "teacher"):
        st.session_state["current_role"] = page
    st.session_state["login_type"] = None if page == "home" else page

    style_base_layout()
    render_top_navigation(page)

    match page:
        case 'teacher':
            from src.screens.teacher_screen import teacher_screen

            teacher_screen()

        case 'student':
            from src.screens.student_screen import student_screen

            student_screen()
        
        case 'home':
            home_screen()
        case 'records':
            from src.screens.records_screen import records_screen

            records_screen()

    join_code = st.query_params.get('join-code')
    if (
        join_code
        and page == 'student'
        and st.session_state.get('is_logged_in')
        and st.session_state.get('user_role') == 'student'
    ):
        from src.components.dialog_auto_enroll import auto_enroll_dialog

        auto_enroll_dialog(join_code)


main()