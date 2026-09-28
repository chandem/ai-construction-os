-- Contract packages & items (Phase 4 Step 17)
-- Apply after tender_packages.sql

create table if not exists public.contract_packages (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  tender_package_id uuid references public.tender_packages(id) on delete set null,
  contract_code text,
  title text not null,
  work_section text,
  contractor_name text,
  status text not null default 'draft'
    check (status in ('draft','under_review','executed','active','completed','terminated','cancelled')),
  currency text not null default 'USD',
  contract_value numeric,
  baseline_total numeric,
  line_count integer default 0,
  source text default 'tender_award',
  notes text,
  properties jsonb default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists contract_packages_project_idx on public.contract_packages(project_id);
create index if not exists contract_packages_status_idx on public.contract_packages(project_id, status);
create index if not exists contract_packages_tender_idx on public.contract_packages(tender_package_id);

create table if not exists public.contract_items (
  id uuid primary key default gen_random_uuid(),
  contract_package_id uuid not null references public.contract_packages(id) on delete cascade,
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
  tender_item_id uuid,
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

create index if not exists contract_items_package_idx on public.contract_items(contract_package_id);
create index if not exists contract_items_project_idx on public.contract_items(project_id);

alter table public.contract_packages enable row level security;
alter table public.contract_items enable row level security;

create policy "contract_packages_select" on public.contract_packages
  for select using (
    exists (
      select 1 from public.projects p
      join public.organization_members m on m.organization_id = p.organization_id
      where p.id = contract_packages.project_id and m.user_id = auth.uid()
    )
  );

create policy "contract_packages_insert" on public.contract_packages
  for insert with check (
    exists (
      select 1 from public.projects p
      join public.organization_members m on m.organization_id = p.organization_id
      where p.id = contract_packages.project_id and m.user_id = auth.uid()
    )
  );

create policy "contract_packages_update" on public.contract_packages
  for update using (
    exists (
      select 1 from public.projects p
      join public.organization_members m on m.organization_id = p.organization_id
      where p.id = contract_packages.project_id and m.user_id = auth.uid()
    )
  );

create policy "contract_items_select" on public.contract_items
  for select using (
    exists (
      select 1 from public.projects p
      join public.organization_members m on m.organization_id = p.organization_id
      where p.id = contract_items.project_id and m.user_id = auth.uid()
    )
  );

create policy "contract_items_insert" on public.contract_items
  for insert with check (
    exists (
      select 1 from public.projects p
      join public.organization_members m on m.organization_id = p.organization_id
      where p.id = contract_items.project_id and m.user_id = auth.uid()
    )
  );

create policy "contract_items_update" on public.contract_items
  for update using (
    exists (
      select 1 from public.projects p
      join public.organization_members m on m.organization_id = p.organization_id
      where p.id = contract_items.project_id and m.user_id = auth.uid()
    )
  );

create or replace function public.set_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists contract_packages_updated_at on public.contract_packages;
create trigger contract_packages_updated_at
  before update on public.contract_packages
  for each row execute function public.set_updated_at();

drop trigger if exists contract_items_updated_at on public.contract_items;
create trigger contract_items_updated_at
  before update on public.contract_items
  for each row execute function public.set_updated_at();
