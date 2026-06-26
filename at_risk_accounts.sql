-- ============================================================
-- FILE: 05_at_risk_accounts.sql
-- ============================================================

USE northbeam_analytics;

WITH usage_trend AS (
    SELECT
        customer_id,
        ROUND(AVG(CASE WHEN event_date >= DATE_SUB(CURDATE(), INTERVAL 8 WEEK)
                       THEN login_count END), 1)    AS recent_avg_logins,
        ROUND(AVG(CASE WHEN event_date BETWEEN
                            DATE_SUB(CURDATE(), INTERVAL 16 WEEK)
                        AND DATE_SUB(CURDATE(), INTERVAL 8 WEEK)
                       THEN login_count END), 1)    AS prior_avg_logins
    FROM usage_events
    GROUP BY customer_id
),

ticket_signals AS (
    -- High/Urgent ticket count and avg CSAT in last 60 days
    SELECT
        customer_id,
        COUNT(*)                                    AS tickets_last_60d,
        SUM(CASE WHEN priority IN ('High','Urgent')
                 THEN 1 ELSE 0 END)                AS high_priority_tickets,
        ROUND(AVG(csat_score), 2)                  AS avg_csat_last_60d
    FROM support_tickets
    WHERE created_date >= DATE_SUB(CURDATE(), INTERVAL 60 DAY)
    GROUP BY customer_id
),

failed_payments AS (
    -- Any failed payment in last 90 days is a hard churn warning signal
    SELECT DISTINCT s.customer_id
    FROM invoices i
    JOIN subscriptions s ON i.subscription_id = s.subscription_id
    WHERE i.payment_status = 'Failed'
      AND i.invoice_date >= DATE_SUB(CURDATE(), INTERVAL 90 DAY)
)

SELECT
    c.customer_id,
    c.company_name,
    c.company_size_band,
    sub.plan_tier,
    ROUND(sub.mrr_amount, 2)                        AS mrr,
    c.assigned_csm,
    ROUND(ut.recent_avg_logins, 1)                  AS recent_weekly_logins,
    ROUND(ut.prior_avg_logins, 1)                   AS prior_weekly_logins,
    ROUND(100.0 * (ut.prior_avg_logins - ut.recent_avg_logins)
          / NULLIF(ut.prior_avg_logins, 0), 1)      AS login_decline_pct,
    COALESCE(ts.tickets_last_60d, 0)                AS tickets_last_60d,
    COALESCE(ts.high_priority_tickets, 0)           AS high_priority_tickets,
    COALESCE(ts.avg_csat_last_60d, 5)               AS avg_csat,
    CASE WHEN fp.customer_id IS NOT NULL
         THEN 'YES' ELSE 'NO' END                   AS failed_payment_90d,
    -- Risk flag: accounts with 2+ of these warning signs are priority outreach
    (
        (CASE WHEN ut.recent_avg_logins < ut.prior_avg_logins * 0.7 THEN 1 ELSE 0 END) +
        (CASE WHEN ts.high_priority_tickets >= 2                     THEN 1 ELSE 0 END) +
        (CASE WHEN ts.avg_csat_last_60d < 3                          THEN 1 ELSE 0 END) +
        (CASE WHEN fp.customer_id IS NOT NULL                        THEN 1 ELSE 0 END)
    )                                               AS risk_flag_count
FROM customers c
JOIN subscriptions sub
    ON c.customer_id = sub.customer_id
    AND sub.status = 'Active'
LEFT JOIN usage_trend ut      ON c.customer_id = ut.customer_id
LEFT JOIN ticket_signals ts   ON c.customer_id = ts.customer_id
LEFT JOIN failed_payments fp  ON c.customer_id = fp.customer_id
ORDER BY risk_flag_count DESC, sub.mrr_amount DESC
LIMIT 50;