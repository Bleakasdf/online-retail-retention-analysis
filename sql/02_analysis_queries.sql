-- 1. Dataset and cleaning flow
SELECT * FROM data_quality_summary ORDER BY check_order;

-- 2. Overall customer and repeat-revenue health
SELECT
    COUNT(DISTINCT customer_id) AS customers,
    COUNT(*) AS orders,
    SUM(order_revenue) AS revenue,
    SUM(CASE WHEN customer_order_number > 1 THEN 1 ELSE 0 END) AS repeat_orders,
    SUM(CASE WHEN customer_order_number > 1 THEN order_revenue ELSE 0 END) AS repeat_revenue,
    1.0 * SUM(CASE WHEN customer_order_number > 1 THEN order_revenue ELSE 0 END)
        / SUM(order_revenue) AS repeat_revenue_share
FROM fact_orders_enriched;

-- 3. Monthly customer and revenue movement
SELECT *
FROM monthly_customer_metrics
ORDER BY activity_month;

-- 4. Weighted cohort retention at complete horizons
SELECT
    month_number,
    SUM(retained_customers) AS retained_customers,
    SUM(cohort_size) AS eligible_cohort_customers,
    1.0 * SUM(retained_customers) / SUM(cohort_size) AS weighted_retention_rate
FROM cohort_retention
WHERE month_number IN (1, 3, 6)
GROUP BY month_number
ORDER BY month_number;

-- 5. Cohort matrix source
SELECT
    cohort_month,
    month_number,
    cohort_size,
    retained_customers,
    retention_rate
FROM cohort_retention
WHERE month_number <= 12
ORDER BY cohort_month, month_number;

-- 6. Historical RFM backtest
SELECT *
FROM rfm_backtest_summary
ORDER BY next_12m_revenue DESC;

-- 7. Current portfolio by RFM segment
SELECT *
FROM rfm_current_summary
ORDER BY trailing_12m_revenue DESC;

-- 8. Markets for CRM prioritization
SELECT *
FROM country_priority
WHERE customers >= 20
ORDER BY target_historical_revenue DESC;

-- 9. Products previously purchased by target customers
SELECT *
FROM target_product_affinity
WHERE target_customers >= 10
ORDER BY target_customers DESC, historical_revenue DESC
LIMIT 25;
