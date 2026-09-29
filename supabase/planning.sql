-- Planning foundation: WBS nodes + schedule activities (Phase 5)
-- Apply after estimate_items.sql (optional link to commercial chain)

create table if not exists public.wbs_nodes (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  parent_id uuid references public.wbs_nodes(id) on delete set null,
  code text,
  name text not null,
  level integer not null default 0,
  work_section text,
  sort_order integer default 0,
  status text not null default 'proposed'
    check (status in ('proposed','approved','active','complete','cancelled')),
  source text default 'estimate_work_section',
  baseline_amount numeric,
  line_count integer default 0,
  properties jsonb default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists wbs_nodes_project_idx on public.wbs_nodes(project_id);
create index if not exists wbs_nodes_parent_idx on public.wbs_nodes(parent_id);
create index if not exists wbs_nodes_level_idx on public.wbs_nodes(project_id, level);

create table if not exists public.schedule_activities (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  wbs_node_id uuid references public.wbs_nodes(id) on delete set null,
  code text,
  name text not null,
  work_section text,
  sort_order integer default 0,
  status text not null default 'not_started'
    check (status in ('not_started','in_progress','complete','delayed','on_hold','cancelled')),
  planned_start date,
  planned_finish date,
  duration_days integer,
  percent_complete numeric default 0,
  predecessor_ids uuid[] default '{}',
  source text default 'wbs_heuristic',
  baseline_amount numeric,
  notes text,
  properties jsonb default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists schedule_activities_project_idx on public.schedule_activities(project_id);
create index if not exists schedule_activities_wbs_idx on public.schedule_activities(wbs_node_id);
create index if not exists schedule_activities_status_idx on public.schedule_activities(project_id, status);

alter table public.wbs_nodes enable row level security;
alter table public.schedule_activities enable row level security;

create policy "wbs_nodes_select" on public.wbs_nodes
  for select using (
    exists (
      select 1 from public.projects p
      join public.organization_members m on m.organization_id = p.organization_id
      where p.id = wbs_nodes.project_id and m.user_id = auth.uid()
    )
  );

create policy "wbs_nodes_insert" on public.wbs_nodes
  for insert with check (
    exists (
      select 1 from public.projects p
      join public.organization_members m on m.organization_id = p.organization_id
      where p.id = wbs_nodes.project_id and m.user_id = auth.uid()
    )
  );

create policy "wbs_nodes_update" on public.wbs_nodes
  for update using (
    exists (
      select 1 from public.projects p
      join public.organization_members m on m.organization_id = p.organization_id
      where p.id = wbs_nodes.project_id and m.user_id = auth.uid()
    )
  );

create policy "schedule_activities_select" on public.schedule_activities
  for select using (
    exists (
      select 1 from public.projects p
      join public.organization_members m on m.organization_id = p.organization_id
      where p.id = schedule_activities.project_id and m.user_id = auth.uid()
    )
  );

create policy "schedule_activities_insert" on public.schedule_activities
  for insert with check (
    exists (
      select 1 from public.projects p
      join public.organization_members m on m.organization_id = p.organization_id
      where p.id = schedule_activities.project_id and m.user_id = auth.uid()
    )
  );

create policy "schedule_activities_update" on public.schedule_activities
  for update using (
    exists (
      select 1 from public.projects p
      join public.organization_members m on m.organization_id = p.organization_id
      where p.id = schedule_activities.project_id and m.user_id = auth.uid()
    )
  );

create or replace function public.set_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists wbs_nodes_updated_at on public.wbs_nodes;
create trigger wbs_nodes_updated_at
  before update on public.wbs_nodes
  for each row execute function public.set_updated_at();

drop trigger if exists schedule_activities_updated_at on public.schedule_activities;
create trigger schedule_activities_updated_at
  before update on public.schedule_activities
  for each row execute function public.set_updated_at();
