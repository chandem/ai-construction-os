-- Step 14 / BOQ linkage: proposed Bill of Quantities items from quantity takeoff.
-- Apply in Supabase SQL editor after engineering_elements.sql.
-- These are proposed lines for professional review, not certified tender quantities.

create table if not exists public.boq_items (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  item_code text,
  work_section text,
  description text,
  element_type text,
  quantity numeric,
  unit text,
  item_count integer not null default 0,
  source_element_ids jsonb not null default '[]'::jsonb,
  source_identifiers jsonb not null default '[]'::jsonb,
  source text not null default 'quantity_takeoff',
  status text not null default 'proposed',
  notes text,
  properties jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists boq_items_project_idx on public.boq_items (project_id, work_section);
create index if not exists boq_items_element_type_idx on public.boq_items (project_id, element_type);

alter table public.boq_items enable row level security;

drop policy if exists "boq items select members" on public.boq_items;
create policy "boq items select members"
  on public.boq_items for select to authenticated
  using (exists (
    select 1 from public.projects p
    join public.organization_members m on m.organization_id = p.organization_id
    where p.id = boq_items.project_id and m.user_id = (select auth.uid())
  ));

drop policy if exists "boq items insert members" on public.boq_items;
create policy "boq items insert members"
  on public.boq_items for insert to authenticated
  with check (exists (
    select 1 from public.projects p
    join public.organization_members m on m.organization_id = p.organization_id
    where p.id = boq_items.project_id and m.user_id = (select auth.uid())
  ));

drop policy if exists "boq items update members" on public.boq_items;
create policy "boq items update members"
  on public.boq_items for update to authenticated
  using (exists (
    select 1 from public.projects p
    join public.organization_members m on m.organization_id = p.organization_id
    where p.id = boq_items.project_id and m.user_id = (select auth.uid())
  ))
  with check (exists (
    select 1 from public.projects p
    join public.organization_members m on m.organization_id = p.organization_id
    where p.id = boq_items.project_id and m.user_id = (select auth.uid())
  ));

drop policy if exists "boq items delete members" on public.boq_items;
create policy "boq items delete members"
  on public.boq_items for delete to authenticated
  using (exists (
    select 1 from public.projects p
    join public.organization_members m on m.organization_id = p.organization_id
    where p.id = boq_items.project_id and m.user_id = (select auth.uid())
  ));

grant select, insert, update, delete on public.boq_items to authenticated;
