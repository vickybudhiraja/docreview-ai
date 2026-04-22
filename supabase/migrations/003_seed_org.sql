-- insert into organizations (name) values ('vickybudhiraja Org');

-- insert into users (org_id, email, role)
-- select id, 'admin@docreview.demo.ai', 'admin'
-- from organizations
-- where name = 'vickybudhiraja Org';

insert into organizations (name)
select 'vickybudhiraja Org'
where not exists (
  select 1 from organizations where name = 'vickybudhiraja Org'
);

insert into users (org_id, email, role)
select o.id, 'admin@docreview.demo.ai', 'admin'
from organizations o
where o.name = 'vickybudhiraja Org'
and not exists (
  select 1 from users where email = 'admin@docreview.demo.ai'
);
