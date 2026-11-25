create table if not exists public.exam_papers (
    exam_id bigserial primary key,
    subject_id bigint not null references public.subjects(subject_id) on delete cascade,
    teacher_id bigint not null references public.teachers(teacher_id) on delete cascade,
    title text not null check (length(trim(title)) > 0),
    blueprint_path text not null,
    blueprint_rubric jsonb not null,
    max_marks numeric(8, 2) not null check (max_marks > 0),
    created_at timestamptz not null default now()
);

alter table public.exam_papers
    add column if not exists question_paper_path text;

alter table public.exam_papers
    alter column blueprint_path drop not null;

alter table public.exam_papers
    add column if not exists marking_scheme jsonb not null
    default '{"modules": [], "alternative_policy": "highest_scoring"}'::jsonb;

create table if not exists public.paper_submissions (
    submission_id bigserial primary key,
    exam_id bigint not null references public.exam_papers(exam_id) on delete cascade,
    student_id bigint not null references public.students(student_id) on delete cascade,
    sheet_path text not null,
    ai_marks numeric(8, 2),
    final_marks numeric(8, 2),
    evaluation_details jsonb not null default '[]'::jsonb,
    status text not null default 'pending'
        check (status in ('pending', 'evaluated', 'verified')),
    reviewed_by bigint references public.teachers(teacher_id) on delete set null,
    reviewed_at timestamptz,
    created_at timestamptz not null default now()
);

alter table public.paper_submissions
    alter column sheet_path drop not null;

alter table public.paper_submissions
    add column if not exists student_answers jsonb;

create unique index if not exists paper_submissions_one_online_attempt_idx
    on public.paper_submissions (exam_id, student_id)
    where student_answers is not null;

create or replace function public.enforce_one_paper_submission_per_student()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
    perform 1
    from public.exam_papers
    where exam_id = new.exam_id
    for update;

    if not found then
        raise exception 'The exam does not exist.';
    end if;

    if exists (
        select 1
        from public.paper_submissions
        where exam_id = new.exam_id
          and student_id = new.student_id
    ) then
        raise exception 'This student already has a submission for this exam.';
    end if;

    return new;
end;
$$;

drop trigger if exists paper_submissions_one_per_student
    on public.paper_submissions;
create trigger paper_submissions_one_per_student
before insert on public.paper_submissions
for each row
execute function public.enforce_one_paper_submission_per_student();

create index if not exists exam_papers_teacher_subject_idx
    on public.exam_papers (teacher_id, subject_id, created_at desc);
create index if not exists paper_submissions_exam_status_idx
    on public.paper_submissions (exam_id, status, created_at desc);
create index if not exists paper_submissions_student_status_idx
    on public.paper_submissions (student_id, status);

alter table public.exam_papers enable row level security;
alter table public.paper_submissions enable row level security;
grant all on public.exam_papers, public.paper_submissions to service_role;
grant usage, select on sequence public.exam_papers_exam_id_seq to service_role;
grant usage, select on sequence public.paper_submissions_submission_id_seq to service_role;

create or replace function public.delete_paper_exam(
    p_exam_id bigint,
    p_teacher_id bigint
)
returns boolean
language plpgsql
security invoker
set search_path = ''
as $$
begin
    perform 1
    from public.exam_papers
    where exam_id = p_exam_id
      and teacher_id = p_teacher_id
    for update;

    if not found then
        raise exception 'This exam does not belong to the signed-in teacher.';
    end if;

    delete from public.exam_papers
    where exam_id = p_exam_id
      and teacher_id = p_teacher_id;

    if not found then
        raise exception 'The exam could not be deleted.';
    end if;

    return true;
end;
$$;

revoke all on function public.delete_paper_exam(bigint, bigint) from public;
grant execute on function public.delete_paper_exam(bigint, bigint) to service_role;
grant delete on public.paper_submissions, public.exam_papers to service_role;

notify pgrst, 'reload schema';

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
    'exam-sheets',
    'exam-sheets',
    false,
    30000000,
    array['image/jpeg']
)
on conflict (id) do update
set public = false,
    file_size_limit = excluded.file_size_limit,
    allowed_mime_types = excluded.allowed_mime_types;
