create extension if not exists "pgcrypto";

create table organizations (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  created_at timestamptz not null default now()
);

create table users (
  id uuid primary key default gen_random_uuid(),
  org_id uuid references organizations(id) on delete cascade,
  email text not null unique,
  role text not null default 'admin',
  created_at timestamptz not null default now()
);

create table documents (
  id uuid primary key default gen_random_uuid(),
  org_id uuid references organizations(id) on delete cascade,
  file_name text not null,
  file_path text not null,
  mime_type text,
  source_type text not null default 'upload',
  checksum text,
  created_by uuid references users(id),
  created_at timestamptz not null default now()
);

create table reference_documents (
  id uuid primary key default gen_random_uuid(),
  org_id uuid references organizations(id) on delete cascade,
  file_name text not null,
  file_path text not null,
  corpus_name text,
  version text,
  created_at timestamptz not null default now()
);

create table brand_rule_sets (
  id uuid primary key default gen_random_uuid(),
  org_id uuid references organizations(id) on delete cascade,
  name text not null,
  version text not null,
  rules_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table review_jobs (
  id uuid primary key default gen_random_uuid(),
  org_id uuid references organizations(id) on delete cascade,
  document_id uuid references documents(id) on delete cascade,
  reference_document_id uuid references reference_documents(id),
  brand_rule_set_id uuid references brand_rule_sets(id),
  status text not null default 'uploaded',
  priority int not null default 5,
  current_stage text,
  error_message text,
  created_by uuid references users(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table findings (
  id uuid primary key default gen_random_uuid(),
  review_job_id uuid references review_jobs(id) on delete cascade,
  finding_type text not null,
  severity text not null,
  confidence numeric,
  page_number int,
  anchor_text text,
  bbox_json jsonb,
  suggested_comment text,
  evidence_json jsonb,
  status text not null default 'open',
  created_at timestamptz not null default now()
);

create table audit_events (
  id uuid primary key default gen_random_uuid(),
  entity_type text not null,
  entity_id uuid not null,
  action text not null,
  actor_id uuid,
  metadata_json jsonb,
  created_at timestamptz not null default now()
);