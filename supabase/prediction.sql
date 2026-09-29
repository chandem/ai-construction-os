-- Prediction: risks + forecasts (Phase 10)

create table if not exists public.project_risks (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  risk_code text,
  title text not null,
  category text default 'other',
  level text default 'medium'
    check (level in ('low','medium','high','critical')),
  description text,
  signal text,
  probability numeric,
  impact numeric,
  score numeric,
  mitigation text,
  status text not null default 'open'
    check (status in ('open','mitigating','accepted','closed','cancelled')),
  source text default 'prediction_heuristic',
  properties jsonb default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists project_risks_project_idx on public.project_risks(project_id);
create index if not exists project_risks_level_idx on public.project_risks(project_id, level);
create index if not exists project_risks_status_idx on public.project_risks(project_id, status);

create table if not exists public.project_forecasts (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  forecast_type text not null,
  label text,
  value numeric,
  unit text,
  baseline numeric,
  delta numeric,
  confidence text,
  method text,
  notes text,
  source text default 'prediction_heuristic',
  properties jsonb default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists project_forecasts_project_idx on public.project_forecasts(project_id);
create index if not exists project_forecasts_type_idx on public.project_forecasts(project_id, forecast_type);

alter table public.project_risks enable row level security;
alter table public.project_forecasts enable row level security;

create policy "project_risks_select" on public.project_risks
  for select using (
    exists (
      select 1 from public.projects p
      join public.organization_members m on m.organization_id = p.organization_id
      where p.id = project_risks.project_id and m.user_id = auth.uid()
    )
  );
create policy "project_risks_insert" on public.project_risks
  for insert with check (
    exists (
      select 1 from public.projects p
      join public.organization_members m on m.organization_id = p.organization_id
      where p.id = project_risks.project_id and m.user_id = auth.uid()
    )
  );
create policy "project_risks_update" on public.project_risks
  for update using (
    exists (
      select 1 from public.projects p
      join public.organization_members m on m.organization_id = p.organization_id
      where p.id = project_risks.project_id and m.user_id = auth.uid()
    )
  );

create policy "project_forecasts_select" on public.project_forecasts
  for select using (
    exists (
      select 1 from public.projects p
      join public.organization_members m on m.organization_id = p.organization_id
      where p.id = project_forecasts.project_id and m.user_id = auth.uid()
    )
  );
create policy "project_forecasts_insert" on public.project_forecasts
  for insert with check (
    exists (
      select 1 from public.projects p
      join public.organization_members m on m.organization_id = p.organization_id
      where p.id = project_forecasts.project_id and m.user_id = auth.uid()
    )
  );
create policy "project_forecasts_update" on public.project_forecasts
  for update using (
    exists (
      select 1 from public.projects p
      join public.organization_members m on m.organization_id = p.organization_id
      where p.id = project_forecasts.project_id and m.user_id = auth.uid()
    )
  );

create or replace function public.set_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists project_risks_updated_at on public.project_risks;
create trigger project_risks_updated_at
  before update on public.project_risks
  for each row execute function public.set_updated_at();

drop trigger if exists project_forecasts_updated_at on public.project_forecasts;
create trigger project_forecasts_updated_at
  before update on public.project_forecasts
  for each row execute function public.set_updated_at();
