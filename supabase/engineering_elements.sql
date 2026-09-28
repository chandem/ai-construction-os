-- Step 13: Engineering elements as first-class project data.
-- Apply in Supabase SQL editor if the table does not already exist.

create table if not exists public.engineering_elements (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  design_asset_id uuid references public.design_assets(id) on delete set null,
  document_id uuid references public.documents(id) on delete set null,
  visual_analysis_id uuid references public.design_visual_analyses(id) on delete set null,
  element_type text not null default 'other',
  name text,
  identifier text,
  discipline text,
  level text,
  location_description text,
  quantity numeric,
  unit text,
  dimensions jsonb not null default '{}'::jsonb,
  materials jsonb not null default '[]'::jsonb,
  properties jsonb not null default '{}'::jsonb,
  geometry jsonb,
  source text not null default 'ai_extraction',
  evidence text,
  source_page integer,
  confidence numeric,
  status text not null default 'proposed',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists engineering_elements_project_idx on public.engineering_elements (project_id, element_type);
create index if not exists engineering_elements_asset_idx on public.engineering_elements (design_asset_id);
create index if not exists engineering_elements_document_idx on public.engineering_elements (document_id);
create index if not exists engineering_elements_visual_idx on public.engineering_elements (visual_analysis_id);

alter table public.engineering_elements enable row level security;

drop policy if exists "engineering elements select members" on public.engineering_elements;
create policy "engineering elements select members"
  on public.engineering_elements for select to authenticated
  using (exists (
    select 1 from public.projects p
    join public.organization_members m on m.organization_id = p.organization_id
    where p.id = engineering_elements.project_id and m.user_id = (select auth.uid())
  ));

drop policy if exists "engineering elements insert members" on public.engineering_elements;
create policy "engineering elements insert members"
  on public.engineering_elements for insert to authenticated
  with check (exists (
    select 1 from public.projects p
    join public.organization_members m on m.organization_id = p.organization_id
    where p.id = engineering_elements.project_id and m.user_id = (select auth.uid())
  ));

drop policy if exists "engineering elements update members" on public.engineering_elements;
create policy "engineering elements update members"
  on public.engineering_elements for update to authenticated
  using (exists (
    select 1 from public.projects p
    join public.organization_members m on m.organization_id = p.organization_id
    where p.id = engineering_elements.project_id and m.user_id = (select auth.uid())
  ))
  with check (exists (
    select 1 from public.projects p
    join public.organization_members m on m.organization_id = p.organization_id
    where p.id = engineering_elements.project_id and m.user_id = (select auth.uid())
  ));

drop policy if exists "engineering elements delete members" on public.engineering_elements;
create policy "engineering elements delete members"
  on public.engineering_elements for delete to authenticated
  using (exists (
    select 1 from public.projects p
    join public.organization_members m on m.organization_id = p.organization_id
    where p.id = engineering_elements.project_id and m.user_id = (select auth.uid())
  ));

grant select, insert, update, delete on public.engineering_elements to authenticated;
