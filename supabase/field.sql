-- Field operations: site diary + progress (Phase 7)
-- Apply after planning.sql (schedule_activities optional FK)

create table if not exists public.site_diary_entries (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  entry_date date not null default current_date,
  weather text,
  work_summary text,
  workforce_on_site integer,
  equipment_on_site text,
  issues text,
  safety_notes text,
  work_section text,
  schedule_activity_id uuid,
  status text not null default 'draft'
    check (status in ('draft','submitted','reviewed','archived')),
  source text default 'field_ops',
  created_by text,
  properties jsonb default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists site_diary_project_idx on public.site_diary_entries(project_id);
create index if not exists site_diary_date_idx on public.site_diary_entries(project_id, entry_date desc);

create table if not exists public.progress_updates (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  schedule_activity_id uuid,
  activity_code text,
  activity_name text,
  work_section text,
  report_date date not null default current_date,
  percent_complete numeric,
  previous_percent numeric,
  delta_percent numeric,
  note text,
  status text not null default 'recorded'
    check (status in ('recorded','verified','disputed','cancelled')),
  source text default 'field_ops',
  recorded_by text,
  properties jsonb default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists progress_updates_project_idx on public.progress_updates(project_id);
create index if not exists progress_updates_activity_idx on public.progress_updates(schedule_activity_id);
create index if not exists progress_updates_date_idx on public.progress_updates(project_id, report_date desc);

alter table public.site_diary_entries enable row level security;
alter table public.progress_updates enable row level security;

create policy "site_diary_select" on public.site_diary_entries
  for select using (
    exists (
      select 1 from public.projects p
      join public.organization_members m on m.organization_id = p.organization_id
      where p.id = site_diary_entries.project_id and m.user_id = auth.uid()
    )
  );
create policy "site_diary_insert" on public.site_diary_entries
  for insert with check (
    exists (
      select 1 from public.projects p
      join public.organization_members m on m.organization_id = p.organization_id
      where p.id = site_diary_entries.project_id and m.user_id = auth.uid()
    )
  );
create policy "site_diary_update" on public.site_diary_entries
  for update using (
    exists (
      select 1 from public.projects p
      join public.organization_members m on m.organization_id = p.organization_id
      where p.id = site_diary_entries.project_id and m.user_id = auth.uid()
    )
  );

create policy "progress_updates_select" on public.progress_updates
  for select using (
    exists (
      select 1 from public.projects p
      join public.organization_members m on m.organization_id = p.organization_id
      where p.id = progress_updates.project_id and m.user_id = auth.uid()
    )
  );
create policy "progress_updates_insert" on public.progress_updates
  for insert with check (
    exists (
      select 1 from public.projects p
      join public.organization_members m on m.organization_id = p.organization_id
      where p.id = progress_updates.project_id and m.user_id = auth.uid()
    )
  );
create policy "progress_updates_update" on public.progress_updates
  for update using (
    exists (
      select 1 from public.projects p
      join public.organization_members m on m.organization_id = p.organization_id
      where p.id = progress_updates.project_id and m.user_id = auth.uid()
    )
  );

create or replace function public.set_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists site_diary_updated_at on public.site_diary_entries;
create trigger site_diary_updated_at
  before update on public.site_diary_entries
  for each row execute function public.set_updated_at();

drop trigger if exists progress_updates_updated_at on public.progress_updates;
create trigger progress_updates_updated_at
  before update on public.progress_updates
  for each row execute function public.set_updated_at();
