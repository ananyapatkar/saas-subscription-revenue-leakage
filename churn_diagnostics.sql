-- ============================================================
-- FILE: 03_churn_diagnostics.sql
-- ============================================================

USE northbeam_analytics;

-- ---- 3A. Logo churn rate by plan tier ----
-- Logo churn = cancelled customers / total customers, by tier.

SELECT
    s.plan_tier,
    COUNT(DISTINCT s.customer_id)                           AS total_customers,
    SUM(CASE WHEN s.status = 'Cancelled' THEN 1 ELSE 0 END) AS churned_customers,
    ROUND(100.0 *
        SUM(CASE WHEN s.status = 'Cancelled' THEN 1 ELSE 0 END) /
        COUNT(DISTINCT s.customer_id), 1)                   AS logo_churn_pct
FROM subscriptions s
GROUP BY s.plan_tier
ORDER BY logo_churn_pct DESC;


-- ---- 3B. Revenue churn rate by plan tier ----
-- Revenue churn = churned MRR / total MRR per tier.
-- Compare with 4A -- if revenue churn is much lower than logo churn,
-- it means small accounts are churning more (tolerable).
-- If revenue churn is high, large accounts are leaving (critical).

SELECT
    plan_tier,
    ROUND(SUM(mrr_amount), 2)                               AS total_mrr,
    ROUND(SUM(CASE WHEN status = 'Cancelled'
                   THEN mrr_amount ELSE 0 END), 2)          AS churned_mrr,
    ROUND(100.0 *
        SUM(CASE WHEN status = 'Cancelled' THEN mrr_amount ELSE 0 END) /
        SUM(mrr_amount), 1)                                 AS revenue_churn_pct
FROM subscriptions
GROUP BY plan_tier
ORDER BY revenue_churn_pct DESC;


-- ---- 3C. Churn rate by acquisition channel ----
-- Tests whether some channels bring in customers who don't stick.
-- Outbound Sales + heavy discount hypothesis will show up here.

SELECT
    c.acquisition_channel,
    COUNT(DISTINCT c.customer_id)                           AS total_customers,
    SUM(CASE WHEN s.status = 'Cancelled' THEN 1 ELSE 0 END) AS churned,
    ROUND(100.0 *
        SUM(CASE WHEN s.status = 'Cancelled' THEN 1 ELSE 0 END) /
        COUNT(DISTINCT c.customer_id), 1)                   AS churn_pct
FROM customers c
JOIN subscriptions s ON c.customer_id = s.customer_id
GROUP BY c.acquisition_channel
ORDER BY churn_pct DESC;



-- ---- 3. Support experience vs churn ----
-- Average CSAT below 3 is a known churn risk signal.

SELECT
    CASE WHEN s.status = 'Cancelled' THEN 'Churned' ELSE 'Active' END AS customer_status,
    ROUND(AVG(t.csat_score), 2)             AS avg_csat,
    ROUND(AVG(t.resolution_hours), 1)       AS avg_resolution_hours,
    COUNT(DISTINCT t.customer_id)           AS customers,
    SUM(CASE WHEN t.priority IN ('High','Urgent') THEN 1 ELSE 0 END) AS high_priority_tickets
FROM support_tickets t
JOIN subscriptions s ON t.customer_id = s.customer_id
GROUP BY customer_status
ORDER BY customer_status;