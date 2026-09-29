-- GIS: locations + infrastructure assets (Phase 9)

create table if not exists public.gis_locations (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  name text not null,
  location_type text default 'site',
  latitude double precision,
  longitude double precision,
  address text,
  description text,
  parent_location_id uuid,
  status text not null default 'active'
    check (status in ('proposed','active','inactive','archived')),
  source text default 'gis_ops',
  properties jsonb default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists gis_locations_project_idx on public.gis_locations(project_id);

create table if not exists public.infrastructure_assets (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  asset_code text,
  name text not null,
  asset_type text default 'building',
  geometry_type text default 'point',
  location_id uuid,
  latitude double precision,
  longitude double precision,
  work_section text,
  design_asset_id uuid,
  description text,
  status text not null default 'planned'
    check (status in ('planned','under_construction','existing','demolished','archived')),
  source text default 'gis_ops',
  properties jsonb default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists infrastructure_assets_project_idx on public.infrastructure_assets(project_id);
create index if not exists infrastructure_assets_location_idx on public.infrastructure_assets(location_id);
create index if not exists infrastructure_assets_type_idx on public.infrastructure_assets(project_id, asset_type);

alter table public.gis_locations enable row level security;
alter table public.infrastructure_assets enable row level security;

create policy "gis_locations_select" on public.gis_locations
  for select using (
    exists (
      select 1 from public.projects p
      join public.organization_members m on m.organization_id = p.organization_id
      where p.id = gis_locations.project_id and m.user_id = auth.uid()
    )
  );
create policy "gis_locations_insert" on public.gis_locations
  for insert with check (
    exists (
      select 1 from public.projects p
      join public.organization_members m on m.organization_id = p.organization_id
      where p.id = gis_locations.project_id and m.user_id = auth.uid()
    )
  );
create policy "gis_locations_update" on public.gis_locations
  for update using (
    exists (
      select 1 from public.projects p
      join public.organization_members m on m.organization_id = p.organization_id
      where p.id = gis_locations.project_id and m.user_id = auth.uid()
    )
  );

create policy "infrastructure_assets_select" on public.infrastructure_assets
  for select using (
    exists (
      select 1 from public.projects p
      join public.organization_members m on m.organization_id = p.organization_id
      where p.id = infrastructure_assets.project_id and m.user_id = auth.uid()
    )
  );
create policy "infrastructure_assets_insert" on public.infrastructure_assets
  for insert with check (
    exists (
      select 1 from public.projects p
      join public.organization_members m on m.organization_id = p.organization_id
      where p.id = infrastructure_assets.project_id and m.user_id = auth.uid()
    )
  );
create policy "infrastructure_assets_update" on public.infrastructure_assets
  for update using (
    exists (
      select 1 from public.projects p
      join public.organization_members m on m.organization_id = p.organization_id
      where p.id = infrastructure_assets.project_id and m.user_id = auth.uid()
    )
  );

create or replace function public.set_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists gis_locations_updated_at on public.gis_locations;
create trigger gis_locations_updated_at
  before update on public.gis_locations
  for each row execute function public.set_updated_at();

drop trigger if exists infrastructure_assets_updated_at on public.infrastructure_assets;
create trigger infrastructure_assets_updated_at
  before update on public.infrastructure_assets
  for each row execute function public.set_updated_at();
