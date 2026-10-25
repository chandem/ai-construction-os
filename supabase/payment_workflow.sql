-- Work-completion payments: measured work -> certification -> approval -> payment.
-- Apply this SQL to the project's Supabase SQL Editor before using the Payments center.

create table if not exists public.work_payment_certificates (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  payee_type text not null check (payee_type in ('contractor', 'internal_unit')),
  payee_name text not null,
  reference text,
  description text not null,
  unit text not null,
  measured_quantity numeric(18,4) not null default 0 check (measured_quantity >= 0),
  certified_quantity numeric(18,4) not null default 0 check (certified_quantity >= 0),
  unit_rate numeric(18,4) not null default 0 check (unit_rate >= 0),
  gross_amount numeric(18,2) not null default 0 check (gross_amount >= 0),
  deductions numeric(18,2) not null default 0 check (deductions >= 0),
  net_amount numeric(18,2) not null default 0 check (net_amount >= 0),
  status text not null default 'measured'
    check (status in ('measured', 'submitted', 'certified', 'approved', 'paid', 'rejected')),
  measurement_date date not null default current_date,
  engineer_name text,
  certification_note text,
  certified_by uuid references auth.users(id) on delete set null,
  certified_at timestamptz,
  approved_by uuid references auth.users(id) on delete set null,
  approved_at timestamptz,
  paid_by uuid references auth.users(id) on delete set null,
  paid_at timestamptz,
  payment_reference text,
  notes text,
  created_by uuid references auth.users(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists work_payment_project_status_idx
  on public.work_payment_certificates(project_id, status, created_at desc);
create index if not exists work_payment_payee_idx
  on public.work_payment_certificates(project_id, payee_type, payee_name);

alter table public.work_payment_certificates enable row level security;

drop policy if exists work_payment_select on public.work_payment_certificates;
create policy work_payment_select on public.work_payment_certificates
  for select using (
    exists (
      select 1 from public.projects p
      join public.organization_members m on m.organization_id = p.organization_id
      where p.id = work_payment_certificates.project_id and m.user_id = auth.uid()
    )
  );

drop policy if exists work_payment_insert on public.work_payment_certificates;
create policy work_payment_insert on public.work_payment_certificates
  for insert with check (
    created_by = auth.uid() and exists (
      select 1 from public.projects p
      join public.organization_members m on m.organization_id = p.organization_id
      where p.id = work_payment_certificates.project_id and m.user_id = auth.uid()
    )
  );

drop policy if exists work_payment_update on public.work_payment_certificates;
create policy work_payment_update on public.work_payment_certificates
  for update using (
    exists (
      select 1 from public.projects p
      join public.organization_members m on m.organization_id = p.organization_id
      where p.id = work_payment_certificates.project_id and m.user_id = auth.uid()
    )
  ) with check (
    exists (
      select 1 from public.projects p
      join public.organization_members m on m.organization_id = p.organization_id
      where p.id = work_payment_certificates.project_id and m.user_id = auth.uid()
    )
  );

drop trigger if exists work_payment_certificates_updated_at on public.work_payment_certificates;
create trigger work_payment_certificates_updated_at
  before update on public.work_payment_certificates
  for each row execute function public.set_updated_at();
