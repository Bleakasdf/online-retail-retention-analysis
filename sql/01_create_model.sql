-- Build the analytical model from cleaned line-item transactions.

DROP TABLE IF EXISTS fact_orders;
CREATE TABLE fact_orders AS
SELECT
    invoice_id,
    customer_id,
    invoice_ts,
    substr(invoice_ts, 1, 10) AS invoice_date,
    substr(invoice_ts, 1, 7) AS purchase_month,
    country,
    SUM(quantity) AS units,
    SUM(line_revenue) AS order_revenue,
    COUNT(DISTINCT stock_code) AS unique_products
FROM transactions_clean
WHERE invoice_ts < '2011-12-01'
GROUP BY
    invoice_id,
    customer_id,
    invoice_ts,
    country;

CREATE UNIQUE INDEX IF NOT EXISTS idx_fact_orders_natural_key
    ON fact_orders(invoice_id, customer_id, invoice_ts);
CREATE INDEX IF NOT EXISTS idx_fact_orders_customer_date
    ON fact_orders(customer_id, invoice_ts);

DROP TABLE IF EXISTS fact_orders_enriched;
CREATE TABLE fact_orders_enriched AS
SELECT
    o.*,
    ROW_NUMBER() OVER (
        PARTITION BY customer_id
        ORDER BY invoice_ts, invoice_id
    ) AS customer_order_number
FROM fact_orders AS o;

DROP TABLE IF EXISTS customer_primary_country;
CREATE TABLE customer_primary_country AS
WITH country_orders AS (
    SELECT
        customer_id,
        country,
        COUNT(*) AS orders,
        ROW_NUMBER() OVER (
            PARTITION BY customer_id
            ORDER BY COUNT(*) DESC, country
        ) AS country_rank
    FROM fact_orders
    GROUP BY customer_id, country
)
SELECT customer_id, country AS primary_country
FROM country_orders
WHERE country_rank = 1;

DROP TABLE IF EXISTS customer_month;
CREATE TABLE customer_month AS
SELECT
    o.customer_id,
    substr(o.invoice_ts, 1, 7) AS activity_month,
    c.primary_country,
    COUNT(*) AS orders,
    SUM(o.order_revenue) AS revenue,
    SUM(o.units) AS units
FROM fact_orders AS o
LEFT JOIN customer_primary_country AS c
    ON o.customer_id = c.customer_id
GROUP BY
    o.customer_id,
    substr(o.invoice_ts, 1, 7),
    c.primary_country;

CREATE UNIQUE INDEX IF NOT EXISTS idx_customer_month
    ON customer_month(customer_id, activity_month);

DROP TABLE IF EXISTS customer_cohorts;
CREATE TABLE customer_cohorts AS
SELECT
    customer_id,
    MIN(activity_month) AS cohort_month,
    MAX(primary_country) AS primary_country
FROM customer_month
GROUP BY customer_id;

DROP TABLE IF EXISTS cohort_retention;
CREATE TABLE cohort_retention AS
WITH cohort_activity AS (
    SELECT
        c.cohort_month,
        m.activity_month,
        (
            (CAST(substr(m.activity_month, 1, 4) AS INTEGER)
             - CAST(substr(c.cohort_month, 1, 4) AS INTEGER)) * 12
            + CAST(substr(m.activity_month, 6, 2) AS INTEGER)
            - CAST(substr(c.cohort_month, 6, 2) AS INTEGER)
        ) AS month_number,
        COUNT(DISTINCT m.customer_id) AS retained_customers
    FROM customer_month AS m
    JOIN customer_cohorts AS c
        ON m.customer_id = c.customer_id
    GROUP BY c.cohort_month, m.activity_month
),
cohort_sizes AS (
    SELECT cohort_month, COUNT(*) AS cohort_size
    FROM customer_cohorts
    GROUP BY cohort_month
)
SELECT
    a.cohort_month,
    a.activity_month,
    a.month_number,
    s.cohort_size,
    a.retained_customers,
    1.0 * a.retained_customers / s.cohort_size AS retention_rate
FROM cohort_activity AS a
JOIN cohort_sizes AS s
    ON a.cohort_month = s.cohort_month
WHERE a.month_number >= 0;

DROP TABLE IF EXISTS monthly_customer_metrics;
CREATE TABLE monthly_customer_metrics AS
WITH customer_status AS (
    SELECT
        m.*,
        c.cohort_month,
        CASE WHEN m.activity_month = c.cohort_month THEN 1 ELSE 0 END AS new_customer_month
    FROM customer_month AS m
    JOIN customer_cohorts AS c
        ON m.customer_id = c.customer_id
),
monthly_customers AS (
    SELECT
        activity_month,
        COUNT(*) AS active_customers,
        SUM(new_customer_month) AS new_customers,
        SUM(CASE WHEN new_customer_month = 0 THEN 1 ELSE 0 END) AS returning_customers,
        SUM(revenue) AS revenue
    FROM customer_status
    GROUP BY activity_month
),
monthly_orders AS (
    SELECT
        purchase_month AS activity_month,
        COUNT(*) AS orders,
        SUM(CASE WHEN customer_order_number > 1 THEN 1 ELSE 0 END) AS repeat_orders,
        SUM(order_revenue) AS order_revenue,
        SUM(CASE WHEN customer_order_number > 1 THEN order_revenue ELSE 0 END) AS repeat_order_revenue
    FROM fact_orders_enriched
    GROUP BY purchase_month
)
SELECT
    c.activity_month,
    c.active_customers,
    c.new_customers,
    c.returning_customers,
    o.orders,
    o.repeat_orders,
    c.revenue,
    o.repeat_order_revenue,
    1.0 * c.returning_customers / c.active_customers AS returning_customer_share,
    1.0 * o.repeat_order_revenue / o.order_revenue AS repeat_revenue_share
FROM monthly_customers AS c
JOIN monthly_orders AS o
    ON c.activity_month = o.activity_month;

DROP TABLE IF EXISTS rfm_backtest;
CREATE TABLE rfm_backtest AS
WITH historical AS (
    SELECT
        o.customer_id,
        c.primary_country,
        CAST(julianday('2010-12-01') - julianday(MAX(o.invoice_date)) AS INTEGER) AS recency_days,
        COUNT(*) AS frequency_orders,
        SUM(o.order_revenue) AS monetary_revenue
    FROM fact_orders AS o
    LEFT JOIN customer_primary_country AS c
        ON o.customer_id = c.customer_id
    WHERE o.invoice_date >= '2009-12-01'
      AND o.invoice_date < '2010-12-01'
    GROUP BY o.customer_id, c.primary_country
),
scored AS (
    SELECT
        h.*,
        NTILE(4) OVER (ORDER BY monetary_revenue) AS monetary_quartile
    FROM historical AS h
),
segmented AS (
    SELECT
        s.*,
        CASE
            WHEN recency_days <= 90 AND (frequency_orders >= 5 OR monetary_quartile = 4)
                THEN 'Loyal Active'
            WHEN recency_days <= 90 AND frequency_orders >= 2
                THEN 'Repeat Active'
            WHEN recency_days <= 90
                THEN 'New / One-time Recent'
            WHEN recency_days <= 180 AND (frequency_orders >= 5 OR monetary_quartile = 4)
                THEN 'High-Value At Risk'
            WHEN recency_days <= 180
                THEN 'Occasional At Risk'
            WHEN frequency_orders >= 5 OR monetary_quartile = 4
                THEN 'High-Value Lapsed'
            ELSE 'Hibernating'
        END AS rfm_segment
    FROM scored AS s
),
future AS (
    SELECT
        customer_id,
        COUNT(*) AS future_orders,
        SUM(order_revenue) AS future_revenue
    FROM fact_orders
    WHERE invoice_date >= '2010-12-01'
      AND invoice_date < '2011-12-01'
    GROUP BY customer_id
)
SELECT
    s.*,
    COALESCE(f.future_orders, 0) AS future_orders,
    COALESCE(f.future_revenue, 0) AS future_revenue,
    CASE WHEN COALESCE(f.future_orders, 0) > 0 THEN 1 ELSE 0 END AS repeat_12m_flag
FROM segmented AS s
LEFT JOIN future AS f
    ON s.customer_id = f.customer_id;

DROP TABLE IF EXISTS rfm_current;
CREATE TABLE rfm_current AS
WITH historical AS (
    SELECT
        o.customer_id,
        c.primary_country,
        CAST(julianday('2011-12-01') - julianday(MAX(o.invoice_date)) AS INTEGER) AS recency_days,
        COUNT(*) AS frequency_orders,
        SUM(o.order_revenue) AS monetary_revenue
    FROM fact_orders AS o
    LEFT JOIN customer_primary_country AS c
        ON o.customer_id = c.customer_id
    WHERE o.invoice_date >= '2010-12-01'
      AND o.invoice_date < '2011-12-01'
    GROUP BY o.customer_id, c.primary_country
),
scored AS (
    SELECT
        h.*,
        NTILE(4) OVER (ORDER BY monetary_revenue) AS monetary_quartile
    FROM historical AS h
)
SELECT
    s.*,
    CASE
        WHEN recency_days <= 90 AND (frequency_orders >= 5 OR monetary_quartile = 4)
            THEN 'Loyal Active'
        WHEN recency_days <= 90 AND frequency_orders >= 2
            THEN 'Repeat Active'
        WHEN recency_days <= 90
            THEN 'New / One-time Recent'
        WHEN recency_days <= 180 AND (frequency_orders >= 5 OR monetary_quartile = 4)
            THEN 'High-Value At Risk'
        WHEN recency_days <= 180
            THEN 'Occasional At Risk'
        WHEN frequency_orders >= 5 OR monetary_quartile = 4
            THEN 'High-Value Lapsed'
        ELSE 'Hibernating'
    END AS rfm_segment
FROM scored AS s;

DROP VIEW IF EXISTS rfm_backtest_summary;
CREATE VIEW rfm_backtest_summary AS
SELECT
    rfm_segment,
    COUNT(*) AS customers,
    SUM(monetary_revenue) AS historical_revenue,
    AVG(monetary_revenue) AS avg_historical_revenue,
    AVG(repeat_12m_flag) AS next_12m_repeat_rate,
    SUM(future_revenue) AS next_12m_revenue,
    AVG(future_revenue) AS avg_next_12m_revenue
FROM rfm_backtest
GROUP BY rfm_segment;

DROP VIEW IF EXISTS rfm_current_summary;
CREATE VIEW rfm_current_summary AS
SELECT
    rfm_segment,
    COUNT(*) AS customers,
    SUM(monetary_revenue) AS trailing_12m_revenue,
    AVG(monetary_revenue) AS avg_customer_revenue,
    AVG(recency_days) AS avg_recency_days,
    AVG(frequency_orders) AS avg_orders
FROM rfm_current
GROUP BY rfm_segment;

DROP VIEW IF EXISTS country_priority;
CREATE VIEW country_priority AS
WITH country_base AS (
    SELECT
        primary_country,
        COUNT(*) AS customers,
        SUM(monetary_revenue) AS trailing_12m_revenue
    FROM rfm_current
    GROUP BY primary_country
),
target AS (
    SELECT
        primary_country,
        COUNT(*) AS target_customers,
        SUM(monetary_revenue) AS target_historical_revenue
    FROM rfm_current
    WHERE rfm_segment IN ('High-Value At Risk', 'High-Value Lapsed')
    GROUP BY primary_country
)
SELECT
    b.primary_country AS country,
    b.customers,
    COALESCE(t.target_customers, 0) AS target_customers,
    1.0 * COALESCE(t.target_customers, 0) / b.customers AS target_customer_share,
    b.trailing_12m_revenue,
    COALESCE(t.target_historical_revenue, 0) AS target_historical_revenue,
    1.0 * COALESCE(t.target_historical_revenue, 0) / b.trailing_12m_revenue AS target_revenue_share
FROM country_base AS b
LEFT JOIN target AS t
    ON b.primary_country = t.primary_country;

DROP VIEW IF EXISTS target_product_affinity;
CREATE VIEW target_product_affinity AS
SELECT
    t.stock_code,
    MAX(t.description) AS product_description,
    COUNT(DISTINCT t.customer_id) AS target_customers,
    SUM(t.quantity) AS units,
    SUM(t.line_revenue) AS historical_revenue
FROM transactions_clean AS t
JOIN rfm_current AS r
    ON t.customer_id = r.customer_id
WHERE t.invoice_ts >= '2010-12-01'
  AND t.invoice_ts < '2011-12-01'
  AND r.rfm_segment IN ('High-Value At Risk', 'High-Value Lapsed')
GROUP BY t.stock_code;
