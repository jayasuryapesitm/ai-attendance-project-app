import pandas as pd
import streamlit as st

from src.database.mentor_db import (
    end_mentor_assignment,
    get_teacher_assignment_requests,
    list_mentors,
    list_students,
    request_students_for_mentor,
)


def _show_flash_notices():
    for level, message in st.session_state.pop("teacher_assignment_notices", []):
        getattr(st, level)(message)


def teacher_assignment_dashboard():
    st.subheader("Assign Students to Mentors")
    st.caption(
        "Send an assignment request. The selected mentor must accept it before "
        "the student becomes an active mentee."
    )
    _show_flash_notices()

    teacher_id = st.session_state.teacher_data["teacher_id"]
    search = st.text_input("Search students", placeholder="Name, student ID, or email")
    try:
        mentors = [
            mentor for mentor in list_mentors()
            if mentor.get("is_active")
        ]
        students = list_students(search=search)
    except Exception as error:
        st.error(f"Could not load mentors and students: {error}")
        return

    if not mentors:
        st.info("No active mentors are registered yet.")
        _render_assignment_history(teacher_id)
        return
    if not students:
        st.info("No registered students match this search.")
        _render_assignment_history(teacher_id)
        return

    mentor_by_id = {mentor["id"]: mentor for mentor in mentors}
    student_by_id = {student["student_id"]: student for student in students}
    selection_version = st.session_state.get("teacher_assignment_selection_version", 0)
    selected_student_ids = st.multiselect(
        "Students",
        list(student_by_id),
        format_func=lambda student_id: (
            f"{student_by_id[student_id].get('name', 'Student')} · "
            f"ST-{student_id}"
            + (
                f" — {student_by_id[student_id]['_assignment']['status'].title()} "
                f"with {(student_by_id[student_id]['_assignment'].get('mentors') or {}).get('full_name', 'a mentor')}"
                if student_by_id[student_id].get("_assignment")
                else ""
            )
        ),
        key=f"teacher_assignment_students_{selection_version}",
        help=(
            "Choose registered students. A student with a pending or accepted "
            "request cannot be assigned again."
        ),
    )
    selected_mentor_id = st.selectbox(
        "Mentor",
        list(mentor_by_id),
        format_func=lambda mentor_id: mentor_by_id[mentor_id]["full_name"],
        key="teacher_assignment_mentor",
    )
    if st.button(
        "Send to Mentor for Approval",
        type="primary",
        disabled=not selected_student_ids,
        key="assign_mentee_students",
    ):
        try:
            request_count = request_students_for_mentor(
                selected_student_ids,
                selected_mentor_id,
                teacher_id,
            )
            st.session_state["teacher_assignment_selection_version"] = (
                selection_version + 1
            )
            st.session_state["teacher_assignment_notices"] = [
                (
                    "success",
                    f"Sent {request_count} assignment request(s) to "
                    f"{mentor_by_id[selected_mentor_id]['full_name']}. "
                    "The students remain pending until the mentor responds.",
                )
            ]
            st.rerun()
        except Exception as error:
            message = str(error)
            if "PGRST202" in message or "create_mentor_assignment_requests" in message:
                st.error("Supabase could not resolve the assignment-request function.")
                st.info(
                    "Run the latest `sql/mentor_mentee.sql` in the same Supabase "
                    "project used by ClassLens.ai, then restart the app."
                )
                st.code(message)
            elif "pending or accepted" in message.lower():
                st.warning(message)
            else:
                st.error(f"Could not create assignment request: {message}")

    _render_assignment_history(teacher_id)


def _render_assignment_history(teacher_id):
    st.divider()
    st.subheader("Assignment Request History")
    try:
        requests = get_teacher_assignment_requests(teacher_id)
    except Exception as error:
        st.error(f"Could not load your assignment requests: {error}")
        return
    if not requests:
        st.info("You have not sent any assignment requests yet.")
        return

    st.dataframe(
        pd.DataFrame([
            {
                "Student": (request.get("student") or {}).get("name", "Student"),
                "Student ID": f"ST-{request.get('student_id', '—')}",
                "Mentor": (request.get("mentor") or {}).get("full_name", "Mentor"),
                "Status": request.get("status", "").title(),
                "Requested": request.get("requested_at") or "—",
                "Responded": request.get("responded_at") or "—",
                "Rejection reason": request.get("rejection_reason") or "—",
            }
            for request in requests
        ]),
        hide_index=True,
        width="stretch",
    )

    accepted_requests = [
        request for request in requests
        if request.get("status") == "accepted"
    ]
    if accepted_requests:
        with st.expander("Manage accepted assignments"):
            st.warning(
                "Ending a relationship removes the student from the mentor's active list "
                "and allows a new assignment request."
            )
            for request in accepted_requests:
                student = request.get("student") or {}
                mentor = request.get("mentor") or {}
                student_name = student.get("name", "Student")
                confirmed = st.checkbox(
                    f"Confirm ending {student_name}'s relationship with "
                    f"{mentor.get('full_name', 'the mentor')}",
                    key=f"confirm_end_assignment_{request['id']}",
                )
                if st.button(
                    "End accepted relationship",
                    disabled=not confirmed,
                    key=f"end_assignment_{request['id']}",
                ):
                    try:
                        end_mentor_assignment(
                            teacher_id,
                            request["student_id"],
                            request["mentor_id"],
                        )
                        st.session_state["teacher_assignment_notices"] = [
                            (
                                "success",
                                f"Ended {student_name}'s accepted mentor relationship. "
                                "A new assignment request can now be sent.",
                            )
                        ]
                        st.rerun()
                    except Exception as error:
                        st.error(f"Could not end the accepted relationship: {error}")
