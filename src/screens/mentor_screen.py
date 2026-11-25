import pandas as pd
import streamlit as st

from src.database.mentor_db import (
    accept_mentor_assignment_request,
    create_mentor,
    get_assigned_mentees,
    get_mentee_profile,
    get_notification_history,
    get_pending_assignment_requests,
    mentor_login,
    calculate_attendance,
    reject_mentor_assignment_request,
    send_pending_mentor_notifications,
)


def _format_acceptance_error(error):
    detail = str(error)
    if "mentor_mentees_assignment_request_idx" in detail:
        return (
            "The Supabase database is using an outdated mentor acceptance function. "
            "Run the latest sql/mentor_mentee.sql in the Supabase project configured "
            "for this app, then refresh and try again. This request is still pending."
        )
    return f"Could not accept this request: {detail}"


def mentor_screen():
    if st.session_state.get("mentor_data"):
        mentor_dashboard()
    else:
        if st.session_state.get("teacher_data"):
            st.info(
                "You are signed in as a teacher. Assign students from Teacher Portal. "
                "To review and accept mentees, sign in with a registered mentor account."
            )
        mentor_login_view()


def mentor_login_view():
    st.markdown('<div class="sa-hero">', unsafe_allow_html=True)
    st.header("Mentor Portal")
    st.caption("Sign in to view your mentees, attendance insights, and alerts.")
    left, center, right = st.columns([1, 2, 1])
    with center:
        st.session_state.setdefault("mentor_auth_mode", "login")
        login_column, create_column = st.columns(2)
        if login_column.button(
            "Login",
            type="primary" if st.session_state.mentor_auth_mode == "login" else "secondary",
            width="stretch",
            key="mentor_login_mode",
        ):
            st.session_state.mentor_auth_mode = "login"
            st.rerun()
        if create_column.button(
            "Create account",
            type="primary" if st.session_state.mentor_auth_mode == "create" else "secondary",
            width="stretch",
            key="mentor_create_mode",
        ):
            st.session_state.mentor_auth_mode = "create"
            st.rerun()

        if st.session_state.mentor_auth_mode == "login":
            with st.form("mentor_login_form"):
                email = st.text_input("Mentor email", autocomplete="email")
                password = st.text_input("Password", type="password", autocomplete="current-password")
                submitted = st.form_submit_button("Login to Mentor Portal", type="primary", width="stretch")
            if submitted:
                try:
                    mentor = mentor_login(email, password)
                    if not mentor:
                        st.error("Email or password is incorrect, or this account is inactive.")
                    else:
                        st.session_state.mentor_data = mentor
                        st.session_state.is_logged_in = True
                        st.session_state.user_role = "mentor"
                        st.rerun()
                except Exception as error:
                    _show_mentor_setup_error(error)
        else:
            st.markdown("#### Create your mentor account")
            st.caption("Create a simple account to view students assigned to you.")
            with st.form("mentor_create_account_form"):
                full_name = st.text_input("Full name")
                email = st.text_input("Work email", autocomplete="email")
                password = st.text_input("Create password", type="password", autocomplete="new-password")
                confirm_password = st.text_input("Confirm password", type="password", autocomplete="new-password")
                submitted = st.form_submit_button("Create mentor account", type="primary", width="stretch")
            if submitted:
                if not full_name.strip() or not email.strip():
                    st.error("Enter your name and email address.")
                elif len(password) < 8:
                    st.error("Use a password with at least 8 characters.")
                elif password != confirm_password:
                    st.error("The passwords do not match.")
                else:
                    try:
                        created = create_mentor(
                            full_name,
                            email,
                            password=password,
                        )
                        if not created:
                            st.error("Account creation returned no mentor record. Please try logging in.")
                        else:
                            mentor = mentor_login(email, password)
                            if not mentor:
                                st.success("Account created. You can now log in.")
                                st.session_state.mentor_auth_mode = "login"
                                st.rerun()
                            st.session_state.mentor_data = mentor
                            st.session_state.is_logged_in = True
                            st.session_state.user_role = "mentor"
                            st.success("Your mentor account is ready.")
                            st.rerun()
                    except Exception as error:
                        _show_mentor_setup_error(error)
    st.markdown("</div>", unsafe_allow_html=True)


def _show_mentor_setup_error(error):
    message = str(error)
    if (
        "PGRST205" in message
        or "public.mentors" in message
        or "mentor_assignment_requests" in message
        or ("mentor_mentees" in message and "status" in message)
    ):
        st.error("Mentor database setup is not active yet.")
        st.info(
            "Run the latest `sql/mentor_mentee.sql` in the Supabase SQL Editor, "
            "wait a few seconds, then refresh ClassLens.ai."
        )
    elif "23505" in message or "duplicate key" in message.lower():
        st.error("An account already uses this email address. Try logging in instead.")
    else:
        st.error(f"Mentor account request failed: {message}")


def _show_flash_notices(key):
    for level, message in st.session_state.pop(key, []):
        getattr(st, level)(message)


def mentor_dashboard():
    mentor = st.session_state.mentor_data
    c1, c2 = st.columns([4, 1])
    c1.subheader(f"Welcome, {mentor['full_name']}")
    _show_flash_notices("mentor_acceptance_notices")
    if c2.button("Logout", key="mentor_logout"):
        del st.session_state.mentor_data
        st.session_state.is_logged_in = False
        st.session_state.user_role = None
        st.rerun()

    try:
        requests = get_pending_assignment_requests(mentor["id"])
        mentees = get_assigned_mentees(mentor["id"])
    except Exception as error:
        _show_mentor_setup_error(error)
        return

    low_attendance = [
        student for student in mentees
        if student.get("_percentage", 0) < 75
    ]
    dashboard_tab, requests_tab, mentees_tab, attendance_tab, alerts_tab, history_tab, profile_tab = st.tabs(
        [
            "Dashboard",
            "Student Assignment Requests",
            "My Mentees",
            "Mentee Attendance",
            "Low Attendance Alerts",
            "Notification History",
            "Mentor Profile",
        ]
    )

    with dashboard_tab:
        metric_columns = st.columns(3)
        metric_columns[0].metric("Pending requests", len(requests))
        metric_columns[1].metric("Accepted mentees", len(mentees))
        metric_columns[2].metric("Below 75%", len(low_attendance))
        st.caption("Assignment requests must be accepted before students appear in My Mentees.")

    with requests_tab:
        st.subheader("Student Assignment Requests")
        st.caption("Review requests sent by teachers. Accept or reject each request.")
        if not requests:
            st.info("You have no pending assignment requests.")
        for request in requests:
            student = request.get("student") or {}
            teacher = request.get("teacher") or {}
            request_id = request["id"]
            with st.container(border=True):
                st.markdown(f"#### {student.get('name') or 'Student'}")
                detail_columns = st.columns(4)
                detail_columns[0].caption(
                    f"Student ID: ST-{student.get('student_id', '—')}"
                )
                detail_columns[1].caption(
                    f"Email: {student.get('email') or 'Not provided'}"
                )
                detail_columns[2].caption(
                    f"Academic year: {student.get('academic_year') or 'Not set'}"
                )
                detail_columns[3].caption(
                    f"Branch: {student.get('branch') or 'Not set'}"
                )
                st.caption(
                    f"Department: {student.get('department') or 'Not set'} · "
                    f"Assigned by: {teacher.get('name') or 'Teacher'} · "
                    f"Requested: {request.get('requested_at') or '—'} · "
                    f"Status: {request.get('status', 'pending').title()}"
                )
                accept_column, reject_column, _ = st.columns([1, 1, 4])
                if accept_column.button(
                    "Accept request",
                    type="primary",
                    key=f"accept_assignment_request_{request_id}",
                ):
                    try:
                        accept_mentor_assignment_request(mentor["id"], request_id)
                    except Exception as error:
                        st.error(_format_acceptance_error(error))
                    else:
                        notices = [
                            (
                                "success",
                                "Student successfully accepted and added to your mentee list.",
                            )
                        ]
                        try:
                            _, notification_error = send_pending_mentor_notifications()
                        except Exception as error:
                            notification_error = str(error)
                        if notification_error:
                            notices.append(
                                (
                                    "info",
                                    "The low-attendance alert is queued but could not be "
                                    f"sent yet: {notification_error}",
                                )
                            )
                        st.session_state["mentor_acceptance_notices"] = notices
                        st.rerun()
                if reject_column.button(
                    "Reject request",
                    key=f"reject_assignment_request_{request_id}",
                ):
                    try:
                        reject_mentor_assignment_request(mentor["id"], request_id)
                        st.session_state["mentor_acceptance_notices"] = [
                            ("success", "Assignment request rejected successfully.")
                        ]
                        st.rerun()
                    except Exception as error:
                        st.error(f"Could not reject this request: {error}")

    with mentees_tab:
        st.subheader("My Mentees")
        if not mentees:
            st.info("Accepted students will appear here.")
        else:
            st.dataframe(
                pd.DataFrame([
                    {
                        "Student": student.get("name", "Student"),
                        "Student ID": f"ST-{student['student_id']}",
                        "Email": student.get("email") or "Not provided",
                        "Academic Year": student.get("academic_year") or "Not set",
                        "Branch": student.get("branch") or "Not set",
                        "Attendance": f"{student.get('_percentage', 0):.1f}%",
                        "Accepted At": student.get("_accepted_at") or "—",
                    }
                    for student in mentees
                ]),
                hide_index=True,
                width="stretch",
            )

    with attendance_tab:
        st.subheader("Mentee Attendance")
        if not mentees:
            st.info("Accept an assignment request to view a student's attendance.")
        else:
            selected = st.selectbox(
                "Select a mentee",
                mentees,
                format_func=lambda student: (
                    f"{student.get('name', 'Student')} · "
                    f"ST-{student['student_id']}"
                ),
                key="mentor_selected_mentee",
            )
            student, logs = get_mentee_profile(
                selected["student_id"],
                mentor["id"],
            )
            if not student:
                st.warning("The selected student profile could not be found.")
            else:
                _, _, percentage = calculate_attendance(logs)
                st.subheader(student.get("name", "Student"))
                st.caption(f"Student ID: ST-{student['student_id']}")
                st.metric("Attendance", f"{percentage:.1f}%")
                if percentage < 75:
                    st.error(
                        f"Low attendance alert: {percentage:.1f}% is below the required 75%."
                    )
                elif logs:
                    st.success("Attendance requirement met.")
                else:
                    st.info("No attendance has been recorded for this student yet.")
                if logs:
                    history = sorted(
                        logs,
                        key=lambda row: row.get("timestamp") or "",
                        reverse=True,
                    )
                    st.dataframe(
                        pd.DataFrame([
                            {
                                "Date": row.get("timestamp") or "—",
                                "Status": "Present" if row.get("is_present") else "Absent",
                            }
                            for row in history
                        ]),
                        hide_index=True,
                        width="stretch",
                    )

    with alerts_tab:
        st.subheader("Low Attendance Alerts")
        if low_attendance:
            st.dataframe(
                pd.DataFrame([
                    {
                        "Student": student.get("name", "Student"),
                        "Student ID": f"ST-{student['student_id']}",
                        "Attendance": f"{student['_percentage']:.1f}%",
                    }
                    for student in low_attendance
                ]),
                hide_index=True,
                width="stretch",
            )
        else:
            st.success("No accepted mentees are below 75% attendance.")

    with history_tab:
        st.subheader("Notification History")
        try:
            notifications = get_notification_history(mentor["id"])
            if notifications:
                st.dataframe(
                    pd.DataFrame([
                        {
                            "Date": row.get("created_at") or "—",
                            "Student": (row.get("students") or {}).get("name", "Student"),
                            "Attendance": f"{row.get('attendance_percentage', 0)}%",
                            "Status": row.get("notification_status", "").title(),
                            "Email": row.get("recipient_email") or "—",
                        }
                        for row in notifications
                    ]),
                    hide_index=True,
                    width="stretch",
                )
            else:
                st.info("No attendance notifications have been recorded.")
        except Exception as error:
            st.error(f"Could not load notification history: {error}")

    with profile_tab:
        st.subheader("Mentor Profile")
        profile_columns = st.columns(2)
        profile_columns[0].write(f"**Name:** {mentor.get('full_name', '—')}")
        profile_columns[0].write(f"**Email:** {mentor.get('email', '—')}")
        profile_columns[1].write(f"**Department:** {mentor.get('department') or 'Not set'}")
        profile_columns[1].write(f"**Branch:** {mentor.get('branch') or 'Not set'}")
