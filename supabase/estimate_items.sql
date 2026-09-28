-- Estimate linkage: proposed cost lines from BOQ with provisional unit rates.
-- Apply in Supabase SQL editor after boq_items.sql.
-- Amounts are design-to-cost exploration only — not tender estimates.

create table if not exists public.estimate_items (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  boq_item_id uuid references public.boq_items(id) on delete set null,
  item_code text,
  work_section text,
  description text,
  element_type text,
  quantity numeric,
  unit text,
  unit_rate numeric,
  amount numeric,
  currency text not null default 'USD',
  rate_source text not null default 'provisional_default',
  item_count integer,
  source_element_ids jsonb not null default '[]'::jsonb,
  source_identifiers jsonb not null default '[]'::jsonb,
  source text not null default 'boq',
  status text not null default 'proposed',
  notes text,
  properties jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists estimate_items_project_idx on public.estimate_items (project_id, work_section);
create index if not exists estimate_items_boq_idx on public.estimate_items (boq_item_id);
create index if not exists estimate_items_element_type_idx on public.estimate_items (project_id, element_type);

alter table public.estimate_items enable row level security;

drop policy if exists "estimate items select members" on public.estimate_items;
create policy "estimate items select members"
  on public.estimate_items for select to authenticated
  using (exists (
    select 1 from public.projects p
    join public.organization_members m on m.organization_id = p.organization_id
    where p.id = estimate_items.project_id and m.user_id = (select auth.uid())
  ));

drop policy if exists "estimate items insert members" on public.estimate_items;
create policy "estimate items insert members"
  on public.estimate_items for insert to authenticated
  with check (exists (
    select 1 from public.projects p
    join public.organization_members m on m.organization_id = p.organization_id
    where p.id = estimate_items.project_id and m.user_id = (select auth.uid())
  ));

drop policy if exists "estimate items update members" on public.estimate_items;
create policy "estimate items update members"
  on public.estimate_items for update to authenticated
  using (exists (
    select 1 from public.projects p
    join public.organization_members m on m.organization_id = p.organization_id
    where p.id = estimate_items.project_id and m.user_id = (select auth.uid())
  ))
  with check (exists (
    select 1 from public.projects p
    join public.organization_members m on m.organization_id = p.organization_id
    where p.id = estimate_items.project_id and m.user_id = (select auth.uid())
  ));

drop policy if exists "estimate items delete members" on public.estimate_items;
create policy "estimate items delete members"
  on public.estimate_items for delete to authenticated
  using (exists (
    select 1 from public.projects p
    join public.organization_members m on m.organization_id = p.organization_id
    where p.id = estimate_items.project_id and m.user_id = (select auth.uid())
  ));

grant select, insert, update, delete on public.estimate_items to authenticated;
