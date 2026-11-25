import streamlit as st


from src.components.header import header_dashboard
from src.components.subject_card import subject_card
from src.ui.navigation import navigate_to


def teacher_screen():
    if "teacher_data" in st.session_state:
        teacher_dashboard()
    elif 'teacher_login_type' not in st.session_state or st.session_state.teacher_login_type=="login":
        teacher_screen_login()
    elif st.session_state.teacher_login_type == "register":
        teacher_screen_register()





def teacher_dashboard():
    teacher_data = st.session_state.teacher_data
    c1, c2 = st.columns(2, vertical_alignment='center', gap='xxlarge')
    with c1:
        header_dashboard()
    with c2:
        st.subheader(f"""Welcome, {teacher_data['name']} """)
        if st.button("Logout", type='secondary', key='loginbackbtn', shortcut="control+backspace"):
            st.session_state['is_logged_in'] = False
            del st.session_state.teacher_data 
            st.rerun()


    st.space()

    if "current_teacher_tab" not in st.session_state:
        st.session_state.current_teacher_tab = 'take_attendance'
    tab1, tab2, tab3, tab4, tab5, tab6 = st.columns(6)


    with tab1:
        type1 = "primary" if st.session_state.current_teacher_tab == 'take_attendance' else "tertiary"
        if st.button('Take Attendance',type=type1, width='stretch', icon=':material/ar_on_you:'):
            st.session_state.current_teacher_tab = 'take_attendance'
            st.rerun()

    with tab2:
        type2 = "primary" if st.session_state.current_teacher_tab == 'manage_subjects' else "tertiary"
        if st.button('Manage Subjects', type=type2, width='stretch', icon=':material/book_ribbon:'):
            st.session_state.current_teacher_tab = 'manage_subjects'
            st.rerun()

    with tab3:
        type3 = "primary" if st.session_state.current_teacher_tab == 'attendance_records' else "tertiary"
        if st.button('Attendance Records',type=type3, width='stretch', icon=':material/cards_stack:'):
            st.session_state.current_teacher_tab = 'attendance_records'
            st.rerun()

    with tab4:
        type4 = "primary" if st.session_state.current_teacher_tab == 'voice_reviews' else "tertiary"
        if st.button('Voice Reviews', type=type4, width='stretch', icon=':material/mic:'):
            st.session_state.current_teacher_tab = 'voice_reviews'
            st.rerun()

    with tab5:
        type5 = "primary" if st.session_state.current_teacher_tab == 'live_sessions' else "tertiary"
        if st.button('Live Check-in', type=type5, width='stretch', icon=':material/qr_code_2:'):
            st.session_state.current_teacher_tab = 'live_sessions'
            st.rerun()

    with tab6:
        type6 = "primary" if st.session_state.current_teacher_tab == 'paper_evaluation' else "tertiary"
        if st.button('Paper Evaluation', type=type6, width='stretch', icon=':material/description:'):
            st.session_state.current_teacher_tab = 'paper_evaluation'
            st.rerun()

    assignment_columns = st.columns([1, 2, 1])
    with assignment_columns[1]:
        assignment_type = (
            "primary"
            if st.session_state.current_teacher_tab == "mentor_assignments"
            else "tertiary"
        )
        if st.button(
            "Assign Students to Mentors",
            type=assignment_type,
            width="stretch",
            icon=":material/group_add:",
        ):
            st.session_state.current_teacher_tab = "mentor_assignments"
            st.rerun()


    st.divider()

    if st.session_state.current_teacher_tab == "take_attendance":
        teacher_tab_take_attendance()
    if st.session_state.current_teacher_tab == "manage_subjects":
        teacher_tab_manage_subjects()
    if st.session_state.current_teacher_tab == "attendance_records":
        teacher_tab_attendance_records()
    if st.session_state.current_teacher_tab == "voice_reviews":
        teacher_tab_voice_reviews()
    if st.session_state.current_teacher_tab == "live_sessions":
        teacher_tab_live_sessions()
    if st.session_state.current_teacher_tab == "paper_evaluation":
        teacher_tab_paper_evaluation()
    if st.session_state.current_teacher_tab == "mentor_assignments":
        from src.screens.teacher_assignment_screen import teacher_assignment_dashboard

        teacher_assignment_dashboard()

    



def teacher_tab_take_attendance():
    from src.database.db import get_teacher_subjects

    teacher_id = st.session_state.teacher_data['teacher_id']
    st.header('Take AI Attendance')


    if 'attendance_images' not in st.session_state:
        st.session_state.attendance_images = []

    subjects = get_teacher_subjects(teacher_id)

    if not subjects:
        st.warning('You havent created any subjects yet! Please create one to begin!')
        return
    
    subject_options = {f"{s['name']} - {s['subject_code']}": s['subject_id'] for s in subjects}

    col1, col2 = st.columns([3,1], vertical_alignment='bottom')

    with col1:
        selected_subject_label = st.selectbox('Select Subject', options=list(subject_options.keys()))

    with col2:
        if st.button('Add Photos', type='primary', icon=':material/photo_prints:', width='stretch'):
            from src.components.dialog_add_photo import add_photos_dialog

            add_photos_dialog()

    selected_subject_id = subject_options[selected_subject_label]

    st.divider()

    if st.session_state.attendance_images:
        st.header('Added Photos')
        gallery_cols = st.columns(4)

        for idx, img in enumerate(st.session_state.attendance_images):
            with gallery_cols[idx % 4 ]:
                st.image(img, width='stretch', caption=f'Photo {idx+1}')
    has_photos = bool(st.session_state.attendance_images)
    if not has_photos:
        st.info('Add or capture at least one classroom photo to enable face analysis.')
    else:
        with st.expander("Preview classroom face locations"):
            photo_index = st.selectbox(
                "Photo to inspect",
                range(len(st.session_state.attendance_images)),
                format_func=lambda index: f"Photo {index + 1}",
                key="classroom_face_preview_index",
            )
            if st.button(
                "Detect and annotate faces",
                key="annotate_classroom_faces",
            ):
                from PIL import Image, ImageDraw

                import numpy as np

                from src.pipelines.face_pipeline import detect_face_boxes

                photo = st.session_state.attendance_images[photo_index].convert("RGB")
                image_array = np.asarray(photo)
                face_boxes = detect_face_boxes(image_array)
                annotated = Image.fromarray(image_array.copy())
                draw = ImageDraw.Draw(annotated)
                line_width = max(2, round(max(annotated.size) / 500))
                for box in face_boxes:
                    draw.rectangle(box, outline=(0, 102, 204), width=line_width)
                st.image(
                    annotated,
                    caption=f"{len(face_boxes)} face locations detected",
                    width="stretch",
                )
                st.caption(
                    "Face location is not an identity decision. Use roster analysis "
                    "below to compare faces with enrolled profiles."
                )

    c1, c2 = st.columns(2)

    with c1:
        if st.button('Clear all photos', width='stretch', type='tertiary', icon=':material/delete:', disabled=not has_photos):
            st.session_state.attendance_images = []
            st.session_state.attendance_image_keys = set()
            st.rerun()


    with c2:
        
        if st.button(
            'Run Face Analysis',
            width='stretch',
            type='secondary',
            icon=':material/analytics:',
            disabled=not has_photos,
            help=(
                'Add or capture at least one classroom photo first.'
                if not has_photos
                else None
            ),
        ):
            with st.spinner('Deep scanning classroom photos...'):
                from datetime import datetime

                import numpy as np
                import pandas as pd

                from src.components.dialog_attendance_results import attendance_result_dialog
                from src.database.config import supabase
                from src.pipelines.face_pipeline import predict_attendance

                enrolled_res = (
                    supabase.table('subject_students')
                    .select("*, students(*)")
                    .eq('subject_id', selected_subject_id)
                    .execute()
                )
                enrolled_students = enrolled_res.data

                if not enrolled_students:
                    st.warning('No students enrolled in this course')
                    return

                candidate_student_ids = [
                    node['students']['student_id']
                    for node in enrolled_students
                    if node.get('students')
                    and node['students'].get('face_embedding')
                ]
                all_detected_ids = {}
                total_faces_detected = 0
                unmatched_faces = 0

                for idx, img in enumerate(st.session_state.attendance_images):
                    img_np = np.array(img.convert('RGB'))
                    detected, faces_detected, unmatched = predict_attendance(
                        img_np,
                        candidate_student_ids=candidate_student_ids,
                        expected_face_count=len(candidate_student_ids),
                    )
                    total_faces_detected += faces_detected
                    unmatched_faces += unmatched

                    if detected:
                        for sid in detected.keys():
                            student_id = int(sid)

                            all_detected_ids.setdefault(student_id, []).append(f"Photo {idx+1}")

                results, attendance_to_log = [], []
                current_timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

                for node in enrolled_students:
                    student = node['students']
                    sources = all_detected_ids.get(int(student['student_id']), [])
                    is_present = len(sources) > 0

                    results.append({
                        "Name": student['name'],
                        "ID": student['student_id'],
                        "Source": ", ".join(sources) if is_present else "-",
                        "Status": "✅ Present" if is_present else "❌ Absent"
                    })

                    attendance_to_log.append({
                        'student_id': student['student_id'],
                        'subject_id': selected_subject_id,
                        'timestamp': current_timestamp,
                        'is_present': bool(is_present)
                    })

                matched_faces = total_faces_detected - unmatched_faces
                unrecognized_student_count = (
                    len(enrolled_students) - len(all_detected_ids)
                )
                if unmatched_faces or unrecognized_student_count:
                    st.warning(
                        f"Matched {matched_faces} of {total_faces_detected} detected "
                        f"face observations; {unmatched_faces} faces could not be "
                        f"matched, and {unrecognized_student_count} enrolled students "
                        "were not recognized in the photos. "
                        "Try a closer, well-lit photo with faces unobstructed, or add "
                        "another photo from a different part of the room. Students "
                        "who are present but not recognized can use voice "
                        "verification in Live Check-in."
                    )
                else:
                    st.info(
                        f"Matched {matched_faces} of {total_faces_detected} detected "
                        "face observations. Review the roster before saving."
                    )

                attendance_result_dialog(pd.DataFrame(results), attendance_to_log)

def teacher_tab_manage_subjects():
    from src.database.db import get_teacher_subjects

    teacher_id = st.session_state.teacher_data['teacher_id']
    col1, col2 = st.columns(2)
    with col1:
        st.header('Manage Subjects', width='stretch')

    with col2:
        if st.button('Create New Subject', width='stretch'):
            from src.components.dialog_create_subject import create_subject_dialog

            create_subject_dialog(teacher_id)


    # LIST all SUBJECTS
    subjects = get_teacher_subjects(teacher_id)
    if subjects:
        for sub in subjects:
            stats = [
                ("🫂", "Students", sub['total_students']),
                ("🕰️", "Classes", sub['total_classes']),
            ]
            def subject_actions():
                share_col, delete_col = st.columns([2, 1])
                with share_col:
                    if st.button(
                        f"Share Code: {sub['name']}",
                        key=f"share_{sub['subject_id']}",
                        icon=":material/share:",
                        width="stretch",
                    ):
                        from src.components.dialog_share_subject import share_subject_dialog

                        share_subject_dialog(sub['name'], sub['subject_code'])
                with delete_col:
                    if st.button(
                        "Delete subject",
                        key=f"delete_subject_{sub['subject_id']}",
                        icon=":material/delete:",
                        width="stretch",
                    ):
                        from src.components.dialog_delete_subject import (
                            delete_subject_dialog,
                        )

                        delete_subject_dialog(
                            sub['subject_id'],
                            teacher_id,
                            sub['name'],
                            sub['subject_code'],
                        )
                st.space()

            subject_card(
                name=sub['name'],
                code=sub['subject_code'],
                section=sub['section'],
                stats=stats,
                footer_callback=subject_actions
            )
    else:
        st.info("NO SUBJECTS FOUND. CREATE ONE ABOVE")


def teacher_tab_attendance_records():
    from src.screens.records_screen import records_screen

    records_screen()


def teacher_tab_voice_reviews():
    from src.database.db import (
        get_pending_voice_attendance_for_subjects,
        get_teacher_subjects,
        review_voice_attendance,
    )

    teacher_id = st.session_state.teacher_data['teacher_id']
    subjects = get_teacher_subjects(teacher_id)
    subject_ids = [subject['subject_id'] for subject in subjects]

    st.header('Pending Voice Attendance')
    st.caption(
        "Voice samples are processed for matching and are not retained. Review the "
        "recorded match score and request a new check-in when needed."
    )
    submissions = get_pending_voice_attendance_for_subjects(subject_ids)
    if not submissions:
        st.info('There are no voice attendance requests waiting for review.')
        return

    for submission in submissions:
        with st.container(border=True):
            st.subheader(submission['student_name'])
            st.write(
                f"{submission['subject_name']} ({submission['subject_code']})"
            )
            st.caption(
                f"Submitted: {submission['submitted_at']} · "
                f"Voice match: {submission['voice_match_score']:.1%}"
            )
            location_url = (
                "https://www.google.com/maps/search/?api=1&query="
                f"{submission['latitude']},{submission['longitude']}"
            )
            st.markdown(f"[View submitted GPS location]({location_url})")
            if submission.get('location_accuracy_m') is not None:
                st.caption(
                    f"Reported GPS accuracy: {submission['location_accuracy_m']} m"
                )

            approve_col, reject_col = st.columns(2)
            with approve_col:
                if st.button(
                    'Approve',
                    key=f"approve_voice_{submission['submission_id']}",
                    type='primary',
                    width='stretch',
                ):
                    try:
                        review_voice_attendance(
                            submission['submission_id'],
                            teacher_id,
                            approved=True,
                        )
                    except ValueError as error:
                        st.warning(str(error))
                    else:
                        st.success('Attendance approved.')
                        st.rerun()
            with reject_col:
                if st.button(
                    'Reject',
                    key=f"reject_voice_{submission['submission_id']}",
                    type='secondary',
                    width='stretch',
                ):
                    try:
                        review_voice_attendance(
                            submission['submission_id'],
                            teacher_id,
                            approved=False,
                        )
                    except ValueError as error:
                        st.warning(str(error))
                    else:
                        st.success('Attendance rejected.')
                        st.rerun()


def teacher_tab_paper_evaluation():
    import logging

    from src.database.db import (
        create_exam_paper,
        delete_exam_paper,
        get_enrolled_students_for_subject,
        get_exam_papers_for_teacher,
        get_paper_submissions_for_teacher,
        get_teacher_subjects,
        insert_paper_submission,
        record_paper_evaluation_error,
        remove_unreferenced_exam_files,
        save_teacher_verified_marks,
        update_exam_documents,
        update_exam_marking_scheme,
        update_paper_evaluation,
    )
    from src.components.exam_marking_config import (
        exam_review_fingerprint,
        render_marking_scheme_editor,
        render_marking_scheme_summary,
    )
    from src.pipelines.exam_marking import (
        calculate_exam_result,
        get_scoring_targets,
        target_scores_from_result,
        validate_marking_scheme,
    )
    from src.pipelines.paper_pipeline import (
        compress_uploaded_pages,
        create_blueprint_rubric,
        decode_storage_paths,
        download_stored_pages,
        encode_storage_paths,
        evaluate_exam_pages,
        extract_exam_rubric,
        exam_storage_prefix,
        upload_page_images,
    )

    logger = logging.getLogger(__name__)
    teacher_id = st.session_state.teacher_data["teacher_id"]
    st.header("Live Paper Check-In & AI Semantic Grading")
    st.caption(
        "Upload a blueprint answer key, map each answer sheet to an enrolled "
        "student, then review and publish the AI-assisted scores."
    )

    subjects = get_teacher_subjects(teacher_id)
    if not subjects:
        st.info("Create a subject before setting up a paper evaluation.")
        return
    subject_options = {
        f"{subject['name']} — {subject['subject_code']}": subject["subject_id"]
        for subject in subjects
    }
    subject_label = st.selectbox(
        "Subject",
        list(subject_options),
        key="paper_evaluation_subject",
    )
    subject_id = subject_options[subject_label]

    from src.database.config import get_vision_api_key

    if not get_vision_api_key():
        st.warning(
            "AI paper grading is not configured yet. Add your Gemini API key as "
            "`GEMINI_API_KEY` in `.streamlit/secrets.toml` or as an environment "
            "variable, then restart ClassLens.ai."
        )

    create_generation_key = f"paper_create_generation_{subject_id}"
    create_generation = st.session_state.setdefault(create_generation_key, 0)
    with st.expander("Create an exam and upload its blueprint", expanded=False):
        exam_title = st.text_input(
            "Exam title",
            key=f"paper_title_{subject_id}_{create_generation}",
        )
        total_marks = st.number_input(
            "Total examination marks",
            min_value=1.0,
            value=100.0,
            step=1.0,
            key=f"paper_total_marks_{subject_id}_{create_generation}",
        )
        blueprint_file = st.file_uploader(
            "Blueprint answer key (image or PDF)",
            type=["png", "jpg", "jpeg", "webp", "pdf"],
            key=f"paper_blueprint_{subject_id}_{create_generation}",
        )
        question_paper_file = st.file_uploader(
            "Question paper (image or PDF)",
            type=["png", "jpg", "jpeg", "webp", "pdf"],
            key=f"paper_question_{subject_id}_{create_generation}",
        )
        marking_scheme, marking_generation_key = render_marking_scheme_editor(
            total_marks,
            f"paper_create_{subject_id}",
        )
        pending_key = f"exam_scheme_pending_{subject_id}"
        try:
            current_fingerprint = exam_review_fingerprint(
                exam_title,
                total_marks,
                marking_scheme,
                blueprint_file,
                question_paper_file,
            )
        except Exception as error:
            current_fingerprint = None
            st.error(f"Could not read the selected exam documents: {error}")
        pending_review = st.session_state.get(pending_key)
        if (
            pending_review
            and pending_review.get("fingerprint") != current_fingerprint
        ):
            st.session_state.pop(pending_key, None)
            pending_review = None
            st.info("The exam configuration changed. Review it again to continue.")

        if st.button(
            "Review marks distribution and documents",
            key=f"review_exam_scheme_{subject_id}_{create_generation}",
            type="primary",
            width="stretch",
        ):
            try:
                if not exam_title.strip():
                    raise ValueError("Enter an exam title before reviewing.")
                if blueprint_file is None or question_paper_file is None:
                    raise ValueError(
                        "Upload both the blueprint and question paper."
                    )
                validate_marking_scheme(marking_scheme, total_marks)
                with st.spinner(
                    "Checking the configured scheme against the blueprint "
                    "and question paper..."
                ):
                    blueprint_pages = compress_uploaded_pages(blueprint_file)
                    question_paper_pages = compress_uploaded_pages(
                        question_paper_file
                    )
                    checked_scheme, report = extract_exam_rubric(
                        blueprint_pages,
                        question_paper_pages,
                        marking_scheme,
                    )
                st.session_state[pending_key] = {
                    "fingerprint": exam_review_fingerprint(
                        exam_title,
                        total_marks,
                        marking_scheme,
                        blueprint_file,
                        question_paper_file,
                    ),
                    "title": exam_title.strip(),
                    "total_marks": total_marks,
                    "marking_scheme": checked_scheme,
                    "report": report,
                    "blueprint_pages": blueprint_pages,
                    "question_paper_pages": question_paper_pages,
                }
                st.rerun()
            except Exception as error:
                logger.exception("Could not review the exam marking scheme")
                st.error(f"Could not review this exam: {error}")

        pending_review = st.session_state.get(pending_key)
        if pending_review and pending_review.get("fingerprint") == current_fingerprint:
            report = pending_review["report"]
            st.subheader("Review and confirm this examination")
            render_marking_scheme_summary(
                pending_review["marking_scheme"],
                pending_review["total_marks"],
            )
            st.markdown("**Document comparison**")
            for module in report["modules"]:
                st.caption(
                    f"{module['module']}: configured "
                    f"{module['configured_marks']:g}; blueprint "
                    f"{module['blueprint_marks'] if module['blueprint_marks'] is not None else 'unclear'}; "
                    f"question paper "
                    f"{module['question_paper_marks'] if module['question_paper_marks'] is not None else 'unclear'}"
                )
            for item in report["items"]:
                st.caption(
                    f"{item['question_no']}: configured "
                    f"{item['configured_marks']:g}; blueprint "
                    f"{item['blueprint_marks'] if item['blueprint_marks'] is not None else 'unclear'}; "
                    f"question paper "
                    f"{item['question_paper_marks'] if item['question_paper_marks'] is not None else 'unclear'}"
                )
            if report["missing_rubric"]:
                st.error(
                    "Expected answer concepts are missing for: "
                    + ", ".join(report["missing_rubric"])
                    + ". Enter the concepts in the configuration above, then "
                    "review again."
                )
            if report["mark_mismatches"] or report["module_mismatches"]:
                st.error(
                    "The document marks do not match the configured scheme. "
                    "Update the marks or documents and review again."
                )
            if report["unconfigured_questions"] or report["unconfigured_modules"]:
                unmatched = (
                    report["unconfigured_modules"]
                    + report["unconfigured_questions"]
                )
                st.error(
                    "The documents contain items not in the configured scheme: "
                    + ", ".join(unmatched)
                    + ". Add them or correct the uploaded documents."
                )
            unclear_marks = any(
                item["blueprint_marks"] is None
                or item["question_paper_marks"] is None
                for item in report["items"] + report["modules"]
            )
            marks_confirmed = True
            if unclear_marks:
                marks_confirmed = st.checkbox(
                    "I verified the configured marks where the documents do "
                    "not show a clear allocation.",
                    key=f"confirm_unclear_marks_{subject_id}_{current_fingerprint}",
                )
            ready_to_create = (
                not report["missing_rubric"]
                and not report["mark_mismatches"]
                and not report["module_mismatches"]
                and not report["unconfigured_questions"]
                and not report["unconfigured_modules"]
                and marks_confirmed
            )
            if st.button(
                "Confirm scheme and create exam",
                key=f"confirm_exam_scheme_{subject_id}_{current_fingerprint}",
                type="primary",
                disabled=not ready_to_create,
            ):
                exam = None
                uploaded_paths = []
                documents_saved = False
                approved_scheme = pending_review["marking_scheme"]
                targets = get_scoring_targets(approved_scheme)
                rubric = {
                    "questions": [
                        {
                            "question_no": target["question_no"],
                            "max_marks": target["max_marks"],
                            "checkpoints": target["checkpoints"],
                            "target_id": target["target_id"],
                        }
                        for target in targets
                    ]
                }
                try:
                    exam = create_exam_paper(
                        subject_id,
                        teacher_id,
                        pending_review["title"],
                        None,
                        rubric,
                        pending_review["total_marks"],
                        None,
                        marking_scheme=approved_scheme,
                    )
                    blueprint_paths = upload_page_images(
                        pending_review["blueprint_pages"],
                        exam_storage_prefix(exam["exam_id"], "blueprints"),
                    )
                    uploaded_paths.extend(blueprint_paths)
                    question_paper_paths = upload_page_images(
                        pending_review["question_paper_pages"],
                        exam_storage_prefix(exam["exam_id"], "question-papers"),
                    )
                    uploaded_paths.extend(question_paper_paths)
                    update_exam_documents(
                        exam["exam_id"],
                        teacher_id,
                        encode_storage_paths(blueprint_paths),
                        blueprint_rubric=rubric,
                        max_marks=pending_review["total_marks"],
                        question_paper_path=encode_storage_paths(
                            question_paper_paths
                        ),
                        marking_scheme=approved_scheme,
                    )
                    documents_saved = True
                except Exception as error:
                    logger.exception("Could not create a paper evaluation exam")
                    cleanup_errors = []
                    if exam is not None:
                        try:
                            delete_exam_paper(exam["exam_id"], teacher_id)
                        except Exception as cleanup_error:
                            logger.exception("Could not remove incomplete exam")
                            cleanup_errors.append(str(cleanup_error))
                    if uploaded_paths and not documents_saved:
                        try:
                            remove_unreferenced_exam_files(uploaded_paths)
                        except Exception as cleanup_error:
                            logger.exception("Could not clean up new exam files")
                            cleanup_errors.append(str(cleanup_error))
                    detail = f"Could not create this exam: {error}"
                    if cleanup_errors:
                        detail += (
                            " Cleanup also failed: " + "; ".join(cleanup_errors)
                        )
                    st.error(detail)
                else:
                    st.session_state.pop(pending_key, None)
                    st.session_state[create_generation_key] += 1
                    st.session_state[marking_generation_key] += 1
                    st.success("The confirmed exam and marking scheme were created.")
                    st.rerun()

    exams = get_exam_papers_for_teacher(teacher_id)
    exams = [exam for exam in exams if exam["subject_id"] == subject_id]
    if not exams:
        st.info("Create an exam for this subject to start receiving answer sheets.")
        return

    exam_labels = {
        exam["exam_id"]: (
            f"{exam['title']} · {(exam.get('subjects') or {}).get('name', 'Subject')} "
            f"· {exam['created_at'][:10]} · Exam {exam['exam_id']}"
        )
        for exam in exams
    }
    exams_by_id = {exam["exam_id"]: exam for exam in exams}
    exam_label = st.selectbox(
        "Exam",
        list(exams_by_id),
        format_func=lambda exam_id: exam_labels[exam_id],
        key=f"paper_exam_selector_{subject_id}",
    )
    exam = exams_by_id[exam_label]

    if st.button(
        "Delete exam",
        key=f"delete_exam_{exam['exam_id']}",
        type="secondary",
        icon=":material/delete:",
    ):
        st.session_state[f"confirm_delete_exam_{exam['exam_id']}"] = True
    if st.session_state.get(f"confirm_delete_exam_{exam['exam_id']}"):
        st.warning(
            f"Delete '{exam['title']}' permanently? This removes the exam, "
            "rubric, question paper, all submitted answer sheets, scores, "
            "and reviews. This cannot be undone."
        )
        confirm_col, cancel_col = st.columns(2)
        with confirm_col:
            if st.button(
                "Yes, permanently delete",
                key=f"confirm_delete_exam_yes_{exam['exam_id']}",
                type="primary",
            ):
                try:
                    with st.spinner("Deleting exam and all related records..."):
                        delete_exam_paper(exam["exam_id"], teacher_id)
                except Exception as error:
                    st.error(f"Could not fully delete this exam: {error}")
                else:
                    st.session_state.pop(
                        f"confirm_delete_exam_{exam['exam_id']}",
                        None,
                    )
                    st.success("The exam and its related records were deleted.")
                    st.rerun()
        with cancel_col:
            if st.button(
                "Cancel",
                key=f"confirm_delete_exam_cancel_{exam['exam_id']}",
            ):
                st.session_state.pop(
                    f"confirm_delete_exam_{exam['exam_id']}",
                    None,
                )
                st.rerun()

    blueprint_path = exam.get("blueprint_path")
    if blueprint_path:
        with st.expander("View blueprint"):
            try:
                blueprint_pages = download_stored_pages(
                    decode_storage_paths(blueprint_path)
                )
                for page_index, blueprint_page in enumerate(
                    blueprint_pages, start=1
                ):
                    st.image(blueprint_page, caption=f"Blueprint page {page_index}")
            except Exception as error:
                st.warning(f"The stored blueprint could not be displayed: {error}")

    question_paper_path = exam.get("question_paper_path")
    if question_paper_path:
        with st.expander("View question paper"):
            try:
                question_pages = download_stored_pages(
                    decode_storage_paths(question_paper_path)
                )
                for page_index, question_page in enumerate(
                    question_pages, start=1
                ):
                    st.image(question_page, caption=f"Question paper page {page_index}")
            except Exception as error:
                st.warning(
                    f"The stored question paper could not be displayed: {error}"
                )

    document_generation_key = f"paper_document_generation_{exam['exam_id']}"
    document_generation = st.session_state.setdefault(document_generation_key, 0)
    has_configured_marking_scheme = bool(
        (exam.get("marking_scheme") or {}).get("modules")
    )
    with st.expander("Update exam documents"):
        with st.form(
            f"update_exam_documents_{exam['exam_id']}_{document_generation}"
        ):
            new_blueprint_file = st.file_uploader(
                "Replace blueprint answer key (optional)",
                type=["png", "jpg", "jpeg", "webp", "pdf"],
                key=(
                    f"update_blueprint_{exam['exam_id']}_"
                    f"{document_generation}"
                ),
            )
            updated_total_marks = st.number_input(
                (
                    "Total marks (controlled by the marking scheme)"
                    if has_configured_marking_scheme
                    else "Total marks (used when replacing the blueprint)"
                ),
                min_value=1.0,
                value=float(exam["max_marks"]),
                step=1.0,
                disabled=has_configured_marking_scheme,
                key=(
                    f"update_total_marks_{exam['exam_id']}_"
                    f"{document_generation}"
                ),
            )
            new_question_paper_file = st.file_uploader(
                "Replace question paper (optional)",
                type=["png", "jpg", "jpeg", "webp", "pdf"],
                key=(
                    f"update_question_{exam['exam_id']}_"
                    f"{document_generation}"
                ),
            )
            clear_question_paper = st.checkbox(
                "Remove the current question paper",
                key=(
                    f"clear_question_paper_{exam['exam_id']}_"
                    f"{document_generation}"
                ),
            )
            confirm_unclear_document_marks = st.checkbox(
                "I reviewed the replacement documents and confirm the configured "
                "marks wherever a document is unclear.",
                key=(
                    f"confirm_document_marks_{exam['exam_id']}_"
                    f"{document_generation}"
                ),
            )
            update_documents = st.form_submit_button(
                "Save document changes",
                type="primary",
            )
        if update_documents:
            if (
                new_blueprint_file is None
                and new_question_paper_file is None
                and not clear_question_paper
            ):
                st.warning("Choose at least one document change.")
            elif clear_question_paper and new_question_paper_file is not None:
                st.error(
                    "Upload a replacement or remove the current question paper, "
                    "not both."
                )
            else:
                uploaded_paths = []
                try:
                    new_rubric = None
                    new_blueprint_path = None
                    new_marking_scheme = None
                    question_pages = None
                    blueprint_pages = None
                    if new_question_paper_file is not None:
                        question_pages = compress_uploaded_pages(
                            new_question_paper_file
                        )
                    if new_blueprint_file is not None:
                        blueprint_pages = compress_uploaded_pages(
                            new_blueprint_file
                        )
                    new_marking_scheme = exam.get("marking_scheme") or {}
                    if new_marking_scheme.get("modules") and (
                        new_blueprint_file is not None
                        or new_question_paper_file is not None
                    ):
                        if blueprint_pages is None:
                            blueprint_pages = download_stored_pages(
                                decode_storage_paths(exam.get("blueprint_path"))
                            )
                        if question_pages is None:
                            question_pages = download_stored_pages(
                                decode_storage_paths(
                                    exam.get("question_paper_path")
                                )
                            )
                        new_marking_scheme, report = extract_exam_rubric(
                            blueprint_pages,
                            question_pages,
                            new_marking_scheme,
                        )
                        unclear_marks = any(
                            item["blueprint_marks"] is None
                            or item["question_paper_marks"] is None
                            for item in report["items"] + report["modules"]
                        )
                        if (
                            report["missing_rubric"]
                            or report["mark_mismatches"]
                            or report["module_mismatches"]
                            or report["unconfigured_questions"]
                            or report["unconfigured_modules"]
                            or (
                                unclear_marks
                                and not confirm_unclear_document_marks
                            )
                        ):
                            raise ValueError(
                                "The replacement documents do not clearly "
                                "match this exam's marking scheme, or unclear "
                                "marks have not been confirmed."
                            )
                        if new_blueprint_file is not None:
                            new_rubric = {
                                "questions": [
                                    {
                                        "question_no": target["question_no"],
                                        "max_marks": target["max_marks"],
                                        "checkpoints": target["checkpoints"],
                                        "target_id": target["target_id"],
                                    }
                                    for target in get_scoring_targets(
                                        new_marking_scheme
                                    )
                                ]
                            }
                    elif new_blueprint_file is not None:
                        new_rubric = create_blueprint_rubric(
                            blueprint_pages,
                            updated_total_marks,
                        )
                    if new_blueprint_file is not None:
                        blueprint_paths = upload_page_images(
                            blueprint_pages,
                            exam_storage_prefix(exam["exam_id"], "blueprints"),
                        )
                        uploaded_paths.extend(blueprint_paths)
                        new_blueprint_path = encode_storage_paths(blueprint_paths)

                    new_question_paper_path = None
                    if new_question_paper_file is not None:
                        question_paths = upload_page_images(
                            question_pages,
                            exam_storage_prefix(
                                exam["exam_id"],
                                "question-papers",
                            ),
                        )
                        uploaded_paths.extend(question_paths)
                        new_question_paper_path = encode_storage_paths(
                            question_paths
                        )

                    updated_exam = update_exam_documents(
                        exam["exam_id"],
                        teacher_id,
                        blueprint_path=new_blueprint_path,
                        blueprint_rubric=new_rubric,
                        max_marks=(
                            (
                                exam["max_marks"]
                                if has_configured_marking_scheme
                                else updated_total_marks
                            )
                            if new_blueprint_path is not None
                            else None
                        ),
                        question_paper_path=new_question_paper_path,
                        clear_question_paper=clear_question_paper,
                        marking_scheme=(
                            new_marking_scheme
                            if new_marking_scheme and new_marking_scheme.get("modules")
                            else None
                        ),
                    )
                except Exception as error:
                    logger.exception(
                        "Could not update documents for exam %s",
                        exam["exam_id"],
                    )
                    cleanup_errors = []
                    if uploaded_paths:
                        try:
                            remove_unreferenced_exam_files(uploaded_paths)
                        except Exception as cleanup_error:
                            logger.exception(
                                "Could not clean up uncommitted exam files"
                            )
                            cleanup_errors.append(str(cleanup_error))
                    detail = f"Could not update exam documents: {error}"
                    if cleanup_errors:
                        detail += (
                            " Cleanup also failed: " + "; ".join(cleanup_errors)
                        )
                    st.error(detail)
                else:
                    old_paths = set()
                    if new_blueprint_path is not None:
                        old_paths.update(
                            decode_storage_paths(exam.get("blueprint_path"))
                        )
                    if (
                        new_question_paper_path is not None
                        or clear_question_paper
                    ):
                        old_paths.update(
                            decode_storage_paths(exam.get("question_paper_path"))
                        )
                    try:
                        remove_unreferenced_exam_files(old_paths)
                    except Exception as error:
                        st.warning(
                            "Documents were updated, but old files could not be "
                            f"fully removed from storage: {error}"
                        )
                    st.session_state[document_generation_key] += 1
                    st.success(
                        f"Documents for {updated_exam['title']} were updated."
                    )
                    st.rerun()

    marking_scheme = exam.get("marking_scheme") or {}
    if marking_scheme.get("modules"):
        edit_namespace = f"paper_edit_{exam['exam_id']}"
        with st.expander(
            "Edit marking scheme (available before any submissions)",
            expanded=False,
        ):
            updated_total_marks = st.number_input(
                "Updated total examination marks",
                min_value=1.0,
                value=float(exam["max_marks"]),
                step=1.0,
                key=f"edit_exam_total_marks_{exam['exam_id']}",
            )
            edited_scheme, _ = render_marking_scheme_editor(
                updated_total_marks,
                edit_namespace,
                initial_scheme=marking_scheme,
            )
            marks_confirmed = st.checkbox(
                "I reviewed the updated marks against this exam's documents.",
                key=f"confirm_edit_exam_scheme_{exam['exam_id']}",
            )
            if st.button(
                "Validate and save marking scheme",
                key=f"save_exam_scheme_{exam['exam_id']}",
                type="primary",
                disabled=not marks_confirmed,
            ):
                try:
                    validate_marking_scheme(
                        edited_scheme,
                        updated_total_marks,
                    )
                    blueprint_pages = download_stored_pages(
                        decode_storage_paths(exam["blueprint_path"])
                    )
                    question_pages = download_stored_pages(
                        decode_storage_paths(exam["question_paper_path"])
                    )
                    checked_scheme, report = extract_exam_rubric(
                        blueprint_pages,
                        question_pages,
                        edited_scheme,
                    )
                    if (
                        report["missing_rubric"]
                        or report["mark_mismatches"]
                        or report["module_mismatches"]
                        or report["unconfigured_questions"]
                        or report["unconfigured_modules"]
                    ):
                        raise ValueError(
                            "The updated scheme does not match the readable "
                            "question/blueprint structure. Correct the structure "
                            "or expected concepts and try again."
                        )
                    rubric = {
                        "questions": [
                            {
                                "question_no": target["question_no"],
                                "max_marks": target["max_marks"],
                                "checkpoints": target["checkpoints"],
                                "target_id": target["target_id"],
                            }
                            for target in get_scoring_targets(checked_scheme)
                        ]
                    }
                    with st.spinner("Saving this exam's marking scheme..."):
                        update_exam_marking_scheme(
                            exam["exam_id"],
                            teacher_id,
                            checked_scheme,
                            updated_total_marks,
                            rubric,
                        )
                except Exception as error:
                    st.error(f"Could not update the marking scheme: {error}")
                else:
                    st.session_state[
                        f"{edit_namespace}_marking_generation"
                    ] += 1
                    st.success("This exam's marking scheme was updated.")
                    st.rerun()

    st.subheader("Upload student answer sheets")
    try:
        enrolled_students = get_enrolled_students_for_subject(
            exam["subject_id"], teacher_id
        )
    except Exception as error:
        st.error(f"Could not load the enrolled students: {error}")
        return
    if not enrolled_students:
        st.info("No students are enrolled in this exam's subject.")
    else:
        student_names = {
            student["student_id"]: student["name"]
            for student in enrolled_students
        }
        student_ids = [None] + list(student_names)
        student_files = st.file_uploader(
            "Student answer sheets (image or PDF)",
            type=["png", "jpg", "jpeg", "webp", "pdf"],
            accept_multiple_files=True,
            key=f"paper_sheets_{exam['exam_id']}",
        )
        student_mapping = {}
        for index, uploaded_file in enumerate(student_files or []):
            student_mapping[index] = st.selectbox(
                f"Student for {uploaded_file.name}",
                student_ids,
                format_func=lambda student_id: (
                    "Choose a student" if student_id is None
                    else student_names[student_id]
                ),
                key=f"paper_student_{exam['exam_id']}_{index}",
            )
        valid_mapping = (
            student_files
            and all(student_mapping.get(index) is not None for index in range(len(student_files)))
            and len(set(student_mapping.values())) == len(student_mapping)
        )
        if student_files and not valid_mapping:
            st.warning("Choose a different enrolled student for each answer sheet.")
        if st.button(
            "Evaluate answer sheets",
            type="primary",
            disabled=not valid_mapping,
            key=f"evaluate_papers_{exam['exam_id']}",
        ):
            progress = st.progress(0, text="Preparing AI evaluation...")
            errors = []
            total_files = len(student_files)
            for index, uploaded_file in enumerate(student_files):
                progress.progress(
                    index / total_files,
                    text=f"Evaluating {uploaded_file.name} ({index + 1}/{total_files})...",
                )
                submission = None
                try:
                    pages = compress_uploaded_pages(uploaded_file)
                    sheet_paths = upload_page_images(
                        pages,
                        exam_storage_prefix(exam["exam_id"], "submissions"),
                    )
                    submission = insert_paper_submission(
                        exam["exam_id"],
                        teacher_id,
                        student_mapping[index],
                        encode_storage_paths(sheet_paths),
                    )
                    ai_marks, evaluation_result = evaluate_exam_pages(
                        exam,
                        pages,
                    )
                    update_paper_evaluation(
                        submission["submission_id"],
                        exam["exam_id"],
                        teacher_id,
                        ai_marks,
                        evaluation_result,
                    )
                except Exception as error:
                    logger.exception(
                        "Could not evaluate answer sheet %s", uploaded_file.name
                    )
                    if submission is not None:
                        try:
                            record_paper_evaluation_error(
                                submission["submission_id"],
                                exam["exam_id"],
                                teacher_id,
                                error,
                            )
                        except Exception:
                            logger.exception(
                                "Could not persist the paper evaluation error"
                            )
                    errors.append(f"{uploaded_file.name}: {error}")
                progress.progress(
                    (index + 1) / total_files,
                    text=f"Completed {index + 1} of {total_files} answer sheets.",
                )
            if errors:
                st.warning("Some answer sheets could not be evaluated:")
                for error in errors:
                    st.error(error)
            else:
                st.success(f"Evaluated {total_files} answer sheet(s).")

    st.divider()
    st.subheader("Teacher review & audit")
    try:
        submissions = get_paper_submissions_for_teacher(
            exam["exam_id"], teacher_id
        )
    except Exception as error:
        st.error(f"Could not load paper submissions: {error}")
        return
    if not submissions:
        st.info("No answer sheets have been submitted for this exam yet.")
        return

    for submission in submissions:
        student = submission.get("students") or {}
        status = submission["status"]
        with st.container(border=True):
            st.write(
                f"**{student.get('name', 'Student')}** · "
                f"Student ID #ST-{submission.get('student_id', 'unknown')} · "
                f"{status.capitalize()}"
            )
            st.caption(
                f"Uploaded {submission['created_at']} · "
                f"AI score: {submission.get('ai_marks', 'Not evaluated')} / "
                f"{exam['max_marks']}"
            )
            student_answers = submission.get("student_answers")
            if student_answers:
                answers = student_answers.get("answers", {})
                with st.expander("View student's submitted answers"):
                    for module in (exam.get("marking_scheme") or {}).get(
                        "modules",
                        [],
                    ):
                        st.markdown(
                            f"**{module['name']} — {module['max_marks']} marks**"
                        )
                        for question in module["questions"]:
                            group_id = question.get("or_group_id")
                            if group_id:
                                question_targets = question.get(
                                    "subquestions",
                                    [],
                                ) or [question]
                                answer_ids = [
                                    target.get("subquestion_id")
                                    or target.get("question_id")
                                    for target in question_targets
                                ]
                                attempted = any(
                                    str(answers.get(answer_id, "")).strip()
                                    for answer_id in answer_ids
                                )
                                st.caption(
                                    f"{question['label']} — "
                                    f"{'attempted' if attempted else 'not attempted'}"
                                )
                            targets = question.get("subquestions", [])
                            if targets:
                                for subquestion in targets:
                                    st.write(
                                        f"**{subquestion['label']}**: "
                                        f"{answers.get(subquestion['subquestion_id'], '')}"
                                    )
                            else:
                                st.write(
                                    f"**{question['label']}**: "
                                    f"{answers.get(question['question_id'], '')}"
                                )
            elif submission.get("sheet_path"):
                try:
                    image_pages = download_stored_pages(
                        decode_storage_paths(submission["sheet_path"])
                    )
                    with st.expander("View uploaded answer sheet"):
                        for page_index, image_page in enumerate(image_pages, start=1):
                            st.image(image_page, caption=f"Page {page_index}")
                except Exception as error:
                    st.warning(
                        f"The stored answer sheet could not be displayed: {error}"
                    )

            details = submission.get("evaluation_details") or []
            if isinstance(details, dict) and "modules" in details:
                marking_scheme = exam.get("marking_scheme") or {}
                revised_scores = target_scores_from_result(details)
                for module_result in details["modules"]:
                    st.markdown(
                        f"### {module_result['name']} · "
                        f"{module_result['awarded_marks']} / "
                        f"{module_result['max_marks']}"
                    )
                    for group in module_result.get("or_groups", []):
                        selected_labels = [
                            alternative["question_no"]
                            for alternative in group["selected_alternatives"]
                        ]
                        selected_text = (
                            ", ".join(selected_labels)
                            if selected_labels
                            else "None (no alternative attempted)"
                        )
                        st.info(
                            f"OR group {group['label']} · Final selected "
                            f"alternative(s): {selected_text} · Official marks "
                            f"awarded: {group['awarded_marks']} / "
                            f"{group['max_marks'] * group['allowed_attempts']:g}"
                        )
                    for question in module_result["questions"]:
                        counted = (
                            " · counted"
                            if question.get("counted_for_score")
                            else " · not counted"
                            if question.get("or_group_id")
                            else ""
                        )
                        st.markdown(
                            f"**{question['question_no']}** · "
                            f"{question['awarded_marks']} / "
                            f"{question['max_marks']}{counted}"
                        )
                        scoring_items = question.get("subquestions", [])
                        if not scoring_items:
                            scoring_items = [{
                                "target_id": question["question_id"],
                                "question_no": question["question_no"],
                                "max_marks": question["max_marks"],
                                "awarded_marks": question["awarded_marks"],
                                "semantic_match_pct": question.get(
                                    "semantic_match_pct",
                                    0,
                                ),
                                "feedback": question.get("feedback", ""),
                            }]
                        for item in scoring_items:
                            st.caption(
                                f"{item['question_no']} · "
                                f"{item['awarded_marks']} / {item['max_marks']} "
                                f"({item.get('semantic_match_pct', 0)}% match)"
                            )
                            st.caption(item.get("feedback", ""))
                            if status == "evaluated":
                                mark = st.number_input(
                                    f"Override marks for {item['question_no']}",
                                    min_value=0.0,
                                    max_value=float(item["max_marks"]),
                                    value=float(item["awarded_marks"]),
                                    step=0.5,
                                    key=(
                                        f"paper_override_{submission['submission_id']}_"
                                        f"{item['target_id']}"
                                    ),
                                )
                                revised_scores[item["target_id"]][
                                    "awarded_marks"
                                ] = mark
                revised_result = calculate_exam_result(
                    marking_scheme,
                    revised_scores,
                )
                if status == "evaluated":
                    st.metric(
                        "Proposed final score",
                        f"{revised_result['final_marks']} / {exam['max_marks']}",
                    )
                    if st.button(
                        "Verify & Publish",
                        type="primary",
                        key=f"verify_paper_{submission['submission_id']}",
                    ):
                        try:
                            save_teacher_verified_marks(
                                submission["submission_id"],
                                exam["exam_id"],
                                teacher_id,
                                revised_result["final_marks"],
                                revised_result,
                            )
                        except Exception as error:
                            st.error(f"Could not publish this score: {error}")
                        else:
                            st.success(
                                "Verified score published to the student portal."
                            )
                            st.rerun()
                elif status == "verified":
                    st.success(
                        f"Published score: {submission.get('final_marks')} / "
                        f"{exam['max_marks']} · reviewed "
                        f"{submission.get('reviewed_at')}"
                    )
                continue
            if isinstance(details, dict):
                st.warning(details.get("error", "AI evaluation is pending."))
                if status == "pending" and submission.get("sheet_path"):
                    if st.button(
                        "Retry AI evaluation",
                        key=f"retry_paper_{submission['submission_id']}",
                    ):
                        try:
                            retry_pages = download_stored_pages(
                                decode_storage_paths(submission["sheet_path"])
                            )
                            if not retry_pages:
                                raise ValueError(
                                    "No stored answer-sheet pages were found. "
                                    "Upload the sheet again to retry evaluation."
                                )
                            ai_marks, evaluation_result = evaluate_exam_pages(
                                exam,
                                retry_pages,
                            )
                            update_paper_evaluation(
                                submission["submission_id"],
                                exam["exam_id"],
                                teacher_id,
                                ai_marks,
                                evaluation_result,
                            )
                        except Exception as error:
                            logger.exception(
                                "Could not retry answer sheet evaluation %s",
                                submission["submission_id"],
                            )
                            try:
                                record_paper_evaluation_error(
                                    submission["submission_id"],
                                    exam["exam_id"],
                                    teacher_id,
                                    error,
                                )
                            except Exception:
                                logger.exception(
                                    "Could not persist the retry evaluation error"
                                )
                            st.error(f"Could not retry AI evaluation: {error}")
                        else:
                            st.success("Answer sheet evaluated successfully.")
                            st.rerun()
                continue
            if details:
                revised_details = []
                mark_inputs = []
                for question in details:
                    st.markdown(
                        f"**Question {question['question_no']}** · "
                        f"{question['awarded_marks']} / {question['max_marks']} "
                        f"({question['semantic_match_pct']}% semantic match)"
                    )
                    st.caption(question.get("feedback", ""))
                    if status == "evaluated":
                        mark = st.number_input(
                            f"Override marks for question {question['question_no']}",
                            min_value=0.0,
                            max_value=float(question["max_marks"]),
                            value=float(question["awarded_marks"]),
                            step=0.5,
                            key=(
                                f"paper_override_{submission['submission_id']}_"
                                f"{question['question_no']}"
                            ),
                        )
                        mark_inputs.append(mark)
                        revised_details.append({**question, "awarded_marks": mark})
                    else:
                        revised_details.append(question)
                if status == "evaluated":
                    final_marks = round(sum(mark_inputs), 2)
                    st.metric("Proposed final score", f"{final_marks} / {exam['max_marks']}")
                    if st.button(
                        "Verify & Publish",
                        type="primary",
                        key=f"verify_paper_{submission['submission_id']}",
                    ):
                        try:
                            save_teacher_verified_marks(
                                submission["submission_id"],
                                exam["exam_id"],
                                teacher_id,
                                final_marks,
                                revised_details,
                            )
                        except Exception as error:
                            st.error(f"Could not publish this score: {error}")
                        else:
                            st.success("Verified score published to the student portal.")
                            st.rerun()
                elif status == "verified":
                    st.success(
                        f"Published score: {submission.get('final_marks')} / "
                        f"{exam['max_marks']} · reviewed {submission.get('reviewed_at')}"
                    )


def teacher_tab_live_sessions():
    from datetime import datetime, timezone
    from io import BytesIO
    from urllib.parse import urlencode, urlsplit, urlunsplit

    import segno

    from src.database.db import (
        close_class_session,
        extend_class_session,
        get_class_sessions_for_teacher,
        get_pending_class_checkins,
        get_teacher_subjects,
        open_class_session,
        review_class_checkin,
        rotate_class_session_code,
    )
    from src.pipelines.class_checkin import generate_class_access_code

    teacher_id = st.session_state.teacher_data['teacher_id']
    st.header('Live class check-in')
    st.caption(
        'Open a time-limited code for an enrolled class. Strong face/voice matches '
        'are recorded; borderline matches wait for your review. Opening a new '
        'session for the same subject finalizes the earlier session.'
    )
    subjects = get_teacher_subjects(teacher_id)
    if not subjects:
        st.info('Create a subject before opening a live check-in session.')
        return

    subject_options = {
        f"{subject['name']} — {subject['subject_code']}": subject['subject_id']
        for subject in subjects
    }
    with st.container(border=True):
        selected_label = st.selectbox(
            'Subject for this session',
            list(subject_options),
            key='live_checkin_subject',
        )
        duration_minutes = st.selectbox(
            'Code lifetime',
            (5, 10, 15, 30, 45, 60),
            index=2,
            format_func=lambda minutes: f'{minutes} minutes',
            key='live_checkin_duration',
        )
        if st.button(
            'Open live check-in',
            type='primary',
            width='stretch',
            key='open_live_checkin',
        ):
            try:
                open_class_session(
                    subject_options[selected_label],
                    teacher_id,
                    generate_class_access_code(),
                    duration_minutes,
                )
            except Exception as error:
                st.error(f'Could not open the check-in session: {error}')
            else:
                st.success('Live check-in is open.')
                st.rerun()

    sessions = get_class_sessions_for_teacher(teacher_id)
    active_sessions = []
    now = datetime.now(timezone.utc)
    for session in sessions:
        expires_at = datetime.fromisoformat(
            session['expires_at'].replace('Z', '+00:00')
        )
        active = session.get('closed_at') is None and expires_at > now
        if active:
            active_sessions.append(session)
            subject = session.get('subjects') or {}
            st.subheader(
                f"Active: {subject.get('name', 'Class')} "
                f"({subject.get('subject_code', '')})"
            )
            st.code(session['access_code'], language=None)
            st.caption(
                f"Expires at {expires_at.astimezone().strftime('%Y-%m-%d %I:%M %p')}"
            )
            remaining_seconds = max(0, int((expires_at - now).total_seconds()))
            minutes, seconds = divmod(remaining_seconds, 60)
            st.metric("Session window", f"{minutes:02d}:{seconds:02d} remaining")

            parsed_url = urlsplit(st.context.url)
            checkin_url = urlunsplit((
                parsed_url.scheme,
                parsed_url.netloc,
                parsed_url.path,
                urlencode({
                    'page': 'student',
                    'session-code': session['access_code'],
                }),
                '',
            ))
            qr_buffer = BytesIO()
            segno.make_qr(checkin_url).save(
                qr_buffer,
                kind='png',
                scale=5,
                border=2,
            )
            st.image(
                qr_buffer.getvalue(),
                width=190,
                alt='QR code linking to the student check-in page with this session code',
            )
            st.caption(
                'Students must sign in and be enrolled in this class. Do not '
                'share this QR/code outside the room.'
            )
            if parsed_url.hostname in {'localhost', '127.0.0.1'}:
                st.warning(
                    'This QR points to a local development address. Use a '
                    'network-accessible deployment when students scan it.'
                )

            extend_col, rotate_col, close_col = st.columns(3)
            with extend_col:
                if st.button(
                    "Extend session (+5m)",
                    key=f"extend_session_{session['session_id']}",
                    width="stretch",
                ):
                    try:
                        extend_class_session(session['session_id'], teacher_id)
                    except Exception as error:
                        st.error(f'Could not extend the session: {error}')
                    else:
                        st.success('Session extended by five minutes.')
                        st.rerun()
            with rotate_col:
                if st.button(
                    'Rotate code',
                    key=f"rotate_session_{session['session_id']}",
                    width='stretch',
                ):
                    try:
                        rotate_class_session_code(
                            session['session_id'],
                            teacher_id,
                            generate_class_access_code(),
                        )
                    except Exception as error:
                        st.error(f'Could not rotate the code: {error}')
                    else:
                        st.rerun()
            with close_col:
                if st.button(
                    'Close session',
                    key=f"close_session_{session['session_id']}",
                    type='secondary',
                    width='stretch',
                ):
                    try:
                        close_class_session(session['session_id'], teacher_id)
                    except Exception as error:
                        st.error(f'Could not close the session: {error}')
                    else:
                        st.success('Check-in session closed.')
                        st.rerun()

    if not active_sessions:
        st.info('There are no active live check-in sessions.')
    if sessions:
        with st.expander('Recent session history'):
            for session in sessions:
                subject = session.get('subjects') or {}
                expires_at = datetime.fromisoformat(
                    session['expires_at'].replace('Z', '+00:00')
                )
                state = (
                    'Closed'
                    if session.get('closed_at')
                    else 'Expired'
                    if expires_at <= now
                    else 'Active'
                )
                st.caption(
                    f"{subject.get('name', 'Class')} · {state} · "
                    f"started {session['started_at']}"
                )
                if state == 'Expired' and session.get('closed_at') is None:
                    if st.button(
                        'Finalize attendance',
                        key=f"finalize_session_{session['session_id']}",
                    ):
                        try:
                            close_class_session(
                                session['session_id'], teacher_id
                            )
                        except Exception as error:
                            st.error(f'Could not finalize attendance: {error}')
                        else:
                            st.success('Session finalized.')
                            st.rerun()

    st.divider()
    st.subheader('Check-ins needing review')
    pending_checkins = get_pending_class_checkins(teacher_id)
    if not pending_checkins:
        st.info('No borderline face or voice matches are waiting for review.')
        return

    for checkin in pending_checkins:
        student = checkin.get('students') or {}
        session = checkin.get('class_sessions') or {}
        subject = session.get('subjects') or {}
        method = checkin['verification_method']
        score = checkin['verification_score']
        score_label = (
            f'{score:.3f} face distance'
            if method == 'face'
            else f'{score:.1%} voice similarity'
        )
        with st.container(border=True):
            st.write(
                f"**{student.get('name', 'Student')}** — "
                f"{subject.get('name', 'Class')} "
                f"({subject.get('subject_code', '')})"
            )
            st.caption(
                f"Submitted {checkin['submitted_at']} · "
                f"{method.capitalize()} · {score_label}"
            )
            flags = checkin.get('risk_flags') or []
            if flags:
                st.warning(
                    'Review flags: '
                    + ', '.join(flag.replace('_', ' ') for flag in flags)
                )
            if checkin.get('latitude') is not None:
                location_url = (
                    'https://www.google.com/maps/search/?api=1&query='
                    f"{checkin['latitude']},{checkin['longitude']}"
                )
                st.markdown(f'[View optional submitted location]({location_url})')
                if checkin.get('location_accuracy_m') is not None:
                    st.caption(
                        'Reported GPS accuracy: '
                        f"{checkin['location_accuracy_m']} m"
                    )

            approve_col, reject_col = st.columns(2)
            with approve_col:
                if st.button(
                    'Approve check-in',
                    key=f"approve_class_checkin_{checkin['checkin_id']}",
                    type='primary',
                    width='stretch',
                ):
                    try:
                        review_class_checkin(
                            checkin['checkin_id'], teacher_id, approved=True
                        )
                    except Exception as error:
                        st.error(f'Could not approve this check-in: {error}')
                    else:
                        st.success('Attendance approved and recorded.')
                        st.rerun()
            with reject_col:
                if st.button(
                    'Reject check-in',
                    key=f"reject_class_checkin_{checkin['checkin_id']}",
                    type='secondary',
                    width='stretch',
                ):
                    try:
                        review_class_checkin(
                            checkin['checkin_id'], teacher_id, approved=False
                        )
                    except Exception as error:
                        st.error(f'Could not reject this check-in: {error}')
                    else:
                        st.success('Check-in rejected.')
                        st.rerun()


def login_teacher(username, password):
    from src.database.db import teacher_login

    if not username or not password:
        return False
    
    teacher = teacher_login(username, password)

    if teacher:
        st.session_state.user_role ='teacher'
        st.session_state.teacher_data = teacher
        st.session_state.is_logged_in = True
        return True
    

    return False
def teacher_screen_login():
    c1, c2 = st.columns(2, vertical_alignment='center', gap='xxlarge')
    with c1:
        header_dashboard()
    with c2:
        if st.button("Go back to Home", type='secondary', key='loginbackbtn', shortcut="control+backspace"):
            navigate_to('home')

    st.header('Login using password', text_alignment='center')
    st.space()
    st.space()


    teacher_username = st.text_input("Enter username", placeholder='ananyaroy')

    teacher_pass = st.text_input("Enter password", type='password', placeholder="Enter password")

    st.divider()

    btnc1, btnc2 = st.columns(2)

    with btnc1:
        if st.button('Login', icon=':material/passkey:', shortcut='control+enter', width='stretch'):
            if login_teacher(teacher_username, teacher_pass):
                st.toast("welcome back!", icon="👋")
                st.rerun()
            else:
                st.error("Invalid username and password combo")

    with btnc2:
        if st.button('Register Instead', type="primary", icon=':material/passkey:', width='stretch'):
            st.session_state.teacher_login_type = 'register'




def register_teacher(teacher_username, teacher_name, teacher_pass, teacher_pass_confirm):
    from src.database.db import check_teacher_exists, create_teacher

    if not teacher_username or not teacher_name or not teacher_pass:
        return False, "All Fields are required!"
    if check_teacher_exists(teacher_username):
        return False, "Username already taken"
    if teacher_pass != teacher_pass_confirm:
        return False, "Password doesn't match"
    
    try:
        create_teacher(teacher_username, teacher_pass, teacher_name)
        return True, "Sucessfully Created! Login Now"
    except Exception as e:
        return False, "Unexpected Error!"
    

def teacher_screen_register():
    c1, c2 = st.columns(2, vertical_alignment='center', gap='xxlarge')
    with c1:
        header_dashboard()
    with c2:
        if st.button("Go back to Home", type='secondary', key='loginbackbtn', shortcut="control+backspace"):
            navigate_to('home')



    st.header('Register your teacher profile')

    st.space()
    st.space()

    
    teacher_username = st.text_input("Enter username", placeholder='ananyaroy')

    teacher_name = st.text_input("Enter name", placeholder='Ananya Roy')

    teacher_pass = st.text_input("Enter password", type='password', placeholder="Enter password")

    teacher_pass_confirm = st.text_input("Confirm your password", type='password', placeholder="Enter password")

    st.divider()

    btnc1, btnc2 = st.columns(2)

    with btnc1:
        if st.button('Register now', icon=':material/passkey:', shortcut='control+enter', width='stretch'):
            success, message = register_teacher(teacher_username, teacher_name, teacher_pass, teacher_pass_confirm)
            if success:
                st.success(message)
                st.session_state.teacher_login_type = "login"
                st.rerun()
            else:
                st.error(message)


    with btnc2:
        if st.button('Login Instead', type="primary", icon=':material/passkey:', width='stretch'):
            st.session_state.teacher_login_type = 'login'
