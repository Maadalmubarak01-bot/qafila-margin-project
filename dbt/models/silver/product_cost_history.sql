with valid_prices as (
select p.sku, p.valid_from, p.unit_cost_sar, p.source_file,
 row_number() over(partition by p.sku,p.valid_from order by p.source_file desc) as priority
from {{ ref('stg_prices') }} p
join (select distinct sku from {{ ref('stg_products') }}) x on p.sku=x.sku
where p.unit_cost_sar > 0 and p.valid_from is not null
), dedup as (
select sku,valid_from,unit_cost_sar from valid_prices where priority=1
), changes as (
select *, lag(unit_cost_sar) over(partition by sku order by valid_from) as prior_cost
from dedup
), versions as (
select sku,valid_from,unit_cost_sar from changes
where prior_cost is null or prior_cost <> unit_cost_sar
)
select sku, cast(unit_cost_sar as double) as unit_cost_sar, valid_from,
lead(valid_from) over(partition by sku order by valid_from) as valid_to,
(lead(valid_from) over(partition by sku order by valid_from) is null) as is_current
from versions
