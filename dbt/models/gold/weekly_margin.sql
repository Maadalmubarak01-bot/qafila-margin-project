with eligible as (
select o.order_date, s.city, p.category, p.sku, i.quantity,
round(i.quantity * i.unit_price - coalesce(i.discount,0),2) as line_revenue
from {{ ref('stg_order_items') }} i
join {{ ref('stg_orders') }} o on i.order_id=o.order_id
join {{ ref('stg_products') }} p on i.product_id=p.product_id
join {{ ref('stg_stores') }} s on o.store_id=s.store_id
where o.status='delivered' and i.quantity>0 and o.order_date >= date '2026-08-31'
), costed as (
select e.*, h.unit_cost_sar,
cast(extract('week' from e.order_date) as integer) as iso_week
from eligible e left join {{ ref('product_cost_history') }} h
on e.sku=h.sku and e.order_date >= h.valid_from
and (h.valid_to is null or e.order_date < h.valid_to)
), sums as (
select iso_week, city, category, cast(count(*) as integer) as lines,
round(sum(line_revenue),2) as revenue_sar,
round(sum(case when unit_cost_sar is not null then line_revenue else 0 end),2) as costed_revenue_sar,
round(sum(case when unit_cost_sar is not null then quantity*unit_cost_sar else 0 end),2) as cost_sar,
cast(sum(case when unit_cost_sar is null then 1 else 0 end) as integer) as uncosted_lines
from costed group by 1,2,3
)
select *, round(costed_revenue_sar-cost_sar,2) as margin_sar from sums
