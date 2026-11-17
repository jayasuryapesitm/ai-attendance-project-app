import pandas as pd
import streamlit as st


def _record_year(timestamp):
    if pd.isna(timestamp):
        return "Unknown"
    return f"Calendar year {timestamp.year}"


def _record_row(record, student_name=None, student_id=None):
    subject = record.get("subjects") or {}
    student = record.get("students") or {}
    timestamp = pd.to_datetime(
        record.get("timestamp") or record.get("submitted_at"),
        errors="coerce",
        utc=True,
    )
    mode = record.get("verification_method") or record.get("verification_mode")
    score = record.get("verification_score")
    confidence = record.get("confidence_score")
    if confidence is None:
        confidence = record.get("verification_confidence")
    if confidence is None and mode == "voice":
        confidence = record.get("voice_match_score", score)

    is_present = record.get("is_present")
    if is_present is None:
        status = str(record.get("status", "Recorded")).capitalize()
        present = status.lower() in {"present", "approved", "verified"}
    else:
        present = bool(is_present)
        status = "Present" if present else "Absent"

    confidence_number = pd.to_numeric(confidence, errors="coerce")
    confidence_value = (
        float(confidence_number / 100 if confidence_number > 1 else confidence_number)
        if not pd.isna(confidence_number)
        else None
    )
    score_value = pd.to_numeric(score, errors="coerce")
    if confidence_value is not None:
        score_label = f"{confidence_value:.1%}"
    elif mode == "face" and score_value is not None and not pd.isna(score_value):
        score_label = f"{float(score_value):.3f} distance"
    elif mode == "voice" and score_value is not None and not pd.isna(score_value):
        score_label = f"{float(score_value):.1%}"
    else:
        score_label = "—"

    return {
        "Timestamp": timestamp,
        "Student Name": student.get("name", student_name or "—"),
        "Student ID": student.get("student_id", student_id or "—"),
        "Course": (
            f"{subject.get('subject_code', '')} — {subject.get('name', 'Course')}"
        ).strip(" —"),
        "Cohort": subject.get("section") or "Unassigned",
        "Academic Term": _record_year(timestamp),
        "Verification Mode": {
            "face": "Face match",
            "voice": "Voice match",
            "qr": "Dynamic QR",
            "dynamic_qr": "Dynamic QR",
            "photo": "Photo scan",
            "photo_scan": "Photo scan",
        }.get(str(mode).lower(), "Attendance record"),
        "Confidence Score": score_label,
        "Confidence Value": confidence_value,
        "Status": status,
        "_present": present,
    }


def _load_records():
    if "teacher_data" in st.session_state:
        from src.database.db import get_attendance_for_teacher, get_teacher_subjects

        teacher_id = st.session_state.teacher_data["teacher_id"]
        rows = get_attendance_for_teacher(teacher_id)
        subjects = get_teacher_subjects(teacher_id)
        pending_count = None
        if subjects:
            from src.database.db import (
                get_pending_class_checkins,
                get_pending_voice_attendance_for_subjects,
            )

            pending_count = len(get_pending_class_checkins(teacher_id))
            pending_count += len(
                get_pending_voice_attendance_for_subjects(
                    [subject["subject_id"] for subject in subjects]
                )
            )
        return rows, None, None, pending_count

    if "student_data" in st.session_state:
        from src.database.db import get_student_attendance

        student = st.session_state.student_data
        rows = get_student_attendance(student["student_id"])
        return rows, student.get("name"), student.get("student_id"), None

    return None, None, None, None


def records_screen():
    st.title("Attendance Records")
    st.caption(
        "Review recorded attendance and verification evidence for your courses. "
        "Biometric scores are shown only when the check-in flow provides them."
    )

    records, student_name, student_id, pending_count = _load_records()
    if records is None:
        st.info("Sign in to a student or teacher portal to view attendance records.")
        student_col, teacher_col = st.columns(2)
        with student_col:
            if st.button("Open Student Portal", type="primary", width="stretch"):
                from src.ui.navigation import navigate_to

                navigate_to("student")
        with teacher_col:
            if st.button("Open Teacher Portal", width="stretch"):
                from src.ui.navigation import navigate_to

                navigate_to("teacher")
        return

    audit = pd.DataFrame(
        [
            _record_row(record, student_name=student_name, student_id=student_id)
            for record in records
        ]
    )
    if audit.empty:
        audit = pd.DataFrame(
            columns=[
                "Timestamp",
                "Student Name",
                "Student ID",
                "Course",
                "Cohort",
                "Academic Term",
                "Verification Mode",
                "Confidence Score",
                "Confidence Value",
                "Status",
                "_present",
            ]
        )
    audit["Timestamp"] = pd.to_datetime(audit["Timestamp"], errors="coerce", utc=True)

    cohort_col, course_col, term_col, sensor_col, state_col = st.columns(5)
    with cohort_col:
        selected_cohort = st.selectbox(
            "Cohort",
            ["All"] + sorted(audit["Cohort"].dropna().unique().tolist()),
            key="records_cohort_filter",
        )
    with course_col:
        selected_course = st.selectbox(
            "Course Module",
            ["All"] + sorted(audit["Course"].dropna().unique().tolist()),
            key="records_course_filter",
        )
    with term_col:
        selected_term = st.selectbox(
            "Academic Term",
            ["All"] + sorted(audit["Academic Term"].dropna().unique().tolist()),
            key="records_term_filter",
        )
    with sensor_col:
        selected_sensor = st.selectbox(
            "Verification Sensor",
            ["All"] + sorted(audit["Verification Mode"].dropna().unique().tolist()),
            key="records_sensor_filter",
        )
    with state_col:
        selected_state = st.selectbox(
            "State",
            ["All"] + sorted(audit["Status"].dropna().unique().tolist()),
            key="records_state_filter",
        )
    st.caption(
        "A separate academic-term value is not stored; this filter uses the "
        "calendar year from each timestamp."
    )

    filtered = audit.copy()
    for column, selected in (
        ("Cohort", selected_cohort),
        ("Course", selected_course),
        ("Academic Term", selected_term),
        ("Verification Mode", selected_sensor),
        ("Status", selected_state),
    ):
        if selected != "All":
            filtered = filtered[filtered[column] == selected]

    total_records = len(filtered)
    verified = int(filtered["_present"].sum()) if total_records else 0
    attendance_rate = (100 * verified / total_records) if total_records else 0.0
    confidence_values = filtered["Confidence Value"].dropna()
    average_confidence = (
        f"{confidence_values.mean():.1%}" if not confidence_values.empty else "—"
    )
    metric_columns = st.columns(4)
    metric_columns[0].metric("Overall attendance", f"{attendance_rate:.1f}%")
    metric_columns[1].metric("Total verified", f"{verified:,}")
    metric_columns[2].metric("Biometric confidence", average_confidence)
    metric_columns[3].metric(
        "Pending audits",
        f"{pending_count:,}" if pending_count is not None else "—",
    )
    if confidence_values.empty:
        st.caption("No confidence values are available for the selected records.")

    st.subheader("Weekly attendance trends")
    trend_rows = filtered.dropna(subset=["Timestamp"]).copy()
    if trend_rows.empty:
        st.info("Attendance trends will appear when dated records are available.")
    else:
        trend_rows["Week"] = (
            trend_rows["Timestamp"]
            .dt.tz_convert(None)
            .dt.to_period("W")
        )
        weekly = (
            trend_rows.groupby("Week", observed=True)
            .agg(Verified=("_present", "sum"), Recorded=("_present", "count"))
            .tail(8)
        )
        weekly["Attendance"] = 100 * weekly["Verified"] / weekly["Recorded"]
        weekly.index = [f"Week {index}" for index in range(1, len(weekly) + 1)]
        st.line_chart(weekly[["Attendance"]], y="Attendance", height=260)

    st.subheader("Audit trail")
    display = filtered[
        [
            "Timestamp",
            "Student Name",
            "Student ID",
            "Course",
            "Verification Mode",
            "Confidence Score",
            "Status",
        ]
    ].copy()
    display["Timestamp"] = (
        display["Timestamp"].dt.tz_convert(None).dt.strftime("%Y-%m-%d %H:%M")
    )
    st.download_button(
        "Export Attendance CSV",
        data=display.to_csv(index=False).encode("utf-8-sig"),
        file_name="attendance_report.csv",
        mime="text/csv",
    )
    st.dataframe(display, width="stretch", hide_index=True)
