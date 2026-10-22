select p.source_file, p.sku, p.valid_from, p.raw_cost,
case when x.sku is null then 'unknown_sku' else 'invalid_cost' end as reason
from {{ ref('stg_prices') }} p
left join (select distinct sku from {{ ref('stg_products') }}) x on p.sku=x.sku
where x.sku is null or p.unit_cost_sar is null or p.unit_cost_sar <= 0
