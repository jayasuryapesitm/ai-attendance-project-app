import logging
import math
from datetime import datetime, timedelta, timezone

import bcrypt
import httpx
from postgrest.exceptions import APIError

from src.database.config import supabase


logger = logging.getLogger(__name__)


def _show_connection_error():
    logger.exception("Supabase connection failed")
    from streamlit import error as show_error

    show_error(
        "Could not connect to Supabase. Check that SUPABASE_URL is the URL "
        "of an active Supabase project and that your internet connection or "
        "firewall allows access, then restart the app."
    )



def hash_pass(pwd):
    return bcrypt.hashpw(pwd.encode(), bcrypt.gensalt()).decode()

def check_pass(pwd, hashed):
    return bcrypt.checkpw(pwd.encode(), hashed.encode())


def check_teacher_exists(username):
    # Check for unique username, returns false when username is already taken
    response = supabase.table("teachers").select("username").eq("username", username).execute()
    return len(response.data) > 0 



def create_teacher(username, password, name):

    data = { "username" : username, "password": hash_pass(password), "name": name}
    response = supabase.table("teachers").insert(data).execute()
    return response.data


def teacher_login(username, password):
    response = supabase.table("teachers").select("*").eq("username", username).execute()
    if response.data:
        teacher = response.data[0]
        if check_pass(password, teacher['password']):
            return teacher
    return None


def get_all_students():
    try:
        response = supabase.table('students').select("*").execute()
    except RuntimeError as error:
        from streamlit import error as show_error
        show_error(str(error))
        return []
    except (httpx.ConnectError, httpx.TimeoutException):
        _show_connection_error()
        return []
    return response.data

def create_student(
    new_name,
    face_embedding=None,
    voice_embedding=None,
    face_consent=False,
    voice_consent=False,
):
    from datetime import datetime, timezone

    consented_at = datetime.now(timezone.utc).isoformat()
    data = {
        'name': new_name,
        'face_embedding': face_embedding,
        'voice_embedding': voice_embedding,
        'face_consent_at': consented_at if face_consent else None,
        'voice_consent_at': consented_at if voice_consent else None,
    }
    response = supabase.table('students').insert(data).execute()
    return response.data


def save_student_voice_profile(student_id, voice_embedding):
    from datetime import datetime, timezone

    response = (
        supabase.table('students')
        .update({
            'voice_embedding': voice_embedding,
            'voice_consent_at': datetime.now(timezone.utc).isoformat(),
        })
        .eq('student_id', student_id)
        .select('*')
        .execute()
    )
    if not response.data:
        raise ValueError('Could not save the voice profile for this student.')
    from src.pipelines.face_pipeline import get_trained_model

    get_trained_model.clear()
    return response.data[0]


def record_student_biometric_consent(student_id, method):
    from datetime import datetime, timezone

    consent_columns = {
        'face': 'face_consent_at',
        'voice': 'voice_consent_at',
    }
    if method not in consent_columns:
        raise ValueError('Unsupported biometric consent type.')

    try:
        response = (
            supabase.table('students')
            .update({
                consent_columns[method]: datetime.now(timezone.utc).isoformat()
            })
            .eq('student_id', student_id)
            .select('student_id')
            .execute()
        )
    except APIError as error:
        logger.exception("Could not record biometric consent")
        error_code = getattr(error, "code", None)
        if error_code == "401" or "JWT" in str(error).upper():
            raise RuntimeError(
                "Supabase rejected SUPABASE_KEY (HTTP 401). Copy a current "
                "server-side secret key from the active Supabase project API "
                "settings into .streamlit/secrets.toml, then restart the app."
            ) from error
        raise RuntimeError(
            "Could not save biometric consent. Run sql/students.sql in the "
            "Supabase SQL Editor, then restart the app. If the problem "
            "continues, verify that SUPABASE_KEY is a server-side key."
        ) from error
    if not response.data:
        raise ValueError('Could not record biometric consent.')


def delete_student_account(student_id):
    response = supabase.rpc(
        'delete_student_account',
        {'p_student_id': student_id},
    ).execute()
    if not response.data:
        raise ValueError('The student profile could not be deleted.')
    from src.pipelines.face_pipeline import get_trained_model

    get_trained_model.clear()


def create_subject(subject_code, name, section, teacher_id):
    data = {"subject_code": subject_code, "name": name, "section": section, "teacher_id": teacher_id}
    response = supabase.table("subjects").insert(data).execute()
    return response.data


def delete_teacher_subject(subject_id, teacher_id):
    response = supabase.rpc(
        'delete_teacher_subject',
        {
            'p_subject_id': subject_id,
            'p_teacher_id': teacher_id,
        },
    ).execute()
    if not response.data:
        raise ValueError('The subject could not be deleted.')


def get_teacher_subjects(teacher_id):
    subjects = (
        supabase.table("subjects")
        .select("*")
        .eq("teacher_id", teacher_id)
        .execute()
        .data
    )

    for subject in subjects:
        subject_id = subject["subject_id"]
        student_count = (
            supabase.table("subject_students")
            .select("student_id", count="exact")
            .eq("subject_id", subject_id)
            .execute()
        )
        attendance = (
            supabase.table("attendance_logs")
            .select("timestamp")
            .eq("subject_id", subject_id)
            .execute()
            .data
        )
        subject["total_students"] = student_count.count or 0
        subject["total_classes"] = len(
            {log["timestamp"] for log in attendance if log.get("timestamp")}
        )

    return subjects


def  enroll_student_to_subject(student_id, subject_id):
    data = {'student_id': student_id, "subject_id": subject_id}
    response= supabase.table('subject_students').insert(data).execute()
    return response.data


def  unenroll_student_to_subject(student_id, subject_id):
    response= supabase.table('subject_students').delete().eq('student_id', student_id).eq('subject_id', subject_id).execute()
    return response.data



def get_student_subjects(student_id):
    response = supabase.table('subject_students').select('*, subjects(*)').eq('student_id', student_id).execute()
    return response.data


def get_student_attendance(student_id):
    response = supabase.table('attendance_logs').select('*, subjects(*)').eq('student_id', student_id).execute()
    return response.data


def create_attendance(logs):
    response = supabase.table('attendance_logs').insert(logs).execute()
    return response.data

def get_attendance_for_teacher(teacher_id):
    subjects = (
        supabase.table("subjects")
        .select("*")
        .eq("teacher_id", teacher_id)
        .execute()
        .data
    )
    if not subjects:
        return []

    subject_by_id = {subject["subject_id"]: subject for subject in subjects}
    attendance = (
        supabase.table("attendance_logs")
        .select("*")
        .in_("subject_id", list(subject_by_id))
        .execute()
        .data
    )
    student_ids = {row["student_id"] for row in attendance if row.get("student_id")}
    students = (
        supabase.table("students")
        .select("student_id, name")
        .in_("student_id", list(student_ids))
        .execute()
        .data
        if student_ids
        else []
    )
    student_by_id = {student["student_id"]: student for student in students}

    for row in attendance:
        row["subjects"] = subject_by_id.get(row["subject_id"], {})
        row["students"] = student_by_id.get(row.get("student_id"), {})

    return attendance


def get_student_voice_attendance(student_id):
    response = (
        supabase.table('voice_attendance_submissions')
        .select('*')
        .eq('student_id', student_id)
        .order('submitted_at', desc=True)
        .execute()
    )
    return response.data


def get_pending_voice_attendance_for_subjects(subject_ids):
    if not subject_ids:
        return []

    response = (
        supabase.table('voice_attendance_submissions')
        .select('*')
        .in_('subject_id', subject_ids)
        .eq('status', 'pending')
        .order('submitted_at', desc=True)
        .execute()
    )
    return response.data


def submit_voice_attendance(
    student_id,
    student_name,
    subject_id,
    subject_name,
    subject_code,
    voice_match_score,
    latitude,
    longitude,
    location_accuracy_m,
):
    response = supabase.rpc(
        'submit_voice_attendance',
        {
            'p_student_id': student_id,
            'p_student_name': student_name,
            'p_subject_id': subject_id,
            'p_subject_name': subject_name,
            'p_subject_code': subject_code,
            'p_voice_match_score': voice_match_score,
            'p_latitude': latitude,
            'p_longitude': longitude,
            'p_location_accuracy_m': location_accuracy_m,
        },
    ).execute()
    return response.data


def review_voice_attendance(submission_id, teacher_id, approved):
    response = supabase.rpc(
        'review_voice_attendance',
        {
            'p_submission_id': submission_id,
            'p_teacher_id': teacher_id,
            'p_approved': approved,
        },
    ).execute()
    if not response.data:
        raise ValueError('This request was already reviewed or is not in your classes.')
    return response.data


def open_class_session(subject_id, teacher_id, access_code, duration_minutes):
    response = supabase.rpc(
        'open_class_session',
        {
            'p_subject_id': subject_id,
            'p_teacher_id': teacher_id,
            'p_access_code': access_code,
            'p_duration_minutes': duration_minutes,
        },
    ).execute()
    if not response.data:
        raise ValueError('The class session could not be opened.')
    return response.data[0]


def rotate_class_session_code(session_id, teacher_id, access_code):
    response = supabase.rpc(
        'rotate_class_session_code',
        {
            'p_session_id': session_id,
            'p_teacher_id': teacher_id,
            'p_access_code': access_code,
        },
    ).execute()
    if not response.data:
        raise ValueError('The active class code could not be rotated.')
    return response.data[0]


def close_class_session(session_id, teacher_id):
    response = supabase.rpc(
        'close_class_session',
        {'p_session_id': session_id, 'p_teacher_id': teacher_id},
    ).execute()
    if not response.data:
        raise ValueError('The class session could not be closed.')
    return response.data[0]


def extend_class_session(session_id, teacher_id):
    session_response = (
        supabase.table("class_sessions")
        .select("expires_at, closed_at")
        .eq("session_id", session_id)
        .eq("teacher_id", teacher_id)
        .execute()
    )
    if not session_response.data:
        raise ValueError("The live class session could not be found.")

    session = session_response.data[0]
    if session.get("closed_at") is not None:
        raise ValueError("A closed class session cannot be extended.")

    expires_at = datetime.fromisoformat(
        session["expires_at"].replace("Z", "+00:00")
    )
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= datetime.now(timezone.utc):
        raise ValueError("An expired class session cannot be extended.")

    updated = (
        supabase.table("class_sessions")
        .update({"expires_at": (expires_at + timedelta(minutes=5)).isoformat()})
        .eq("session_id", session_id)
        .eq("teacher_id", teacher_id)
        .is_("closed_at", "null")
        .execute()
    )
    if not updated.data:
        raise ValueError("The class session could not be extended.")
    return updated.data[0]


def get_class_sessions_for_teacher(teacher_id):
    try:
        sessions = (
            supabase.table("class_sessions")
            .select("*")
            .eq('teacher_id', teacher_id)
            .order('started_at', desc=True)
            .limit(100)
            .execute()
            .data
        )
    except APIError:
        logger.exception("Could not load live class sessions")
        from streamlit import error as show_error

        show_error(
            "Live Sessions are not available yet. Run "
            "sql/class_checkin_sessions.sql in the SQL Editor for the "
            "Supabase project configured in this app."
        )
        return []
    subject_ids = {session["subject_id"] for session in sessions}
    subjects = []
    if subject_ids:
        try:
            subjects = (
                supabase.table("subjects")
                .select("subject_id, name, subject_code, section")
                .in_("subject_id", list(subject_ids))
                .execute()
                .data
            )
        except APIError:
            logger.exception("Could not load subjects for live class sessions")
    subject_by_id = {subject["subject_id"]: subject for subject in subjects}
    for session in sessions:
        session["subjects"] = subject_by_id.get(session["subject_id"], {})
    return sessions


def get_live_campus_session_count(teacher_id=None):
    """Return the number of active class sessions currently open across campus or for a teacher."""
    try:
        now_utc = datetime.now(timezone.utc).isoformat()
        query = (
            supabase.table("class_sessions")
            .select("session_id", count="exact")
            .is_("closed_at", "null")
            .gt("expires_at", now_utc)
        )
        if teacher_id is not None:
            query = query.eq("teacher_id", teacher_id)
        response = query.execute()
        if response.count is not None:
            return response.count
        return len(response.data or [])
    except APIError:
        logger.exception("Could not count live class sessions via APIError")
        return 0
    except (httpx.HTTPError, Exception):
        logger.exception("Could not count live campus sessions")
        return 0


def submit_class_checkin(
    access_code,
    student_id,
    verification_method,
    verification_score,
    subject_id=None,
    latitude=None,
    longitude=None,
    location_accuracy_m=None,
):
    response = supabase.rpc(
        'submit_class_checkin',
        {
            'p_access_code': access_code,
            'p_student_id': student_id,
            'p_subject_id': subject_id,
            'p_verification_method': verification_method,
            'p_verification_score': verification_score,
            'p_latitude': latitude,
            'p_longitude': longitude,
            'p_location_accuracy_m': location_accuracy_m,
        },
    ).execute()
    if not response.data:
        raise ValueError('The check-in request was not saved.')
    return response.data[0]


def get_pending_class_checkins(teacher_id):
    try:
        response = (
            supabase.table('class_checkins')
            .select(
                '*, students(name), '
                'class_sessions!inner(subject_id, teacher_id, subjects(name, subject_code, section))'
            )
            .eq('status', 'pending')
            .eq('class_sessions.teacher_id', teacher_id)
            .order('submitted_at')
            .execute()
        )
    except APIError:
        logger.exception("Could not load pending class check-ins")
        return []
    return response.data


def review_class_checkin(checkin_id, teacher_id, approved):
    response = supabase.rpc(
        'review_class_checkin',
        {
            'p_checkin_id': checkin_id,
            'p_teacher_id': teacher_id,
            'p_approved': approved,
        },
    ).execute()
    if not response.data:
        raise ValueError('This request was already reviewed or is not in your classes.')
    return response.data[0]


def save_student_voice_profile(student_id, voice_embedding):
    response = (
        supabase.table('students')
        .update({'voice_embedding': voice_embedding})
        .eq('student_id', student_id)
        .select('*')
        .execute()
    )
    if not response.data:
        raise ValueError('Could not save the voice profile for this student.')
    return response.data[0]


def _get_owned_exam(exam_id, teacher_id):
    response = (
        supabase.table("exam_papers")
        .select(
            "exam_id, subject_id, title, max_marks, blueprint_path, "
            "blueprint_rubric, question_paper_path, marking_scheme"
        )
        .eq("exam_id", exam_id)
        .eq("teacher_id", teacher_id)
        .execute()
    )
    if not response.data:
        raise ValueError("This exam was not found in your subjects.")
    return response.data[0]


def get_enrolled_students_for_subject(subject_id, teacher_id):
    subject = (
        supabase.table("subjects")
        .select("subject_id")
        .eq("subject_id", subject_id)
        .eq("teacher_id", teacher_id)
        .execute()
    )
    if not subject.data:
        raise ValueError("This subject was not found in your classes.")
    response = (
        supabase.table("subject_students")
        .select("student_id, students(student_id, name)")
        .eq("subject_id", subject_id)
        .execute()
    )
    return [
        {
            "student_id": row["student_id"],
            "name": (row.get("students") or {}).get("name", "Student"),
        }
        for row in response.data
        if row.get("students")
    ]


def create_exam_paper(
    subject_id,
    teacher_id,
    title,
    blueprint_path,
    blueprint_rubric,
    max_marks,
    question_paper_path=None,
    marking_scheme=None,
):
    subject = (
        supabase.table("subjects")
        .select("subject_id")
        .eq("subject_id", subject_id)
        .eq("teacher_id", teacher_id)
        .execute()
    )
    if not subject.data:
        raise ValueError("This subject was not found in your classes.")
    response = (
        supabase.table("exam_papers")
        .insert({
            "subject_id": subject_id,
            "teacher_id": teacher_id,
            "title": title,
            "blueprint_path": blueprint_path,
            "blueprint_rubric": blueprint_rubric,
            "max_marks": max_marks,
            "question_paper_path": question_paper_path,
            "marking_scheme": marking_scheme or {},
        })
        .select("*")
        .execute()
    )
    return response.data[0]


def get_exam_papers_for_teacher(teacher_id):
    response = (
        supabase.table("exam_papers")
        .select("*, subjects(name, subject_code, section)")
        .eq("teacher_id", teacher_id)
        .order("created_at", desc=True)
        .execute()
    )
    return response.data


def get_available_exams_for_student(student_id):
    subjects = get_student_subjects(student_id)
    subject_ids = [
        row["subjects"]["subject_id"]
        for row in subjects
        if row.get("subjects")
    ]
    if not subject_ids:
        return []

    exams = (
        supabase.table("exam_papers")
        .select("*, subjects(name, subject_code)")
        .in_("subject_id", subject_ids)
        .order("created_at", desc=True)
        .execute()
        .data
    )
    existing_attempts = (
        supabase.table("paper_submissions")
        .select("exam_id, student_answers")
        .eq("student_id", student_id)
        .execute()
        .data
    )
    attempted_exam_ids = {
        row["exam_id"]
        for row in existing_attempts
        if row.get("student_answers") is not None
    }
    return [
        exam for exam in exams
        if exam["exam_id"] not in attempted_exam_ids
        and (exam.get("marking_scheme") or {}).get("modules")
        and exam.get("question_paper_path")
    ]


def get_student_exam_attempts(student_id):
    response = (
        supabase.table("paper_submissions")
        .select(
            "*, exam_papers!inner(title, max_marks, marking_scheme, "
            "question_paper_path, subjects(name, subject_code))"
        )
        .eq("student_id", student_id)
        .order("created_at", desc=True)
        .execute()
    )
    return [
        row for row in response.data
        if row.get("student_answers") is not None
    ]


def submit_student_exam_attempt(exam_id, student_id, answers, evaluation_result):
    from src.pipelines.exam_marking import (
        calculate_exam_result,
        target_scores_from_result,
        validate_marking_scheme,
        validate_student_answers,
    )

    exam_response = (
        supabase.table("exam_papers")
        .select("exam_id, subject_id, marking_scheme, question_paper_path")
        .eq("exam_id", exam_id)
        .execute()
    )
    if not exam_response.data:
        raise ValueError("This exam is no longer available.")
    exam = exam_response.data[0]
    if not exam.get("question_paper_path"):
        raise ValueError("This exam does not have a question paper.")
    if not (exam.get("marking_scheme") or {}).get("modules"):
        raise ValueError("This exam does not have a student marking scheme.")
    marking_scheme = exam["marking_scheme"]
    validate_marking_scheme(marking_scheme, evaluation_result.get("max_marks"))
    answers = validate_student_answers(marking_scheme, answers)
    evaluation_result = calculate_exam_result(
        marking_scheme,
        target_scores_from_result(evaluation_result),
    )

    enrollment = (
        supabase.table("subject_students")
        .select("student_id")
        .eq("subject_id", exam["subject_id"])
        .eq("student_id", student_id)
        .execute()
    )
    if not enrollment.data:
        raise ValueError("You are not enrolled in this exam's subject.")

    existing = (
        supabase.table("paper_submissions")
        .select("submission_id, student_answers")
        .eq("exam_id", exam_id)
        .eq("student_id", student_id)
        .execute()
        .data
    )
    if any(row.get("student_answers") is not None for row in existing):
        raise ValueError("You have already submitted this exam.")
    response = (
        supabase.table("paper_submissions")
        .insert({
            "exam_id": exam_id,
            "student_id": student_id,
            "sheet_path": None,
            "student_answers": answers,
            "ai_marks": evaluation_result["final_marks"],
            "evaluation_details": evaluation_result,
            "status": "evaluated",
        })
        .select("*")
        .execute()
    )
    if not response.data:
        raise ValueError("Your exam attempt could not be saved.")
    return response.data[0]


def _decode_storage_paths(value):
    from src.pipelines.paper_pipeline import decode_storage_paths

    return [str(path) for path in decode_storage_paths(value) if path]


def _get_all_storage_reference_rows(table_name, columns):
    rows = []
    page_size = 500
    offset = 0
    while True:
        page = (
            supabase.table(table_name)
            .select(columns)
            .range(offset, offset + page_size - 1)
            .execute()
            .data
        )
        rows.extend(page)
        if len(page) < page_size:
            return rows
        offset += page_size


def remove_unreferenced_exam_files(paths):
    candidates = set(paths)
    if not candidates:
        return

    exam_rows = _get_all_storage_reference_rows(
        "exam_papers",
        "blueprint_path, question_paper_path",
    )
    submission_rows = _get_all_storage_reference_rows(
        "paper_submissions",
        "sheet_path",
    )
    referenced = set()
    for row in exam_rows:
        referenced.update(_decode_storage_paths(row.get("blueprint_path")))
        referenced.update(_decode_storage_paths(row.get("question_paper_path")))
    for row in submission_rows:
        referenced.update(_decode_storage_paths(row.get("sheet_path")))

    unreferenced = sorted(candidates - referenced)
    if unreferenced:
        from src.pipelines.paper_pipeline import remove_stored_pages

        try:
            remove_stored_pages(unreferenced)
        except Exception as error:
            logger.exception("Could not remove unreferenced exam files")
            raise RuntimeError(
                "The database change succeeded, but one or more old files "
                "could not be removed from storage."
            ) from error


def update_exam_documents(
    exam_id,
    teacher_id,
    blueprint_path=None,
    blueprint_rubric=None,
    max_marks=None,
    question_paper_path=None,
    clear_question_paper=False,
    marking_scheme=None,
):
    _get_owned_exam(exam_id, teacher_id)
    updates = {}

    if blueprint_path is not None:
        if not blueprint_rubric or max_marks is None or max_marks <= 0:
            raise ValueError("A new blueprint requires a valid grading rubric and total.")
        updates.update({
            "blueprint_path": blueprint_path,
            "max_marks": max_marks,
        })
        if blueprint_rubric is not None:
            updates["blueprint_rubric"] = blueprint_rubric
    if marking_scheme is not None:
        updates["marking_scheme"] = marking_scheme

    if question_paper_path is not None:
        updates["question_paper_path"] = question_paper_path
    elif clear_question_paper:
        updates["question_paper_path"] = None

    if not updates:
        raise ValueError("Choose a document to update.")

    response = (
        supabase.table("exam_papers")
        .update(updates)
        .eq("exam_id", exam_id)
        .eq("teacher_id", teacher_id)
        .select("*")
        .execute()
    )
    if not response.data:
        raise ValueError("The exam documents could not be updated.")

    return response.data[0]


def update_exam_marking_scheme(
    exam_id,
    teacher_id,
    marking_scheme,
    total_marks,
    blueprint_rubric,
):
    from src.pipelines.exam_marking import validate_marking_scheme

    _get_owned_exam(exam_id, teacher_id)
    validate_marking_scheme(marking_scheme, total_marks)
    submissions = (
        supabase.table("paper_submissions")
        .select("submission_id")
        .eq("exam_id", exam_id)
        .execute()
        .data
    )
    if submissions:
        raise ValueError(
            "The marking scheme cannot be changed after student submissions "
            "exist, because that would reinterpret recorded scores."
        )
    response = (
        supabase.table("exam_papers")
        .update({
            "marking_scheme": marking_scheme,
            "blueprint_rubric": blueprint_rubric,
            "max_marks": total_marks,
        })
        .eq("exam_id", exam_id)
        .eq("teacher_id", teacher_id)
        .select("*")
        .execute()
    )
    if not response.data:
        raise ValueError("The exam marking scheme could not be updated.")
    return response.data[0]


def delete_exam_paper(exam_id, teacher_id):
    exam = _get_owned_exam(exam_id, teacher_id)

    submissions = (
        supabase.table("paper_submissions")
        .select("sheet_path")
        .eq("exam_id", exam_id)
        .execute()
        .data
    )

    storage_paths = set()
    for field in (
        exam.get("blueprint_path"),
        exam.get("question_paper_path"),
    ):
        storage_paths.update(_decode_storage_paths(field))
    for submission in submissions:
        storage_paths.update(
            _decode_storage_paths(submission.get("sheet_path"))
        )

    response = supabase.rpc(
        "delete_paper_exam",
        {
            "p_exam_id": exam_id,
            "p_teacher_id": teacher_id,
        },
    ).execute()
    if not response.data:
        raise ValueError("The exam could not be deleted.")

    remove_unreferenced_exam_files(storage_paths)


def insert_paper_submission(exam_id, teacher_id, student_id, sheet_path):
    exam = _get_owned_exam(exam_id, teacher_id)
    enrollment = (
        supabase.table("subject_students")
        .select("student_id")
        .eq("subject_id", exam["subject_id"])
        .eq("student_id", student_id)
        .execute()
    )
    if not enrollment.data:
        raise ValueError("The selected student is not enrolled in this subject.")
    response = (
        supabase.table("paper_submissions")
        .insert({
            "exam_id": exam_id,
            "student_id": student_id,
            "sheet_path": sheet_path,
            "status": "pending",
        })
        .select("*")
        .execute()
    )
    return response.data[0]


def update_paper_evaluation(submission_id, exam_id, teacher_id, ai_marks, details):
    exam = _get_owned_exam(exam_id, teacher_id)
    if ai_marks < 0 or ai_marks > float(exam["max_marks"]):
        raise ValueError("The AI score must be within the exam's total marks.")
    response = (
        supabase.table("paper_submissions")
        .update({
            "ai_marks": ai_marks,
            "evaluation_details": details,
            "status": "evaluated",
        })
        .eq("submission_id", submission_id)
        .eq("exam_id", exam_id)
        .eq("status", "pending")
        .select("*")
        .execute()
    )
    if not response.data:
        raise ValueError("This paper is no longer waiting for AI evaluation.")
    return response.data[0]


def get_paper_submissions_for_teacher(exam_id, teacher_id):
    _get_owned_exam(exam_id, teacher_id)
    response = (
        supabase.table("paper_submissions")
        .select("*, students(name)")
        .eq("exam_id", exam_id)
        .order("created_at", desc=True)
        .execute()
    )
    return response.data


def record_paper_evaluation_error(submission_id, exam_id, teacher_id, error):
    _get_owned_exam(exam_id, teacher_id)
    response = (
        supabase.table("paper_submissions")
        .update({"evaluation_details": {"error": str(error)}})
        .eq("submission_id", submission_id)
        .eq("exam_id", exam_id)
        .eq("status", "pending")
        .select("submission_id")
        .execute()
    )
    if not response.data:
        raise ValueError("Could not save the paper evaluation failure.")


def save_teacher_verified_marks(
    submission_id, exam_id, teacher_id, final_marks, evaluation_details
):
    exam = _get_owned_exam(exam_id, teacher_id)
    if isinstance(evaluation_details, dict) and "modules" in evaluation_details:
        from src.pipelines.exam_marking import (
            calculate_exam_result,
            target_scores_from_result,
        )

        evaluation_details = calculate_exam_result(
            exam.get("marking_scheme") or {},
            target_scores_from_result(evaluation_details),
        )
        if not math.isclose(
            float(final_marks),
            evaluation_details["final_marks"],
            abs_tol=0.01,
        ):
            raise ValueError(
                "The verified total must equal the capped module and "
                "question scores."
            )
        final_marks = evaluation_details["final_marks"]
    if final_marks < 0 or final_marks > float(exam["max_marks"]):
        raise ValueError("The verified score must be within the exam's total marks.")
    response = (
        supabase.table("paper_submissions")
        .update({
            "final_marks": final_marks,
            "evaluation_details": evaluation_details,
            "status": "verified",
            "reviewed_by": teacher_id,
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
        })
        .eq("submission_id", submission_id)
        .eq("exam_id", exam_id)
        .eq("status", "evaluated")
        .select("*")
        .execute()
    )
    if not response.data:
        raise ValueError("This paper was already reviewed or is not evaluated.")
    return response.data[0]


def get_verified_paper_results(student_id):
    response = (
        supabase.table("paper_submissions")
        .select(
            "*, exam_papers!inner(title, max_marks, marking_scheme, "
            "question_paper_path, subjects(name, subject_code))"
        )
        .eq("student_id", student_id)
        .eq("status", "verified")
        .order("reviewed_at", desc=True)
        .execute()
    )
    return response.data
