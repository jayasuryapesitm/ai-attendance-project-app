import streamlit as st
from src.database.db import enroll_student_to_subject
from src.database.config import supabase
import time


from src.database.db import create_attendance

def show_attendance_result(df, logs, review_data=None):
    st.write('Please review attendance before confirming.')
    st.dataframe(df, hide_index=True, width='stretch')

    if review_data:
        corrected_present_ids = {
            int(log["student_id"])
            for log in logs
            if log.get("is_present")
        }
        st.subheader("Recognized Students")
        if review_data["recognized"]:
            for row in review_data["recognized"]:
                col1, col2 = st.columns([1, 3])
                with col1:
                    if row.get("Crop") is not None:
                        st.image(row["Crop"], width=120)
                with col2:
                    st.write(
                        f"Student ID #{row.get('Student ID')} · "
                        f"{row.get('Orientation')} · "
                        f"distance {row.get('Distance'):.4f}"
                        if isinstance(row.get("Distance"), float)
                        else f"Student ID #{row.get('Student ID')}"
                    )
        else:
            st.caption("No strong matches.")

        st.subheader("Borderline Matches – Requires Review")
        correction_options = ["Not present"]
        correction_options += [
            f"{student['Name']} (#{student['ID']})"
            for student in df.to_dict("records")
        ]
        for index, row in enumerate(review_data["borderline"]):
            col1, col2 = st.columns([1, 3])
            with col1:
                if row.get("Crop") is not None:
                    st.image(row["Crop"], width=120)
            with col2:
                choice = st.selectbox(
                    f"Correct face Photo {row['Photo']} / Face {row['Face']}",
                    correction_options,
                    key=f"borderline_correction_{index}",
                )
                if choice != "Not present":
                    corrected_id = int(choice.rsplit("#", 1)[1].rstrip(")"))
                    if corrected_id not in corrected_present_ids:
                        corrected_present_ids.add(corrected_id)
        if not review_data["borderline"]:
            st.caption("No borderline matches.")

        st.subheader("Unmatched Faces")
        for index, row in enumerate(review_data["unmatched"]):
            col1, col2 = st.columns([1, 3])
            with col1:
                if row.get("Crop") is not None:
                    st.image(row["Crop"], width=120)
            with col2:
                choice = st.selectbox(
                    f"Correct unmatched face Photo {row['Photo']} / Face {row['Face']}",
                    correction_options,
                    key=f"unmatched_correction_{index}",
                )
                if choice != "Not present":
                    corrected_id = int(choice.rsplit("#", 1)[1].rstrip(")"))
                    corrected_present_ids.add(corrected_id)
        if not review_data["unmatched"]:
            st.caption("No unmatched faces.")

        st.subheader("Enrolled Students Not Detected")
        if review_data["enrolled_not_detected"]:
            st.table(review_data["enrolled_not_detected"])
        else:
            st.caption("All enrolled students had a detected observation.")

        for log in logs:
            log["is_present"] = int(log["student_id"]) in corrected_present_ids

    col1, col2 = st.columns(2)

    with col1:
        if st.button('Discard', width='stretch'):
            st.session_state.voice_attendance_results = None
            st.session_state.attendance_images = []
            st.session_state.attendance_image_keys = set()
            st.rerun()

    with col2:
        if st.button('Confirm & Save', width='stretch', type='primary'):
            try:
                create_attendance(logs)
                st.toast("Attendance taken")
                st.session_state.attendance_images = []
                st.session_state.attendance_image_keys = set()
                st.session_state.voice_attendance_results = None
                st.rerun()
            except Exception as e:
                st.error('Sync failed!')



@st.dialog("Attendance Reports")
def attendance_result_dialog(df, logs, review_data=None):
    show_attendance_result(df, logs, review_data)

