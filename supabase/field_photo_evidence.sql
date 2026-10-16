-- Private field photo evidence for construction site progress.
-- Apply after supabase/field.sql. Storage objects are scoped to project membership.

create table if not exists public.field_photo_evidence (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  diary_entry_id uuid references public.site_diary_entries(id) on delete set null,
  storage_path text not null unique,
  caption text,
  work_section text,
  captured_at timestamptz,
  created_by uuid not null default auth.uid(),
  created_at timestamptz not null default now(),
  constraint field_photo_evidence_path_matches_project
    check (split_part(storage_path, '/', 1) = project_id::text)
);

create index if not exists field_photo_evidence_project_created_idx
  on public.field_photo_evidence(project_id, created_at desc);

alter table public.field_photo_evidence enable row level security;

drop policy if exists field_photo_evidence_select on public.field_photo_evidence;
create policy field_photo_evidence_select on public.field_photo_evidence
  for select to authenticated using (
    exists (
      select 1 from public.projects p
      join public.organization_members m on m.organization_id = p.organization_id
      where p.id = field_photo_evidence.project_id and m.user_id = (select auth.uid())
    )
  );

drop policy if exists field_photo_evidence_insert on public.field_photo_evidence;
create policy field_photo_evidence_insert on public.field_photo_evidence
  for insert to authenticated with check (
    created_by = (select auth.uid()) and exists (
      select 1 from public.projects p
      join public.organization_members m on m.organization_id = p.organization_id
      where p.id = field_photo_evidence.project_id and m.user_id = (select auth.uid())
    )
  );

drop policy if exists field_photo_evidence_delete on public.field_photo_evidence;
create policy field_photo_evidence_delete on public.field_photo_evidence
  for delete to authenticated using (
    exists (
      select 1 from public.projects p
      join public.organization_members m on m.organization_id = p.organization_id
      where p.id = field_photo_evidence.project_id and m.user_id = (select auth.uid())
    )
  );

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('field-photo-evidence', 'field-photo-evidence', false, 10485760, array['image/jpeg','image/png','image/webp'])
on conflict (id) do update set
  public = false,
  file_size_limit = 10485760,
  allowed_mime_types = array['image/jpeg','image/png','image/webp'];

drop policy if exists field_photo_storage_select on storage.objects;
create policy field_photo_storage_select on storage.objects
  for select to authenticated using (
    bucket_id = 'field-photo-evidence'
    and exists (
      select 1 from public.projects p
      join public.organization_members m on m.organization_id = p.organization_id
      where p.id::text = (storage.foldername(name))[1] and m.user_id = (select auth.uid())
    )
  );

drop policy if exists field_photo_storage_insert on storage.objects;
create policy field_photo_storage_insert on storage.objects
  for insert to authenticated with check (
    bucket_id = 'field-photo-evidence'
    and exists (
      select 1 from public.projects p
      join public.organization_members m on m.organization_id = p.organization_id
      where p.id::text = (storage.foldername(name))[1] and m.user_id = (select auth.uid())
    )
  );

drop policy if exists field_photo_storage_delete on storage.objects;
create policy field_photo_storage_delete on storage.objects
  for delete to authenticated using (
    bucket_id = 'field-photo-evidence'
    and exists (
      select 1 from public.projects p
      join public.organization_members m on m.organization_id = p.organization_id
      where p.id::text = (storage.foldername(name))[1] and m.user_id = (select auth.uid())
    )
  );

grant select, insert, delete on public.field_photo_evidence to authenticated;
