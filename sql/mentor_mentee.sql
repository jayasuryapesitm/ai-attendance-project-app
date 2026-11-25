-- ClassLens.ai Mentor-Mentee management
-- Safe to rerun. Existing student, teacher and attendance records are preserved.

create table if not exists public.mentors (
  id bigint generated always as identity primary key,
  mentor_code text unique not null,
  full_name text not null,
  email text unique not null,
  phone text,
  department text,
  branch text,
  designation text,
  password_hash text,
  is_active boolean not null default true,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.mentor_mentees (
  id bigint generated always as identity primary key,
  mentor_id bigint not null references public.mentors(id) on delete restrict,
  student_id bigint not null references public.students(student_id) on delete cascade,
  assigned_at timestamptz not null default timezone('utc', now()),
  accepted_at timestamptz,
  assignment_request_id bigint,
  is_active boolean not null default true,
  status text not null default 'pending',
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

alter table public.mentor_mentees
  add column if not exists status text,
  add column if not exists accepted_at timestamptz,
  add column if not exists assignment_request_id bigint;

update public.mentor_mentees
set status = 'accepted'
where status is null;

alter table public.mentor_mentees
  alter column status set default 'pending',
  alter column status set not null;

do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conname = 'mentor_mentees_status_check'
      and conrelid = 'public.mentor_mentees'::regclass
  ) then
    alter table public.mentor_mentees
      add constraint mentor_mentees_status_check
      check (status in ('pending', 'accepted'));
  end if;
end $$;

create unique index if not exists mentor_mentees_one_active_per_student
  on public.mentor_mentees(student_id)
  where is_active;

create unique index if not exists mentor_mentees_no_duplicate_pair
  on public.mentor_mentees(mentor_id, student_id)
  where is_active;

create table if not exists public.mentor_attendance_notifications (
  id bigint generated always as identity primary key,
  mentor_id bigint references public.mentors(id) on delete set null,
  student_id bigint not null references public.students(student_id) on delete cascade,
  attendance_percentage numeric(7,3) not null,
  reporting_period text not null,
  recipient_email text,
  notification_status text not null default 'pending'
    check (notification_status in ('pending', 'successful', 'failed')),
  email_subject text,
  sent_at timestamptz,
  error_message text,
  created_at timestamptz not null default timezone('utc', now()),
  unique (student_id, reporting_period)
);

alter table public.mentor_attendance_notifications
  drop constraint if exists mentor_attendance_notifications_student_id_reporting_period_key;
create unique index if not exists mentor_attendance_notifications_student_mentor_period_idx
  on public.mentor_attendance_notifications(student_id, mentor_id, reporting_period);

create index if not exists mentor_attendance_notifications_mentor_idx
  on public.mentor_attendance_notifications(mentor_id, created_at desc);
create index if not exists mentor_attendance_notifications_status_idx
  on public.mentor_attendance_notifications(notification_status);

alter table public.mentors enable row level security;
alter table public.mentor_mentees enable row level security;
alter table public.mentor_attendance_notifications enable row level security;
revoke all on public.mentors from public, anon, authenticated;
revoke all on public.mentor_mentees from public, anon, authenticated;
revoke all on public.mentor_attendance_notifications from public, anon, authenticated;
grant select, insert, update, delete on public.mentors to service_role;
grant select, insert, update, delete on public.mentor_mentees to service_role;
grant select, insert, update, delete
  on public.mentor_attendance_notifications to service_role;
grant usage, select on sequence public.mentors_id_seq to service_role;
grant usage, select on sequence public.mentor_mentees_id_seq to service_role;
grant usage, select
  on sequence public.mentor_attendance_notifications_id_seq to service_role;

drop function if exists public.assign_students_to_mentor(bigint[], bigint);
drop function if exists public.accept_mentor_students(bigint, bigint[]);
drop function if exists public.end_mentor_assignment(bigint, bigint);

create or replace function public.generate_mentor_code()
returns trigger language plpgsql as $$
begin
  if new.mentor_code is null or btrim(new.mentor_code) = '' then
    new.mentor_code := 'MENTOR-' || upper(substr(md5(random()::text || clock_timestamp()::text), 1, 8));
  end if;
  new.updated_at := timezone('utc', now());
  new.email := lower(btrim(new.email));
  return new;
end $$;

drop trigger if exists mentors_generate_code on public.mentors;
create trigger mentors_generate_code
before insert or update on public.mentors
for each row execute function public.generate_mentor_code();

alter table public.students
  add column if not exists email text,
  add column if not exists academic_year text,
  add column if not exists semester text,
  add column if not exists branch text,
  add column if not exists department text,
  add column if not exists section text,
  add column if not exists account_status text not null default 'Active';

create table if not exists public.mentor_assignment_requests (
  id bigint generated always as identity primary key,
  student_id bigint not null references public.students(student_id) on delete cascade,
  mentor_id bigint not null references public.mentors(id) on delete restrict,
  assigned_by_teacher_id bigint references public.teachers(teacher_id) on delete set null,
  status text not null default 'pending'
    check (status in ('pending', 'accepted', 'rejected', 'cancelled')),
  requested_at timestamptz not null default timezone('utc', now()),
  responded_at timestamptz,
  rejection_reason text,
  legacy_mentor_mentee_id bigint unique
    references public.mentor_mentees(id) on delete set null,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create unique index if not exists mentor_assignment_requests_one_active_per_student
  on public.mentor_assignment_requests(student_id)
  where status in ('pending', 'accepted');
create index if not exists mentor_assignment_requests_mentor_status_idx
  on public.mentor_assignment_requests(mentor_id, status, requested_at desc);
create index if not exists mentor_assignment_requests_teacher_status_idx
  on public.mentor_assignment_requests(assigned_by_teacher_id, status, requested_at desc);

do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conname = 'mentor_mentees_assignment_request_fk'
      and conrelid = 'public.mentor_mentees'::regclass
  ) then
    alter table public.mentor_mentees
      add constraint mentor_mentees_assignment_request_fk
      foreign key (assignment_request_id)
      references public.mentor_assignment_requests(id)
      on delete set null;
  end if;
end $$;

create unique index if not exists mentor_mentees_assignment_request_idx
  on public.mentor_mentees(assignment_request_id)
  where assignment_request_id is not null;

insert into public.mentor_assignment_requests (
  student_id, mentor_id, status, requested_at, responded_at,
  legacy_mentor_mentee_id
)
select
  mm.student_id,
  mm.mentor_id,
  case
    when mm.is_active then mm.status
    else 'cancelled'
  end,
  mm.assigned_at,
  case
    when mm.is_active and mm.status = 'pending' then null
    else coalesce(mm.updated_at, mm.assigned_at)
  end,
  mm.id
from public.mentor_mentees mm
on conflict (legacy_mentor_mentee_id) do nothing;

update public.mentor_mentees mm
set assignment_request_id = requests.id
from public.mentor_assignment_requests requests
where requests.legacy_mentor_mentee_id = mm.id
  and mm.assignment_request_id is null;

update public.mentor_mentees
set is_active = false,
    updated_at = timezone('utc', now())
where is_active
  and status = 'pending';

update public.mentor_mentees
set accepted_at = coalesce(accepted_at, assigned_at)
where is_active
  and status = 'accepted';

alter table public.mentor_assignment_requests enable row level security;
revoke all on public.mentor_assignment_requests from public, anon, authenticated;
grant select, insert, update, delete on public.mentor_assignment_requests to service_role;
grant usage, select on sequence public.mentor_assignment_requests_id_seq to service_role;

create or replace function public.create_mentor_assignment_requests(
  p_student_ids bigint[],
  p_mentor_id bigint,
  p_teacher_id bigint
)
returns integer
language plpgsql
security definer
set search_path = public as $$
declare
  v_student_id bigint;
  v_requested_count integer;
  v_existing_count integer;
  v_created_count integer := 0;
begin
  if p_student_ids is null or cardinality(p_student_ids) = 0 then
    raise exception 'Select at least one student to assign.';
  end if;
  if exists (
    select 1 from unnest(p_student_ids) as requested(student_id)
    where requested.student_id is null
  ) then
    raise exception 'The student selection is invalid.';
  end if;
  if not exists (
    select 1 from public.teachers where teacher_id = p_teacher_id
  ) then
    raise exception 'The requesting teacher account could not be verified.';
  end if;
  if not exists (
    select 1 from public.mentors where id = p_mentor_id and is_active
  ) then
    raise exception 'The selected mentor is not active.';
  end if;

  select count(distinct requested.student_id)
  into v_requested_count
  from unnest(p_student_ids) as requested(student_id);
  if v_requested_count <> cardinality(p_student_ids) then
    raise exception 'The student selection contains duplicates.';
  end if;

  select count(*)
  into v_existing_count
  from public.students
  where student_id = any(p_student_ids);
  if v_requested_count <> v_existing_count then
    raise exception 'One or more selected students no longer exist.';
  end if;

  foreach v_student_id in array p_student_ids loop
    if exists (
      select 1
      from public.mentor_assignment_requests
      where student_id = v_student_id
        and status in ('pending', 'accepted')
    ) then
      raise exception
        'Student % already has a pending or accepted mentor assignment.',
        v_student_id;
    end if;

    insert into public.mentor_assignment_requests (
      student_id, mentor_id, assigned_by_teacher_id
    ) values (
      v_student_id, p_mentor_id, p_teacher_id
    );
    v_created_count := v_created_count + 1;
  end loop;

  return v_created_count;
exception
  when unique_violation then
    raise exception
      'A pending or accepted mentor assignment already exists for one of the selected students.';
end $$;

create or replace function public.accept_mentor_assignment_request(
  p_request_id bigint,
  p_mentor_id bigint
)
returns integer
language plpgsql
security definer
set search_path = public as $$
declare
  v_request public.mentor_assignment_requests%rowtype;
  v_total integer;
  v_present integer;
  v_percentage numeric(7,3);
  v_period text;
  v_mentor_email text;
begin
  if not exists (
    select 1 from public.mentors where id = p_mentor_id and is_active
  ) then
    raise exception 'The mentor account is not active.';
  end if;

  select *
  into v_request
  from public.mentor_assignment_requests
  where id = p_request_id
    and mentor_id = p_mentor_id
  for update;

  if not found then
    raise exception 'This assignment request does not belong to this mentor.';
  end if;
  if v_request.status <> 'pending' then
    raise exception 'Only pending assignment requests can be accepted.';
  end if;

  update public.mentor_assignment_requests
  set status = 'accepted',
      responded_at = timezone('utc', now()),
      updated_at = timezone('utc', now())
  where id = v_request.id
    and status = 'pending';

  update public.mentor_mentees
  set mentor_id = v_request.mentor_id,
      student_id = v_request.student_id,
      assigned_at = v_request.requested_at,
      accepted_at = timezone('utc', now()),
      is_active = true,
      status = 'accepted',
      updated_at = timezone('utc', now())
  where assignment_request_id = v_request.id;

  if not found then
    insert into public.mentor_mentees (
      mentor_id, student_id, assigned_at, accepted_at,
      assignment_request_id, is_active, status
    ) values (
      v_request.mentor_id, v_request.student_id, v_request.requested_at,
      timezone('utc', now()), v_request.id, true, 'accepted'
    );
  end if;

  select count(*),
         count(*) filter (where coalesce(is_present, false))
  into v_total, v_present
  from public.attendance_logs
  where student_id = v_request.student_id;

  if v_total > 0 then
    v_percentage := round((100.0 * v_present / v_total)::numeric, 3);
    if v_percentage < 75 then
      select email
      into v_mentor_email
      from public.mentors
      where id = v_request.mentor_id
        and is_active;
      v_period := to_char(timezone('utc', now()), 'YYYY-MM');

      insert into public.mentor_attendance_notifications (
        mentor_id, student_id, attendance_percentage, reporting_period,
        recipient_email, notification_status, email_subject
      ) values (
        v_request.mentor_id, v_request.student_id, v_percentage, v_period,
        v_mentor_email, 'pending',
        'ClassLens.ai - Low Attendance Alert for Your Mentee'
      )
      on conflict (student_id, mentor_id, reporting_period) do nothing;
    end if;
  end if;

  return 1;
end $$;

create or replace function public.reject_mentor_assignment_request(
  p_request_id bigint,
  p_mentor_id bigint,
  p_rejection_reason text default null
)
returns integer
language plpgsql
security definer
set search_path = public as $$
begin
  update public.mentor_assignment_requests
  set status = 'rejected',
      responded_at = timezone('utc', now()),
      rejection_reason = nullif(btrim(p_rejection_reason), ''),
      updated_at = timezone('utc', now())
  where id = p_request_id
    and mentor_id = p_mentor_id
    and status = 'pending';

  if not found then
    if not exists (
      select 1 from public.mentor_assignment_requests
      where id = p_request_id and mentor_id = p_mentor_id
    ) then
      raise exception 'This assignment request does not belong to this mentor.';
    end if;
    raise exception 'Only pending assignment requests can be rejected.';
  end if;

  return 1;
end $$;

create or replace function public.end_mentor_assignment(
  p_student_id bigint,
  p_mentor_id bigint,
  p_teacher_id bigint
)
returns integer
language plpgsql
security definer
set search_path = public as $$
declare
  v_request_id bigint;
begin
  select id
  into v_request_id
  from public.mentor_assignment_requests
  where student_id = p_student_id
    and mentor_id = p_mentor_id
    and assigned_by_teacher_id = p_teacher_id
    and status = 'accepted'
  for update;

  if not found then
    raise exception 'No accepted assignment request owned by this teacher was found.';
  end if;

  update public.mentor_mentees
  set is_active = false,
      updated_at = timezone('utc', now())
  where student_id = p_student_id
    and mentor_id = p_mentor_id
    and assignment_request_id = v_request_id
    and is_active
    and status = 'accepted';

  if not found then
    raise exception 'No active accepted mentee relationship was found.';
  end if;

  update public.mentor_assignment_requests
  set status = 'cancelled',
      responded_at = timezone('utc', now()),
      updated_at = timezone('utc', now())
  where id = v_request_id
    and status = 'accepted';

  return 1;
end $$;

revoke all on function public.create_mentor_assignment_requests(bigint[], bigint, bigint)
  from public, anon, authenticated;
revoke all on function public.accept_mentor_assignment_request(bigint, bigint)
  from public, anon, authenticated;
revoke all on function public.reject_mentor_assignment_request(bigint, bigint, text)
  from public, anon, authenticated;
revoke all on function public.end_mentor_assignment(bigint, bigint, bigint)
  from public, anon, authenticated;
grant execute on function public.create_mentor_assignment_requests(bigint[], bigint, bigint)
  to service_role;
grant execute on function public.accept_mentor_assignment_request(bigint, bigint)
  to service_role;
grant execute on function public.reject_mentor_assignment_request(bigint, bigint, text)
  to service_role;
grant execute on function public.end_mentor_assignment(bigint, bigint, bigint)
  to service_role;

create or replace function public.queue_mentor_attendance_alert()
returns trigger language plpgsql security definer
set search_path = public as $$
declare
  v_mentor record;
  v_total integer;
  v_present integer;
  v_percentage numeric(7,3);
  v_period text;
begin
  select m.*
  into v_mentor
  from public.mentor_mentees mm
  join public.mentors m on m.id = mm.mentor_id
  where mm.student_id = new.student_id
    and mm.is_active
    and mm.status = 'accepted'
    and m.is_active
  limit 1;

  if v_mentor.id is null then
    return new;
  end if;

  select count(*),
         count(*) filter (where coalesce(is_present, false))
  into v_total, v_present
  from public.attendance_logs
  where student_id = new.student_id;

  v_percentage := case when v_total = 0 then 0
                       else round((100.0 * v_present / v_total)::numeric, 3)
                  end;
  v_period := to_char(timezone('utc', now()), 'YYYY-MM');

  if v_percentage < 75 then
    insert into public.mentor_attendance_notifications (
      mentor_id, student_id, attendance_percentage, reporting_period,
      recipient_email, notification_status, email_subject
    ) values (
      v_mentor.id, new.student_id, v_percentage, v_period,
      v_mentor.email, 'pending',
      'ClassLens.ai - Low Attendance Alert for Your Mentee'
    )
    on conflict (student_id, mentor_id, reporting_period) do nothing;
  end if;

  return new;
end $$;

drop trigger if exists attendance_queue_mentor_alert on public.attendance_logs;
create trigger attendance_queue_mentor_alert
after insert or update of is_present on public.attendance_logs
for each row execute function public.queue_mentor_attendance_alert();

-- Reload Supabase's PostgREST metadata so the new tables are available to the app.
notify pgrst, 'reload schema';
notify pgrst, 'reload config';
