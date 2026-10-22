with normalized as (
 select source_file, trim(sku) as sku, try_cast(valid_from as date) as valid_from,
 raw_cost,
 translate(replace(replace(replace(trim(raw_cost), '٫', '.'), '٬', ''), ',', '.'),
 '٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹', '01234567890123456789') as cost_text
 from {{ source('raw','supplier_prices') }}
)
select *, round(try_cast(cost_text as double),2) as unit_cost_sar from normalized
