-- Hardening: ops queue jobs + cost events (Phase 13)

create table if not exists public.ops_queue_jobs (
  id uuid primary key default gen_random_uuid(),
  project_id uuid references public.projects(id) on delete cascade,
  kind text not null default 'other',
  status text not null default 'queued'
    check (status in ('queued','running','succeeded','failed','cancelled','dead')),
  priority integer default 100,
  attempt integer default 0,
  max_attempts integer default 3,
  payload jsonb default '{}'::jsonb,
  last_error text,
  available_at timestamptz,
  started_at timestamptz,
  finished_at timestamptz,
  source text default 'hardening_ops',
  properties jsonb default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists ops_queue_jobs_status_idx on public.ops_queue_jobs(status, available_at);
create index if not exists ops_queue_jobs_project_idx on public.ops_queue_jobs(project_id);
create index if not exists ops_queue_jobs_kind_idx on public.ops_queue_jobs(kind);

create table if not exists public.ops_cost_events (
  id uuid primary key default gen_random_uuid(),
  project_id uuid references public.projects(id) on delete cascade,
  category text not null,
  amount_usd numeric not null default 0,
  units integer default 1,
  reference text,
  notes text,
  recorded_at timestamptz not null default now(),
  source text default 'hardening_ops',
  properties jsonb default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists ops_cost_events_project_idx on public.ops_cost_events(project_id);
create index if not exists ops_cost_events_category_idx on public.ops_cost_events(category);

alter table public.ops_queue_jobs enable row level security;
alter table public.ops_cost_events enable row level security;

-- Project-scoped rows: members only; null project_id = platform (service role)
create policy "ops_queue_jobs_select" on public.ops_queue_jobs
  for select using (
    project_id is null
    or exists (
      select 1 from public.projects p
      join public.organization_members m on m.organization_id = p.organization_id
      where p.id = ops_queue_jobs.project_id and m.user_id = auth.uid()
    )
  );
create policy "ops_queue_jobs_insert" on public.ops_queue_jobs
  for insert with check (
    project_id is null
    or exists (
      select 1 from public.projects p
      join public.organization_members m on m.organization_id = p.organization_id
      where p.id = ops_queue_jobs.project_id and m.user_id = auth.uid()
    )
  );
create policy "ops_queue_jobs_update" on public.ops_queue_jobs
  for update using (
    project_id is null
    or exists (
      select 1 from public.projects p
      join public.organization_members m on m.organization_id = p.organization_id
      where p.id = ops_queue_jobs.project_id and m.user_id = auth.uid()
    )
  );

create policy "ops_cost_events_select" on public.ops_cost_events
  for select using (
    project_id is null
    or exists (
      select 1 from public.projects p
      join public.organization_members m on m.organization_id = p.organization_id
      where p.id = ops_cost_events.project_id and m.user_id = auth.uid()
    )
  );
create policy "ops_cost_events_insert" on public.ops_cost_events
  for insert with check (
    project_id is null
    or exists (
      select 1 from public.projects p
      join public.organization_members m on m.organization_id = p.organization_id
      where p.id = ops_cost_events.project_id and m.user_id = auth.uid()
    )
  );

create or replace function public.set_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists ops_queue_jobs_updated_at on public.ops_queue_jobs;
create trigger ops_queue_jobs_updated_at
  before update on public.ops_queue_jobs
  for each row execute function public.set_updated_at();

drop trigger if exists ops_cost_events_updated_at on public.ops_cost_events;
create trigger ops_cost_events_updated_at
  before update on public.ops_cost_events
  for each row execute function public.set_updated_at();
