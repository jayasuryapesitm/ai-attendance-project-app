create table if not exists public.student_face_templates (
    id bigserial primary key,
    student_id bigint not null references public.students(student_id) on delete cascade,
    pose_label text not null
        check (pose_label in ('front', 'left', 'right', 'left_profile', 'right_profile')),
    embedding jsonb not null,
    model_version text not null default 'dlib-128-v1',
    image_quality_score numeric(6, 3),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create unique index if not exists student_face_templates_one_pose_idx
    on public.student_face_templates (student_id, pose_label);
create index if not exists student_face_templates_model_idx
    on public.student_face_templates (model_version);

insert into public.student_face_templates (
    student_id,
    pose_label,
    embedding,
    model_version,
    created_at,
    updated_at
)
select
    student_id,
    'front',
    to_jsonb(face_embedding),
    'dlib-128-v1',
    coalesce(face_consent_at, now()),
    coalesce(face_consent_at, now())
from public.students
where face_embedding is not null
on conflict (student_id, pose_label) do nothing;

alter table public.student_face_templates enable row level security;
grant all on public.student_face_templates to service_role;
grant usage, select on sequence public.student_face_templates_id_seq to service_role;
grant select, insert, update, delete on public.student_face_templates to service_role;

notify pgrst, 'reload schema';
