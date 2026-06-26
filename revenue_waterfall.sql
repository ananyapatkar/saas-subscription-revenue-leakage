-- ============================================================
-- FILE: 02_revenue_waterfall.sql
-- ============================================================

USE northbeam_analytics;

-- ---- 2A. MRR movement by change type per month ----
-- New        = brand new customers (change_type = 'New')
-- Expansion  = existing customers upgrading (change_type = 'Upgrade')
-- Contraction= existing customers downgrading (change_type = 'Downgrade')
-- Churned    = cancelled subscriptions (status = 'Cancelled')

SELECT
    DATE_FORMAT(start_date, '%Y-%m')    AS month,
    change_type,
    COUNT(DISTINCT customer_id)         AS customers,
    ROUND(SUM(mrr_amount), 2)           AS mrr_impact
FROM subscriptions
GROUP BY DATE_FORMAT(start_date, '%Y-%m'), change_type
ORDER BY month, change_type;


-- ---- 2B. Net New MRR per month (the waterfall bottom line) ----
-- Formula: New + Expansion - Contraction - Churned
-- A positive number = ARR is growing. Negative = ARR is shrinking.

SELECT
    DATE_FORMAT(start_date, '%Y-%m')                AS month,
    ROUND(SUM(CASE WHEN change_type = 'New'
                   THEN mrr_amount ELSE 0 END), 2)  AS new_mrr,
    ROUND(SUM(CASE WHEN change_type = 'Upgrade'
                   THEN mrr_amount ELSE 0 END), 2)  AS expansion_mrr,
    ROUND(SUM(CASE WHEN change_type = 'Downgrade'
                   THEN mrr_amount ELSE 0 END), 2)  AS contraction_mrr,
    ROUND(SUM(CASE WHEN status = 'Cancelled'
                   THEN mrr_amount ELSE 0 END), 2)  AS churned_mrr,
    ROUND(
        SUM(CASE WHEN change_type = 'New'      THEN mrr_amount ELSE 0 END) +
        SUM(CASE WHEN change_type = 'Upgrade'  THEN mrr_amount ELSE 0 END) -
        SUM(CASE WHEN change_type = 'Downgrade'THEN mrr_amount ELSE 0 END) -
        SUM(CASE WHEN status = 'Cancelled'     THEN mrr_amount ELSE 0 END),
    2)                                              AS net_new_mrr
FROM subscriptions
GROUP BY DATE_FORMAT(start_date, '%Y-%m')
ORDER BY month;


-- ---- 2C. Failed payment revenue leakage by month ----
-- This is the third leakage vector beyond churn and downgrades.
-- You found $74K gap in November alone from reconciliation.
-- This query surfaces that pattern across all months.

SELECT
    DATE_FORMAT(invoice_date, '%Y-%m')  AS month,
    payment_status,
    COUNT(*)                            AS invoice_count,
    ROUND(SUM(amount_due), 2)           AS amount_billed,
    ROUND(SUM(amount_paid), 2)          AS amount_collected,
    ROUND(SUM(amount_due - amount_paid), 2) AS revenue_gap
FROM invoices
WHERE payment_status IN ('Failed', 'Refunded')
GROUP BY DATE_FORMAT(invoice_date, '%Y-%m'), payment_status
ORDER BY month, payment_status;