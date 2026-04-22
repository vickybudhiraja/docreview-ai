create or replace function set_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

create trigger trg_review_jobs_updated_at
before update on review_jobs
for each row
execute function set_updated_at();