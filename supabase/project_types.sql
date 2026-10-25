-- Project type foundation: classify projects across construction domains.
-- Safe to run more than once. Existing projects default to 'other'.

alter table public.projects
  add column if not exists project_type text not null default 'other';

update public.projects
set project_type = 'other'
where project_type is null or btrim(project_type) = '';

do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conname = 'projects_project_type_check'
      and conrelid = 'public.projects'::regclass
  ) then
    alter table public.projects
      add constraint projects_project_type_check
      check (project_type in ('road', 'building', 'bridge', 'water', 'utilities', 'industrial', 'other'));
  end if;
end $$;

comment on column public.projects.project_type is
  'Construction domain used to select relevant project workflows and AI guidance.';
