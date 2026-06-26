-- ============================================================
USE northbeam_analytics;

-- ---- 1A. Monthly Active MRR ----
-- Logic: for each calendar month, sum mrr_amount for all subscriptions
-- that were active during that month (started before month end,
-- ended after month start or are still active).
-- This is the foundation number everything else is derived from.

SELECT
    DATE_FORMAT(s.start_date, '%Y-%m')          AS month,
    s.plan_tier,
    COUNT(DISTINCT s.customer_id)               AS active_customers,
    ROUND(SUM(s.mrr_amount), 2)                 AS mrr,
    ROUND(SUM(s.mrr_amount) * 12, 2)            AS arr
FROM subscriptions s
WHERE s.status = 'Active'
GROUP BY DATE_FORMAT(s.start_date, '%Y-%m'), s.plan_tier
ORDER BY month, s.plan_tier;


-- ---- 1B. Total current ARR snapshot (as of today) ----
-- This is the single headline number the CFO wants first.

SELECT
    ROUND(SUM(mrr_amount) * 12, 2)  AS current_arr,
    ROUND(SUM(mrr_amount), 2)       AS current_mrr,
    COUNT(DISTINCT customer_id)     AS total_active_customers
FROM subscriptions
WHERE status = 'Active';


-- ---- 1C. MRR by plan tier (current snapshot) ----
-- Breaks the ARR into its tier components so we can see
-- which tier is the revenue engine vs the volume engine.

SELECT
    plan_tier,
    COUNT(DISTINCT customer_id)     AS active_customers,
    ROUND(SUM(mrr_amount), 2)       AS mrr,
    ROUND(SUM(mrr_amount) * 12, 2) AS arr,
    ROUND(
        100.0 * SUM(mrr_amount) /
        (SELECT SUM(mrr_amount) FROM subscriptions WHERE status = 'Active'),
    1)                              AS pct_of_total_mrr
FROM subscriptions
WHERE status = 'Active'
GROUP BY plan_tier
ORDER BY arr DESC;