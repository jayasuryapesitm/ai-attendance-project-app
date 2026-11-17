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
    tab1, tab2, tab3, tab4, tab5 = st.columns(5)


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
