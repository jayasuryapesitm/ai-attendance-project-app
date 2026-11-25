# ai-attendance-project-app

## Mentor portal setup

Run the latest `sql/mentor_mentee.sql` in the Supabase SQL Editor. It creates a
teacher-attributed assignment-request history, migrates existing mentor
assignments safely, and keeps existing student, teacher, and attendance records.
The migration also installs the request, accept, reject, and relationship-ending
database functions and reloads the PostgREST schema cache.

The workflow is **Teacher Portal → assignment request → Mentor Portal → accept
or reject**. A teacher selects active mentor(s) and registered student(s); each
request is recorded as Pending with the teacher ID and request time. A student
cannot have another Pending or Accepted request. A rejected request remains in
history and can be requested again. An accepted relationship must be ended
before the student can be requested for another mentor.

Mentors sign in from **Mentor Portal** and can only see requests addressed to
their account. They can accept or reject each request; accepting creates the
active mentor–mentee relationship, while rejecting does not. Only accepted
students appear under **My Mentees** and in attendance views. Teachers can view
the status and rejection reason for requests they submitted. Low-attendance
email alerts are sent only to the current mentor of an accepted mentee.

The app uses the server-side `SUPABASE_KEY` for database operations. Assignment
RPC functions are restricted to `service_role`; keep this key private. After
running the migration, restart or refresh ClassLens.ai so the new API schema is
available.

Configure SMTP in Streamlit secrets for low-attendance email alerts:

```toml
SMTP_HOST = "smtp.example.com"
SMTP_PORT = "587"
SMTP_USERNAME = "smtp-user"
SMTP_PASSWORD = "smtp-password"
SMTP_FROM_EMAIL = "attendance@example.com"
SMTP_USE_TLS = "true"
```

Attendance at or above 75% does not create an alert. A strictly lower overall
attendance percentage queues one notification per student per calendar month;
SMTP failures are stored in notification history and do not block attendance.

## ClassLens.ai interface

Start the application with `streamlit run app.py`. The top navigation keeps the
Home, Student, Teacher, and Attendance Records views available, and the theme
switch is stored for the current browser session. Students can use **Live Class
Check-in** with the short-lived code from their teacher; teachers open and close
those sessions from **Live Check-in**. Camera, microphone, and location access
are requested only when the related flow is used. The live session count on the
home screen queries active sessions from the database in real time. The optional
geofence control remains illustrative; the application does not configure a real
campus boundary.
Teachers can extend an active session by five minutes, rotate its access code,
or close it to lock check-in.

## Paper evaluation

Install the packages in `requirements.txt`, set `GEMINI_API_KEY` in the
environment or `.streamlit/secrets.toml`, and run `sql/paper_evaluation.sql`
in the Supabase SQL Editor. The migration creates the exam/submission tables
and a private `exam-sheets` storage bucket. In the Teacher Portal, each exam
gets its own blueprint and question-paper files; selected exams can replace or
remove their documents without affecting another exam. Exams can also be
deleted with their submissions and unshared stored files. Map uploaded student
sheets to enrolled students, then review the AI marks before selecting
**Verify & Publish**. For new exams, configure the total, modules, questions,
sub-questions, compulsory questions, and OR groups in the teacher marking
editor. The application compares the configured marks with the blueprint and
question paper and requires confirmation before creating the exam. Each exam's
marking scheme is stored on its own exam record. Students can submit one online
attempt per exam; the scheme identifies compulsory questions and OR groups.
AI paper evaluation uses `gemini-3.5-flash-lite` by default. To override it,
set `GEMINI_MODEL` in the environment or `.streamlit/secrets.toml`; if the
configured model is unavailable, the evaluator tries supported fallbacks.
Failed evaluations stay pending; after correcting the model setting and
restarting ClassLens.ai, use **Retry AI evaluation** on the saved submission.
Students may leave sub-questions unanswered and still receive partial credit
for their other answers. Alternatives in an OR group must have equal question
marks and matching sub-question counts and marks; the module maximum counts
only the permitted choices, not every alternative. Each alternative is
evaluated independently, and the highest-scoring permitted alternatives count
toward the module total. Teachers review the hierarchical AI marks before
publishing, and
students see only verified scores and question feedback in **Exam Results**.
Stored documents are converted to JPEG page images; PostgreSQL stores storage
paths, rubric, marks, and feedback, not original file contents. The migration
is rerunnable and updates existing exam records for document lifecycle
management and online attempts.
Install dependencies and launch Streamlit with the same Python environment.
On Windows, for example:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

## Supabase setup

Before using the student portal, run `sql/students.sql` in the Supabase SQL
Editor. This creates the `public.students` table used for student profiles and
reloads the PostgREST schema cache. The app stores face and voice embeddings as
arrays of floating-point values. Use the server-side `SUPABASE_KEY` configured
in Streamlit secrets to access the table.

For FaceID sign-in or profile setup, allow camera access in the browser and
Windows privacy settings. If another app or browser tab is using the webcam,
close it or upload a clear JPG/PNG face photo instead. Captured and uploaded
photos are processed in memory for face matching and are not retained.

## Student voice attendance

Before using student voice attendance, run `sql/voice_attendance_submissions.sql`
in the Supabase SQL Editor. The application reads and writes this table using
the server-side `SUPABASE_KEY`; configure it as a Supabase service-role key in
Streamlit secrets (not the publishable/anon key) and never expose it in browser
code or commit it. In Supabase, copy a server-side secret/service-role key from
the project's API keys settings and set it as `SUPABASE_KEY` in
`.streamlit/secrets.toml`. Keep that key private; it has elevated database
access. The table and RPC functions intentionally restrict access to
`service_role` only, so rerunning the SQL migration will not resolve a
permission error caused by using a publishable/anon key.

Older voice requests remain available in **Voice Reviews**. New voice submissions
are session-bound; students explicitly consent before recording, and the
per-subject voice dialog does not collect location. In the main Live Check-in
panel, students can optionally share GPS for either verification method.
Voice fields support live microphone recording and WAV, MP3, OGG, WEBM, or M4A
uploads. Use the upload option if the browser blocks microphone access.
On Windows, install [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
with the C++ build workload before installing `requirements.txt`. Resemblyzer
depends on `webrtcvad`, which compiles a native extension. Then run
`python -m pip install -r requirements.txt` from the project root and restart
Streamlit.

## Live, trust-aware class check-in

After the base `students`, `subjects`, `teachers`, `subject_students`, and
`attendance_logs` tables exist, run `sql/class_checkin_sessions.sql` in the
Supabase SQL Editor. This migration creates expiring class sessions, check-in
records, teacher review functions, and an optional class-session reference on
attendance records. It is safe to rerun. Keep the configured Supabase key
server-side; the new tables and RPC functions are restricted to `service_role`.

In **Live Check-in**, a teacher opens a 5–60 minute session. An eight-digit code
can be rotated or the session closed at any time. The QR code opens the student
page with that code prefilled; students must still sign in and be enrolled in
the matching class. A network-accessible deployment is needed for students to
open the QR link from their devices. Teachers should close a session or open a
new one for that subject to finalize it; students without a submitted check-in
are then recorded absent, while borderline requests remain available for review.

Students explicitly consent before using face or voice matching. During
check-in, a strong face match (distance at most 0.3375) or voice match
(similarity at least 0.80) records attendance automatically. Borderline face
matches (distance above 0.3375 and at most 0.45) are sent to **Live Check-in**
teacher review; unmatched attempts are not marked present. These thresholds
are initial engineering defaults, not validated identity guarantees: evaluate
them with consented, representative data before any real-world deployment.
Face recognition rejects distances above 0.45 and also rejects a result unless
the best registered profile is at least 0.05 distance units closer than the
second-best profile. The camera flow has no liveness detection, so a photograph
may still be accepted if its face embedding passes these matching checks.
Voice verification is available as an alternative to face verification. GPS
sharing is optional, and accuracy above 200 metres is shown as a review flag,
not treated as proof of misconduct. Captured check-in photos and audio are
processed for matching and not stored by the session-check-in flow.
Initial face/voice profile consent and subsequent successful biometric sign-ins
are timestamped on the student profile. Each check-in also records its
verification method, score, and any teacher decision.

The student privacy panel can delete the profile, biometric embeddings,
enrollments, attendance records, and voice requests. Deletion is permanent.

## Deleting a subject

Run `sql/delete_teacher_subject.sql` in the Supabase SQL Editor to enable the
teacher's **Delete subject** action. This creates the required RPC function and
reloads the Supabase API schema cache. If the function is still not found,
refresh the schema cache in Supabase and wait a few seconds. The action requires confirmation and
permanently deletes the selected subject, its enrollments, attendance records,
voice submissions, class sessions, and session check-ins/reviews. The operation
runs in a single database transaction.

## Evaluating this major project

Use a consented, representative evaluation set and report false-accept and
false-reject rates separately for face and voice, match latency, borderline
review rate, and results across lighting, camera quality, face angle, and
recording conditions. Compare verification alternatives, include teacher
review outcomes, and avoid reporting a single accuracy figure without its
conditions or sample size. The included tests exercise code generation and
check-in decision boundaries; they do not certify biometric accuracy.

For crowded classroom photos, upload or capture multiple clear views from
different parts of the room. Face detection keeps more image detail than the
previous 800-pixel resize and retries with stronger upsampling when fewer faces
are detected than enrolled profiles. Attendance recognition is limited to the
selected subject's enrolled students. The review screen reports detected faces
that could not be matched; review the roster before saving and use student voice
verification in **Live Check-in** for missed students. Occlusion, faces
that are too small or turned away, poor lighting, and missing or outdated
student profiles can still prevent a match, so a single group photo cannot
guarantee perfect recognition.