select order_id, store_id, status,
 cast(cast(created_at as timestamptz) at time zone 'Asia/Riyadh' as date) as order_date
 from {{ source('raw','orders') }}
