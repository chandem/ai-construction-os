-- Quality & safety: inspections, NCRs, incidents (Phase 8)

create table if not exists public.inspections (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  title text not null,
  inspection_type text default 'workmanship',
  work_section text,
  location text,
  inspector text,
  result text default 'pending'
    check (result in ('pass','fail','conditional','pending')),
  findings text,
  schedule_activity_id uuid,
  inspection_date date default current_date,
  status text not null default 'planned'
    check (status in ('planned','in_progress','completed','cancelled')),
  source text default 'quality_ops',
  properties jsonb default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists inspections_project_idx on public.inspections(project_id);
create index if not exists inspections_result_idx on public.inspections(project_id, result);

create table if not exists public.ncrs (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  ncr_code text,
  title text not null,
  description text,
  severity text default 'minor'
    check (severity in ('minor','major','critical')),
  work_section text,
  location text,
  inspection_id uuid,
  raised_by text,
  corrective_action text,
  status text not null default 'open'
    check (status in ('open','under_review','corrective_action','closed','cancelled')),
  raised_date date default current_date,
  source text default 'quality_ops',
  properties jsonb default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists ncrs_project_idx on public.ncrs(project_id);
create index if not exists ncrs_status_idx on public.ncrs(project_id, status);

create table if not exists public.incidents (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  incident_code text,
  title text not null,
  incident_type text default 'near_miss',
  severity text default 'low'
    check (severity in ('low','medium','high','critical')),
  description text,
  location text,
  work_section text,
  reported_by text,
  persons_involved integer,
  status text not null default 'reported'
    check (status in ('reported','investigating','actions_open','closed','cancelled')),
  incident_date date default current_date,
  source text default 'quality_ops',
  properties jsonb default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists incidents_project_idx on public.incidents(project_id);
create index if not exists incidents_status_idx on public.incidents(project_id, status);

alter table public.inspections enable row level security;
alter table public.ncrs enable row level security;
alter table public.incidents enable row level security;

create policy "inspections_select" on public.inspections
  for select using (
    exists (
      select 1 from public.projects p
      join public.organization_members m on m.organization_id = p.organization_id
      where p.id = inspections.project_id and m.user_id = auth.uid()
    )
  );
create policy "inspections_insert" on public.inspections
  for insert with check (
    exists (
      select 1 from public.projects p
      join public.organization_members m on m.organization_id = p.organization_id
      where p.id = inspections.project_id and m.user_id = auth.uid()
    )
  );
create policy "inspections_update" on public.inspections
  for update using (
    exists (
      select 1 from public.projects p
      join public.organization_members m on m.organization_id = p.organization_id
      where p.id = inspections.project_id and m.user_id = auth.uid()
    )
  );

create policy "ncrs_select" on public.ncrs
  for select using (
    exists (
      select 1 from public.projects p
      join public.organization_members m on m.organization_id = p.organization_id
      where p.id = ncrs.project_id and m.user_id = auth.uid()
    )
  );
create policy "ncrs_insert" on public.ncrs
  for insert with check (
    exists (
      select 1 from public.projects p
      join public.organization_members m on m.organization_id = p.organization_id
      where p.id = ncrs.project_id and m.user_id = auth.uid()
    )
  );
create policy "ncrs_update" on public.ncrs
  for update using (
    exists (
      select 1 from public.projects p
      join public.organization_members m on m.organization_id = p.organization_id
      where p.id = ncrs.project_id and m.user_id = auth.uid()
    )
  );

create policy "incidents_select" on public.incidents
  for select using (
    exists (
      select 1 from public.projects p
      join public.organization_members m on m.organization_id = p.organization_id
      where p.id = incidents.project_id and m.user_id = auth.uid()
    )
  );
create policy "incidents_insert" on public.incidents
  for insert with check (
    exists (
      select 1 from public.projects p
      join public.organization_members m on m.organization_id = p.organization_id
      where p.id = incidents.project_id and m.user_id = auth.uid()
    )
  );
create policy "incidents_update" on public.incidents
  for update using (
    exists (
      select 1 from public.projects p
      join public.organization_members m on m.organization_id = p.organization_id
      where p.id = incidents.project_id and m.user_id = auth.uid()
    )
  );

create or replace function public.set_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists inspections_updated_at on public.inspections;
create trigger inspections_updated_at
  before update on public.inspections
  for each row execute function public.set_updated_at();

drop trigger if exists ncrs_updated_at on public.ncrs;
create trigger ncrs_updated_at
  before update on public.ncrs
  for each row execute function public.set_updated_at();

drop trigger if exists incidents_updated_at on public.incidents;
create trigger incidents_updated_at
  before update on public.incidents
  for each row execute function public.set_updated_at();
