-- Procurement & resources (Phase 6)
-- Apply after estimate_items.sql / planning.sql

create table if not exists public.material_requirements (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  material_code text,
  name text not null,
  category text,
  unit text,
  quantity numeric,
  work_sections text[] default '{}',
  element_types text[] default '{}',
  source_line_count integer default 0,
  status text not null default 'proposed'
    check (status in ('proposed','requested','ordered','delivered','cancelled')),
  source text default 'estimate_heuristic',
  properties jsonb default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists material_requirements_project_idx on public.material_requirements(project_id);
create index if not exists material_requirements_category_idx on public.material_requirements(project_id, category);

create table if not exists public.equipment_requirements (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  equipment_code text,
  name text not null,
  unit text default 'days',
  quantity_days integer,
  work_sections text[] default '{}',
  status text not null default 'proposed'
    check (status in ('proposed','reserved','on_site','released','cancelled')),
  source text default 'estimate_heuristic',
  properties jsonb default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists equipment_requirements_project_idx on public.equipment_requirements(project_id);

create table if not exists public.workforce_requirements (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  trade text not null,
  headcount integer,
  duration_days integer,
  person_days integer,
  work_section text,
  status text not null default 'proposed'
    check (status in ('proposed','allocated','active','complete','cancelled')),
  source text default 'estimate_heuristic',
  properties jsonb default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists workforce_requirements_project_idx on public.workforce_requirements(project_id);

alter table public.material_requirements enable row level security;
alter table public.equipment_requirements enable row level security;
alter table public.workforce_requirements enable row level security;

create policy "material_requirements_select" on public.material_requirements
  for select using (
    exists (
      select 1 from public.projects p
      join public.organization_members m on m.organization_id = p.organization_id
      where p.id = material_requirements.project_id and m.user_id = auth.uid()
    )
  );
create policy "material_requirements_insert" on public.material_requirements
  for insert with check (
    exists (
      select 1 from public.projects p
      join public.organization_members m on m.organization_id = p.organization_id
      where p.id = material_requirements.project_id and m.user_id = auth.uid()
    )
  );
create policy "material_requirements_update" on public.material_requirements
  for update using (
    exists (
      select 1 from public.projects p
      join public.organization_members m on m.organization_id = p.organization_id
      where p.id = material_requirements.project_id and m.user_id = auth.uid()
    )
  );

create policy "equipment_requirements_select" on public.equipment_requirements
  for select using (
    exists (
      select 1 from public.projects p
      join public.organization_members m on m.organization_id = p.organization_id
      where p.id = equipment_requirements.project_id and m.user_id = auth.uid()
    )
  );
create policy "equipment_requirements_insert" on public.equipment_requirements
  for insert with check (
    exists (
      select 1 from public.projects p
      join public.organization_members m on m.organization_id = p.organization_id
      where p.id = equipment_requirements.project_id and m.user_id = auth.uid()
    )
  );
create policy "equipment_requirements_update" on public.equipment_requirements
  for update using (
    exists (
      select 1 from public.projects p
      join public.organization_members m on m.organization_id = p.organization_id
      where p.id = equipment_requirements.project_id and m.user_id = auth.uid()
    )
  );

create policy "workforce_requirements_select" on public.workforce_requirements
  for select using (
    exists (
      select 1 from public.projects p
      join public.organization_members m on m.organization_id = p.organization_id
      where p.id = workforce_requirements.project_id and m.user_id = auth.uid()
    )
  );
create policy "workforce_requirements_insert" on public.workforce_requirements
  for insert with check (
    exists (
      select 1 from public.projects p
      join public.organization_members m on m.organization_id = p.organization_id
      where p.id = workforce_requirements.project_id and m.user_id = auth.uid()
    )
  );
create policy "workforce_requirements_update" on public.workforce_requirements
  for update using (
    exists (
      select 1 from public.projects p
      join public.organization_members m on m.organization_id = p.organization_id
      where p.id = workforce_requirements.project_id and m.user_id = auth.uid()
    )
  );

create or replace function public.set_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists material_requirements_updated_at on public.material_requirements;
create trigger material_requirements_updated_at
  before update on public.material_requirements
  for each row execute function public.set_updated_at();

drop trigger if exists equipment_requirements_updated_at on public.equipment_requirements;
create trigger equipment_requirements_updated_at
  before update on public.equipment_requirements
  for each row execute function public.set_updated_at();

drop trigger if exists workforce_requirements_updated_at on public.workforce_requirements;
create trigger workforce_requirements_updated_at
  before update on public.workforce_requirements
  for each row execute function public.set_updated_at();
