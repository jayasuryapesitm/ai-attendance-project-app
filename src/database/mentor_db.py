import re
import smtplib
from email.message import EmailMessage
from datetime import datetime, timezone

import bcrypt

from src.database.config import get_smtp_config, supabase


EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def calculate_attendance(logs):
    held = len(logs)
    attended = sum(bool(log.get("is_present")) for log in logs)
    percentage = (100.0 * attended / held) if held else 0.0
    return held, attended, percentage


def validate_mentor_email(email):
    email = (email or "").strip().lower()
    if not EMAIL_PATTERN.fullmatch(email):
        raise ValueError("Enter a valid email address.")
    return email


def list_mentors(search="", department="", branch=""):
    query = supabase.table("mentors").select("*").order("full_name")
    if department:
        query = query.eq("department", department)
    if branch:
        query = query.eq("branch", branch)
    rows = query.execute().data
    if search:
        needle = search.lower()
        rows = [
            row for row in rows
            if needle in str(row.get("full_name", "")).lower()
            or needle in str(row.get("email", "")).lower()
        ]
    for row in rows:
        count = (
            supabase.table("mentor_mentees")
            .select("id", count="exact")
            .eq("mentor_id", row["id"])
            .eq("is_active", True)
            .execute()
        )
        row["mentee_count"] = count.count or 0
    return rows


def create_mentor(
    full_name,
    email,
    phone=None,
    department=None,
    branch=None,
    designation=None,
    password=None,
):
    email = validate_mentor_email(email)
    if not full_name.strip():
        raise ValueError("Full name is required.")
    existing = supabase.table("mentors").select("id").eq("email", email).limit(1).execute()
    if existing.data:
        raise ValueError("A mentor with this email address already exists.")
    payload = {
        "full_name": full_name.strip(),
        "email": email,
        "phone": (phone or "").strip() or None,
        "department": (department or "").strip() or None,
        "branch": (branch or "").strip() or None,
        "designation": (designation or "").strip() or None,
        "is_active": True,
    }
    if password:
        payload["password_hash"] = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    result = supabase.table("mentors").insert(payload).execute()
    return result.data[0] if result.data else None


def update_mentor(mentor_id, updates):
    if "email" in updates:
        updates["email"] = validate_mentor_email(updates["email"])
    if "password" in updates:
        password = updates.pop("password")
        if password:
            updates["password_hash"] = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    return supabase.table("mentors").update(updates).eq("id", mentor_id).execute().data


def deactivate_mentor(mentor_id):
    active_mentees = (
        supabase.table("mentor_mentees")
        .select("id", count="exact")
        .eq("mentor_id", mentor_id)
        .eq("is_active", True)
        .execute()
    )
    pending_requests = (
        supabase.table("mentor_assignment_requests")
        .select("id", count="exact")
        .eq("mentor_id", mentor_id)
        .eq("status", "pending")
        .execute()
    )
    if active_mentees.count or pending_requests.count:
        raise ValueError(
            "Resolve pending requests and end active mentee relationships before deactivating this mentor."
        )
    return supabase.table("mentors").update({"is_active": False}).eq("id", mentor_id).execute().data


def list_students(search=""):
    response = supabase.table("students").select("*").order("name").execute()
    rows = response.data
    if search:
        needle = search.lower()
        rows = [
            row for row in rows
            if needle in str(row.get("name", "")).lower()
            or needle in str(row.get("student_id", "")).lower()
            or needle in str(row.get("email", "")).lower()
        ]
    assignments = (
        supabase.table("mentor_assignment_requests")
        .select("student_id, mentor_id, status, mentors(full_name,email)")
        .in_("status", ["pending", "accepted"])
        .execute()
        .data
    )
    assignment_by_student = {row["student_id"]: row for row in assignments}
    for row in rows:
        row["_assignment"] = assignment_by_student.get(row["student_id"])
    return rows


def request_students_for_mentor(student_ids, mentor_id, teacher_id):
    if not student_ids:
        raise ValueError("Select at least one student to assign.")
    if not teacher_id:
        raise ValueError("The signed-in teacher could not be verified.")
    response = supabase.rpc(
        "create_mentor_assignment_requests",
        {
            "p_student_ids": list(dict.fromkeys(student_ids)),
            "p_mentor_id": mentor_id,
            "p_teacher_id": teacher_id,
        },
    ).execute()
    return int(response.data or 0)


def get_pending_assignment_requests(mentor_id):
    rows = (
        supabase.table("mentor_assignment_requests")
        .select(
            "id,student_id,mentor_id,assigned_by_teacher_id,status,requested_at,"
            "students(student_id,name,email,academic_year,branch,department),"
            "teachers(name)"
        )
        .eq("mentor_id", mentor_id)
        .eq("status", "pending")
        .order("requested_at")
        .execute()
        .data
    )
    for row in rows:
        row["student"] = row.pop("students") or {}
        row["teacher"] = row.pop("teachers") or {}
    return rows


def get_teacher_assignment_requests(teacher_id):
    if not teacher_id:
        raise ValueError("The signed-in teacher could not be verified.")
    rows = (
        supabase.table("mentor_assignment_requests")
        .select(
            "id,student_id,mentor_id,assigned_by_teacher_id,status,requested_at,"
            "responded_at,rejection_reason,"
            "students(student_id,name,email),mentors(full_name,email)"
        )
        .eq("assigned_by_teacher_id", teacher_id)
        .order("requested_at", desc=True)
        .execute()
        .data
    )
    for row in rows:
        row["student"] = row.pop("students") or {}
        row["mentor"] = row.pop("mentors") or {}
    return rows


def accept_mentor_assignment_request(mentor_id, request_id):
    if not mentor_id or not request_id:
        raise ValueError("A mentor and assignment request are required.")
    response = supabase.rpc(
        "accept_mentor_assignment_request",
        {
            "p_mentor_id": mentor_id,
            "p_request_id": request_id,
        },
    ).execute()
    return int(response.data or 0)


def reject_mentor_assignment_request(mentor_id, request_id, reason=None):
    if not mentor_id or not request_id:
        raise ValueError("A mentor and assignment request are required.")
    response = supabase.rpc(
        "reject_mentor_assignment_request",
        {
            "p_mentor_id": mentor_id,
            "p_request_id": request_id,
            "p_rejection_reason": (reason or "").strip() or None,
        },
    ).execute()
    return int(response.data or 0)


def end_mentor_assignment(teacher_id, student_id, mentor_id):
    if not teacher_id or not student_id or not mentor_id:
        raise ValueError("A teacher, student, and mentor are required.")
    response = supabase.rpc(
        "end_mentor_assignment",
        {
            "p_teacher_id": teacher_id,
            "p_student_id": student_id,
            "p_mentor_id": mentor_id,
        },
    ).execute()
    return int(response.data or 0)


def update_student_academic(student_id, academic_year, semester, branch, department, section):
    return supabase.table("students").update({
        "academic_year": academic_year or None,
        "semester": semester or None,
        "branch": branch or None,
        "department": department or None,
        "section": section or None,
    }).eq("student_id", student_id).execute().data


def mentor_login(email, password):
    email = validate_mentor_email(email)
    rows = supabase.table("mentors").select("*").eq("email", email).eq("is_active", True).limit(1).execute().data
    if not rows:
        return None
    mentor = rows[0]
    password_hash = mentor.get("password_hash")
    if not password_hash or not bcrypt.checkpw(password.encode(), password_hash.encode()):
        return None
    return mentor


def get_assigned_mentees(mentor_id):
    assignments = (
        supabase.table("mentor_mentees")
        .select("student_id, accepted_at, students(*)")
        .eq("mentor_id", mentor_id)
        .eq("is_active", True)
        .eq("status", "accepted")
        .execute()
        .data
    )
    mentees = []
    for assignment in assignments:
        student = assignment.get("students") or {}
        if not student:
            continue
        student["_accepted_at"] = assignment.get("accepted_at")
        logs = (
            supabase.table("attendance_logs")
            .select("is_present,timestamp,subject_id")
            .eq("student_id", student["student_id"])
            .execute()
            .data
        )
        held, attended, percentage = calculate_attendance(logs)
        student["_held"] = held
        student["_attended"] = attended
        student["_percentage"] = percentage
        mentees.append(student)
    return mentees


def get_mentee_profile(student_id, mentor_id=None):
    query = supabase.table("students").select("*").eq("student_id", student_id).limit(1)
    students = query.execute().data
    if not students:
        return None, []
    if mentor_id is not None:
        active = (
            supabase.table("mentor_mentees")
            .select("id")
            .eq("student_id", student_id)
            .eq("mentor_id", mentor_id)
            .eq("is_active", True)
            .eq("status", "accepted")
            .limit(1)
            .execute()
            .data
        )
        if not active:
            raise PermissionError("This student is not assigned to the logged-in mentor.")
    logs = (
        supabase.table("attendance_logs")
        .select("*, subjects(*)")
        .eq("student_id", student_id)
        .execute()
        .data
    )
    return students[0], logs


def get_notification_history(mentor_id=None, status="All"):
    query = (
        supabase.table("mentor_attendance_notifications")
        .select("*, students(student_id,name), mentors(full_name)")
        .order("created_at", desc=True)
    )
    if mentor_id is not None:
        query = query.eq("mentor_id", mentor_id)
    if status != "All":
        query = query.eq("notification_status", status.lower())
    return query.execute().data


def _get_current_accepted_mentor_email(student_id, mentor_id):
    rows = (
        supabase.table("mentor_mentees")
        .select("id, mentors!inner(email,is_active)")
        .eq("student_id", student_id)
        .eq("mentor_id", mentor_id)
        .eq("is_active", True)
        .eq("status", "accepted")
        .eq("mentors.is_active", True)
        .limit(1)
        .execute()
        .data
    )
    if not rows:
        return None
    return (rows[0].get("mentors") or {}).get("email")


def send_pending_mentor_notifications(limit=50):
    rows = (
        supabase.table("mentor_attendance_notifications")
        .select("*")
        .eq("notification_status", "pending")
        .order("created_at")
        .limit(limit)
        .execute()
        .data
    )
    if not rows:
        return 0, None
    config = get_smtp_config()
    if not config["host"] or not config["from_email"]:
        return 0, "SMTP_HOST and SMTP_FROM_EMAIL must be configured."
    sent = 0
    for row in rows:
        try:
            if not row.get("mentor_id"):
                supabase.table("mentor_attendance_notifications").update({
                    "notification_status": "failed",
                    "error_message": "No mentor is recorded for this notification.",
                }).eq("id", row["id"]).execute()
                continue
            recipient_email = _get_current_accepted_mentor_email(
                row["student_id"],
                row["mentor_id"],
            )
            if not recipient_email:
                supabase.table("mentor_attendance_notifications").update({
                    "notification_status": "failed",
                    "error_message": (
                        "No active accepted mentor assignment with a mentor email exists."
                    ),
                }).eq("id", row["id"]).execute()
                continue
            student = (
                supabase.table("students")
                .select("name,academic_year,branch")
                .eq("student_id", row["student_id"])
                .limit(1)
                .execute()
                .data
            )
            student = student[0] if student else {}
            message = EmailMessage()
            message["Subject"] = "ClassLens.ai – Low Attendance Alert for Your Mentee"
            message["From"] = config["from_email"]
            message["To"] = recipient_email
            message.set_content(
                "Dear Mentor,\n\n"
                "This is an automated notification from ClassLens.ai. One of your assigned "
                "mentees has an attendance percentage below the required 75%.\n\n"
                f"Student Name: {student.get('name', 'Unknown')}\n"
                f"Student ID: {row['student_id']}\n"
                f"Academic Year: {student.get('academic_year', 'Not set')}\n"
                f"Branch: {student.get('branch', 'Not set')}\n"
                f"Current Attendance: {row['attendance_percentage']}%\n"
                "Required Attendance: 75%\n\n"
                "Please contact the student and provide the necessary academic guidance.\n"
                "You can log in to the ClassLens.ai Mentor Portal to view the student's "
                "detailed attendance report.\n\nRegards,\nClassLens.ai Attendance Management System"
            )
            with smtplib.SMTP(config["host"], config["port"], timeout=20) as smtp:
                if config["use_tls"]:
                    smtp.starttls()
                if config["username"]:
                    smtp.login(config["username"], config["password"])
                smtp.send_message(message)
            supabase.table("mentor_attendance_notifications").update({
                "notification_status": "successful",
                "sent_at": "now",
            }).eq("id", row["id"]).execute()
            sent += 1
        except Exception as error:
            supabase.table("mentor_attendance_notifications").update({
                "notification_status": "failed",
                "error_message": str(error)[:1000],
            }).eq("id", row["id"]).execute()
    return sent, None
