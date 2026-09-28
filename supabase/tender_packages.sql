-- Tender packages & items (Phase 4)
-- Apply in Supabase SQL editor after estimate_items.sql

-- Package header
create table if not exists public.tender_packages (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  package_code text,
  title text not null,
  work_section text,
  status text not null default 'draft'
    check (status in ('draft','ready','issued','received','evaluated','awarded','cancelled')),
  currency text not null default 'USD',
  baseline_total numeric,
  line_count integer default 0,
  priced_lines integer default 0,
  source text default 'estimate_baseline',
  notes text,
  properties jsonb default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists tender_packages_project_idx on public.tender_packages(project_id);
create index if not exists tender_packages_status_idx on public.tender_packages(project_id, status);

-- Line items inside a package
create table if not exists public.tender_items (
  id uuid primary key default gen_random_uuid(),
  tender_package_id uuid not null references public.tender_packages(id) on delete cascade,
  project_id uuid not null references public.projects(id) on delete cascade,
  line_no integer,
  item_code text,
  work_section text,
  description text,
  element_type text,
  quantity numeric,
  unit text,
  unit_rate numeric,
  amount numeric,
  currency text default 'USD',
  estimate_item_id uuid,
  boq_item_id uuid,
  source_element_ids uuid[] default '{}',
  source_identifiers text[] default '{}',
  status text not null default 'included',
  notes text,
  properties jsonb default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists tender_items_package_idx on public.tender_items(tender_package_id);
create index if not exists tender_items_project_idx on public.tender_items(project_id);

-- RLS
alter table public.tender_packages enable row level security;
alter table public.tender_items enable row level security;

-- Members of the project org can read/write packages
create policy "tender_packages_select" on public.tender_packages
  for select using (
    exists (
      select 1 from public.projects p
      join public.organization_members m on m.organization_id = p.organization_id
      where p.id = tender_packages.project_id and m.user_id = auth.uid()
    )
  );

create policy "tender_packages_insert" on public.tender_packages
  for insert with check (
    exists (
      select 1 from public.projects p
      join public.organization_members m on m.organization_id = p.organization_id
      where p.id = tender_packages.project_id and m.user_id = auth.uid()
    )
  );

create policy "tender_packages_update" on public.tender_packages
  for update using (
    exists (
      select 1 from public.projects p
      join public.organization_members m on m.organization_id = p.organization_id
      where p.id = tender_packages.project_id and m.user_id = auth.uid()
    )
  );

create policy "tender_items_select" on public.tender_items
  for select using (
    exists (
      select 1 from public.projects p
      join public.organization_members m on m.organization_id = p.organization_id
      where p.id = tender_items.project_id and m.user_id = auth.uid()
    )
  );

create policy "tender_items_insert" on public.tender_items
  for insert with check (
    exists (
      select 1 from public.projects p
      join public.organization_members m on m.organization_id = p.organization_id
      where p.id = tender_items.project_id and m.user_id = auth.uid()
    )
  );

create policy "tender_items_update" on public.tender_items
  for update using (
    exists (
      select 1 from public.projects p
      join public.organization_members m on m.organization_id = p.organization_id
      where p.id = tender_items.project_id and m.user_id = auth.uid()
    )
  );

-- updated_at trigger (reuse if already defined)
create or replace function public.set_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists tender_packages_updated_at on public.tender_packages;
create trigger tender_packages_updated_at
  before update on public.tender_packages
  for each row execute function public.set_updated_at();

drop trigger if exists tender_items_updated_at on public.tender_items;
create trigger tender_items_updated_at
  before update on public.tender_items
  for each row execute function public.set_updated_at();
