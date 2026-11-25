import importlib.util

import streamlit as st

from src.database.db import get_live_campus_session_count
from src.ui.navigation import navigate_to


def _diagnostic_card(title, status, detail):
    with st.container(border=True):
        st.caption(title)
        st.markdown(f'<span class="sa-badge">{status}</span>', unsafe_allow_html=True)
        st.caption(detail)


def home_screen():
    st.markdown(
        """
        <section class="sa-hero">
            <div class="sa-kicker">ACADEMIC BIOMETRIC ATTENDANCE</div>
            <h1>Attendance, made clear.</h1>
            <p>Secure classroom check-in for students and faculty.</p>
        </section>
        """,
        unsafe_allow_html=True,
    )

    st.subheader("System readiness")
    camera, microphone, location, biometric = st.columns(4)
    with camera:
        _diagnostic_card(
            "Browser camera",
            "Ready on request",
            "Camera permission is requested only when you start verification.",
        )
    with microphone:
        _diagnostic_card(
            "Microphone input",
            "Ready on request",
            "Recordings are collected only during an opted-in voice check.",
        )
    with location:
        with st.container(border=True):
            st.caption("Campus proximity")
            st.session_state.setdefault("demo_campus_geofence", True)
            demo_in_radius = st.toggle(
                "Demo location: in radius",
                key="demo_campus_geofence",
                help="Illustration only; no campus boundary is configured.",
            )
            st.markdown(
                '<span class="sa-badge">'
                f"{'In radius · demo' if demo_in_radius else 'Not checked'}"
                "</span>",
                unsafe_allow_html=True,
            )
            st.caption("Optional location sharing; no campus boundary is configured.")
    with biometric:
        biometric_ready = importlib.util.find_spec("dlib") is not None
        _diagnostic_card(
            "Biometric verification",
            "Available" if biometric_ready else "Unavailable",
            "Face matching is initialized when a verification flow is opened.",
        )

    st.subheader("Choose your portal")
    student_column, teacher_column = st.columns(2, gap="large")
    with student_column:
        with st.container(border=True):
            st.markdown("### Student portal")
            st.write(
                "Use Live Class Check-in with your teacher's session code, review "
                "attendance, and manage enrolled subjects."
            )
            if st.button(
                "Launch Student Portal",
                key="launch_student_portal",
                type="primary",
                width="stretch",
            ):
                navigate_to("student")
    with teacher_column:
        with st.container(border=True):
            st.markdown("### Teacher portal")
            st.write(
                "Open a Live Class Check-in session, review student submissions, "
                "and manage course rosters."
            )
            if st.button(
                "Launch Teacher Portal",
                key="launch_teacher_portal",
                type="primary",
                width="stretch",
            ):
                navigate_to("teacher")

    live_sessions_count = get_live_campus_session_count()
    teacher_data = st.session_state.get("teacher_data")
    teacher_note = ""
    if teacher_data and isinstance(teacher_data, dict) and "teacher_id" in teacher_data:
        teacher_live_count = get_live_campus_session_count(teacher_data["teacher_id"])
        teacher_note = f" ({teacher_live_count} in your classes)"

    with st.container(border=True):
        metric_column, description_column = st.columns([1, 4], vertical_alignment="center")
        with metric_column:
            st.metric("Live campus sessions", live_sessions_count)
        with description_column:
            st.markdown("**Campus operations snapshot**")
            st.caption(
                "Real-time count of active class sessions currently open for "
                f"attendance check-in across campus{teacher_note}."
            )
