-- Integrations: connections + sync jobs (Phase 12)

create table if not exists public.integration_connections (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  connector_type text not null default 'other',
  name text not null,
  direction text default 'import'
    check (direction in ('import','export','bidirectional')),
  external_ref text,
  status text not null default 'draft'
    check (status in ('draft','connected','error','disabled','archived')),
  config jsonb default '{}'::jsonb,
  last_sync_at timestamptz,
  last_sync_status text default 'idle',
  source text default 'integrations_ops',
  properties jsonb default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists integration_connections_project_idx
  on public.integration_connections(project_id);
create index if not exists integration_connections_type_idx
  on public.integration_connections(project_id, connector_type);

create table if not exists public.integration_sync_jobs (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  connection_id uuid,
  connector_type text,
  target text default 'other',
  direction text default 'import',
  status text not null default 'queued'
    check (status in ('idle','queued','running','succeeded','failed','cancelled')),
  message text,
  started_at timestamptz,
  finished_at timestamptz,
  records_processed integer default 0,
  source text default 'integrations_ops',
  properties jsonb default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists integration_sync_jobs_project_idx
  on public.integration_sync_jobs(project_id);
create index if not exists integration_sync_jobs_connection_idx
  on public.integration_sync_jobs(connection_id);
create index if not exists integration_sync_jobs_status_idx
  on public.integration_sync_jobs(project_id, status);

alter table public.integration_connections enable row level security;
alter table public.integration_sync_jobs enable row level security;

create policy "integration_connections_select" on public.integration_connections
  for select using (
    exists (
      select 1 from public.projects p
      join public.organization_members m on m.organization_id = p.organization_id
      where p.id = integration_connections.project_id and m.user_id = auth.uid()
    )
  );
create policy "integration_connections_insert" on public.integration_connections
  for insert with check (
    exists (
      select 1 from public.projects p
      join public.organization_members m on m.organization_id = p.organization_id
      where p.id = integration_connections.project_id and m.user_id = auth.uid()
    )
  );
create policy "integration_connections_update" on public.integration_connections
  for update using (
    exists (
      select 1 from public.projects p
      join public.organization_members m on m.organization_id = p.organization_id
      where p.id = integration_connections.project_id and m.user_id = auth.uid()
    )
  );

create policy "integration_sync_jobs_select" on public.integration_sync_jobs
  for select using (
    exists (
      select 1 from public.projects p
      join public.organization_members m on m.organization_id = p.organization_id
      where p.id = integration_sync_jobs.project_id and m.user_id = auth.uid()
    )
  );
create policy "integration_sync_jobs_insert" on public.integration_sync_jobs
  for insert with check (
    exists (
      select 1 from public.projects p
      join public.organization_members m on m.organization_id = p.organization_id
      where p.id = integration_sync_jobs.project_id and m.user_id = auth.uid()
    )
  );
create policy "integration_sync_jobs_update" on public.integration_sync_jobs
  for update using (
    exists (
      select 1 from public.projects p
      join public.organization_members m on m.organization_id = p.organization_id
      where p.id = integration_sync_jobs.project_id and m.user_id = auth.uid()
    )
  );

create or replace function public.set_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists integration_connections_updated_at on public.integration_connections;
create trigger integration_connections_updated_at
  before update on public.integration_connections
  for each row execute function public.set_updated_at();

drop trigger if exists integration_sync_jobs_updated_at on public.integration_sync_jobs;
create trigger integration_sync_jobs_updated_at
  before update on public.integration_sync_jobs
  for each row execute function public.set_updated_at();
