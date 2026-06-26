"""
generate_data.py
=================
Synthetic data generator for the Northbeam Analytics SaaS Revenue Leakage project.

Produces 5 relational CSVs in /data/raw:
    customers.csv
    subscriptions.csv
    invoices.csv
    usage_events.csv
    support_tickets.csv

Design goals (read this before editing):
1. Tables are relationally consistent (every FK exists in its parent table).
2. Real business patterns are baked in on purpose, so later analysis "discovers"
   genuine signal instead of noise:
     - Enterprise accounts WITH an assigned CSM churn ~40% less than those without.
     - Accounts with 2+ high-priority tickets and low CSAT in the 60 days before
       cancellation churn at a much higher rate.
     - Heavy-discount / Outbound-Sales-acquired accounts renew often (low logo churn)
       but at eroded prices (poor revenue retention) -- a classic NRR drag.
     - Declining login activity over 8+ weeks precedes most cancellations.
3. Deliberate messiness is injected so Phase 2 (cleaning) has real work to do:
     - Inconsistent casing / whitespace in categorical text fields
     - A handful of duplicate invoice rows
     - A few out-of-range CSAT scores
     - Some missing (NaN) values in non-critical columns
     - A few orphan-ish formatting issues (e.g. stray currency symbols as strings)

Run:
    python generate_data.py
"""
import os
os.makedirs("./data/raw", exist_ok=True)
import numpy as np
import pandas as pd
from faker import Faker
import random
from datetime import timedelta

# ----------------------------------------------------------------------------
# Config
# ----------------------------------------------------------------------------
SEED = 42
random.seed(SEED)
np.random.seed(SEED)
fake = Faker()
Faker.seed(SEED)

N_CUSTOMERS = 3000
PROJECT_START = pd.Timestamp("2023-01-01")   # earliest possible signup
TODAY = pd.Timestamp("2025-12-31")           # "as of" date for the project (snapshot end)

OUT_DIR = "./data/raw"

INDUSTRIES = ["Software", "Retail", "Healthcare", "Manufacturing", "Education",
              "Financial Services", "Media", "Logistics", "Hospitality", "Construction"]
SIZE_BANDS = ["SMB", "Mid-Market", "Enterprise"]
COUNTRIES = ["United States", "United Kingdom", "Canada", "Australia", "Germany",
             "India", "Singapore", "Netherlands", "France", "Ireland"]
CHANNELS = ["Organic", "Paid", "Referral", "Outbound Sales"]
TIERS = ["Starter", "Growth", "Enterprise"]
TIER_BASE_MRR = {"Starter": 49, "Growth": 199, "Enterprise": 899}
CHANGE_TYPES = ["New", "Upgrade", "Downgrade", "Reactivation", "Cancellation"]
FEATURES = ["Dashboards", "Task Boards", "Reporting", "Integrations", "Automations",
            "Time Tracking", "Calendar Sync", "API Access"]
TICKET_CATEGORIES = ["Billing", "Bug Report", "Feature Request", "Onboarding Help",
                      "Performance Issue", "Account Access", "General Question"]
PRIORITIES = ["Low", "Medium", "High", "Urgent"]

CSM_NAMES = [fake.name() for _ in range(12)]  # pool of CSMs for Mid-Market/Enterprise


def messify_text(value, dirty_rate=0.04):
    """Randomly mangle casing/whitespace on a categorical text value."""
    if random.random() < dirty_rate:
        choice = random.random()
        if choice < 0.4:
            return value.upper()
        elif choice < 0.7:
            return value.lower()
        else:
            return f"  {value}  "  # stray whitespace
    return value


def random_date_with_growth(start, end, growth=True):
    """
    Pick a random date between start/end, weighted to reflect signup growth
    over time (more recent months get more signups) rather than uniform spread.
    """
    days_range = (end - start).days
    if growth:
        # skew toward later dates using a power distribution
        r = np.random.power(2.2)
    else:
        r = np.random.random()
    return start + timedelta(days=int(r * days_range))


# ----------------------------------------------------------------------------
# 1. CUSTOMERS
# ----------------------------------------------------------------------------
def generate_customers(n=N_CUSTOMERS):
    rows = []
    for i in range(1, n + 1):
        customer_id = f"CUST{i:05d}"
        size_band = np.random.choice(SIZE_BANDS, p=[0.55, 0.30, 0.15])
        industry = random.choice(INDUSTRIES)
        country = np.random.choice(COUNTRIES, p=[0.35, 0.12, 0.10, 0.07, 0.08,
                                                   0.08, 0.06, 0.05, 0.05, 0.04])
        signup_date = random_date_with_growth(PROJECT_START, TODAY - timedelta(days=30))
        channel = np.random.choice(CHANNELS, p=[0.30, 0.25, 0.20, 0.25])

        # Business rule: Mid-Market/Enterprise often get a CSM; Starter rarely does.
        # Within Enterprise, ~78% get a CSM (so ~22% are the "unassigned" risk group
        # the whole project is built to surface).
        if size_band == "Enterprise":
            has_csm = np.random.random() < 0.78
        elif size_band == "Mid-Market":
            has_csm = np.random.random() < 0.45
        else:
            has_csm = np.random.random() < 0.03
        assigned_csm = random.choice(CSM_NAMES) if has_csm else np.nan

        rows.append({
            "customer_id": customer_id,
            "company_name": fake.company(),
            "industry": messify_text(industry),
            "company_size_band": size_band,
            "country": messify_text(country),
            "signup_date": signup_date.date(),
            "acquisition_channel": channel,
            "assigned_csm": assigned_csm,
        })

    df = pd.DataFrame(rows)

    # Inject a few duplicate customer rows (common real-world dirty data issue)
    dupes = df.sample(n=8, random_state=SEED)
    df = pd.concat([df, dupes], ignore_index=True)

    return df


# ----------------------------------------------------------------------------
# 2. SUBSCRIPTIONS
# ----------------------------------------------------------------------------
def generate_subscriptions(customers_df):
    rows = []
    sub_counter = 1

    for _, cust in customers_df.drop_duplicates("customer_id").iterrows():
        customer_id = cust["customer_id"]
        size_band = cust["company_size_band"]
        signup_date = pd.Timestamp(cust["signup_date"])
        has_csm = pd.notna(cust["assigned_csm"])
        channel = cust["acquisition_channel"]

        # Plan tier eligibility loosely follows company size
        if size_band == "Enterprise":
            tier = np.random.choice(TIERS, p=[0.05, 0.25, 0.70])
        elif size_band == "Mid-Market":
            tier = np.random.choice(TIERS, p=[0.20, 0.60, 0.20])
        else:
            tier = np.random.choice(TIERS, p=[0.65, 0.32, 0.03])

        base_mrr = TIER_BASE_MRR[tier]

        # Discount logic: Outbound Sales deals get discounted more often/heavily
        if channel == "Outbound Sales":
            discount = np.random.choice([0, 10, 15, 20, 25], p=[0.20, 0.20, 0.25, 0.20, 0.15])
        else:
            discount = np.random.choice([0, 5, 10, 15], p=[0.55, 0.20, 0.15, 0.10])

        mrr_amount = round(base_mrr * (1 - discount / 100), 2)

        # ---- Churn probability engineering ----
        # Base churn risk by tier
        base_churn_p = {"Starter": 0.32, "Growth": 0.20, "Enterprise": 0.14}[tier]
        # CSM effect: having a CSM cuts churn risk substantially (Enterprise/Mid-Market story)
        if has_csm:
            base_churn_p *= 0.60
        # Heavy discount + outbound channel: renews more (lower churn) but at bad economics
        if channel == "Outbound Sales" and discount >= 20:
            base_churn_p *= 0.75

        will_churn = np.random.random() < base_churn_p

        months_active_max = max(1, (TODAY - signup_date).days // 30)
        if will_churn:
            if months_active_max <= 1:
                tenure_months = 1
            else:
                mode = min(5, months_active_max - 0.001)
                tenure_months = max(1, int(np.random.triangular(1, mode, months_active_max)))
            end_date = signup_date + pd.DateOffset(months=tenure_months)
            if end_date > TODAY:
                end_date = TODAY
            status = "Cancelled"
        else:
            end_date = pd.NaT
            status = "Active"

        # Occasionally simulate an upgrade/downgrade mid-life as a SECOND subscription row
        change_type = "New"
        rows.append({
            "subscription_id": f"SUB{sub_counter:06d}",
            "customer_id": customer_id,
            "plan_tier": tier,
            "start_date": signup_date.date(),
            "end_date": end_date.date() if pd.notna(end_date) else np.nan,
            "billing_cycle": np.random.choice(["Monthly", "Annual"], p=[0.7, 0.3]),
            "mrr_amount": mrr_amount,
            "status": status,
            "change_type": change_type,
        })
        sub_counter += 1

        # ~18% of still-active customers get an upgrade event later
        if status == "Active" and np.random.random() < 0.18 and tier != "Enterprise":
            upgrade_tier = TIERS[TIERS.index(tier) + 1]
            upgrade_date = signup_date + pd.DateOffset(
                months=np.random.randint(3, max(4, months_active_max)))
            if upgrade_date < TODAY:
                rows.append({
                    "subscription_id": f"SUB{sub_counter:06d}",
                    "customer_id": customer_id,
                    "plan_tier": upgrade_tier,
                    "start_date": upgrade_date.date(),
                    "end_date": np.nan,
                    "billing_cycle": np.random.choice(["Monthly", "Annual"], p=[0.7, 0.3]),
                    "mrr_amount": round(TIER_BASE_MRR[upgrade_tier] * (1 - discount / 100), 2),
                    "status": "Active",
                    "change_type": "Upgrade",
                })
                sub_counter += 1

        # ~8% of active customers get a downgrade event (contraction -- key leakage driver)
        elif status == "Active" and np.random.random() < 0.08 and tier != "Starter":
            downgrade_tier = TIERS[TIERS.index(tier) - 1]
            downgrade_date = signup_date + pd.DateOffset(
                months=np.random.randint(3, max(4, months_active_max)))
            if downgrade_date < TODAY:
                rows.append({
                    "subscription_id": f"SUB{sub_counter:06d}",
                    "customer_id": customer_id,
                    "plan_tier": downgrade_tier,
                    "start_date": downgrade_date.date(),
                    "end_date": np.nan,
                    "billing_cycle": np.random.choice(["Monthly", "Annual"], p=[0.7, 0.3]),
                    "mrr_amount": round(TIER_BASE_MRR[downgrade_tier] * (1 - discount / 100), 2),
                    "status": "Active",
                    "change_type": "Downgrade",
                })
                sub_counter += 1

    df = pd.DataFrame(rows)
    return df


# ----------------------------------------------------------------------------
# 3. INVOICES
# ----------------------------------------------------------------------------
def generate_invoices(subscriptions_df):
    rows = []
    inv_counter = 1

    for _, sub in subscriptions_df.iterrows():
        start = pd.Timestamp(sub["start_date"])
        end = pd.Timestamp(sub["end_date"]) if pd.notna(sub["end_date"]) else TODAY
        mrr = sub["mrr_amount"]

        # Monthly invoices across the active life of the subscription
        current = start
        while current <= end:
            # Failed payment probability -- slightly higher for Starter tier
            # (smaller cards, more personal billing -> more bounces) and for
            # customers in the final 2 months before cancellation (early signal)
            near_cancellation = pd.notna(sub["end_date"]) and (end - current).days <= 60
            fail_p = 0.07 if not near_cancellation else 0.18
            roll = np.random.random()

            if roll < fail_p:
                payment_status = "Failed"
                amount_paid = 0.0
            elif roll < fail_p + 0.02:
                payment_status = "Refunded"
                amount_paid = 0.0
            else:
                payment_status = "Paid"
                amount_paid = mrr

            discount_pct = round(max(0, 100 * (1 - mrr / TIER_BASE_MRR[sub["plan_tier"]])), 1)

            rows.append({
                "invoice_id": f"INV{inv_counter:07d}",
                "subscription_id": sub["subscription_id"],
                "invoice_date": current.date(),
                "amount_due": mrr,
                "amount_paid": amount_paid,
                "payment_status": payment_status,
                "discount_pct": discount_pct,
            })
            inv_counter += 1
            current += pd.DateOffset(months=1)

    df = pd.DataFrame(rows)

    # Inject ~25 duplicate invoice rows (real billing-system glitch pattern)
    dupes = df.sample(n=min(25, len(df) - 1), random_state=SEED)
    df = pd.concat([df, dupes], ignore_index=True)

    return df


# ----------------------------------------------------------------------------
# 4. USAGE_EVENTS
# ----------------------------------------------------------------------------
def generate_usage_events(customers_df, subscriptions_df):
    rows = []
    event_counter = 1

    # one row per customer per active week, with engineered decline before churn
    cust_sub = subscriptions_df.sort_values("start_date").drop_duplicates(
        "customer_id", keep="last")

    for _, sub in cust_sub.iterrows():
        customer_id = sub["customer_id"]
        start = pd.Timestamp(sub["start_date"])
        end = pd.Timestamp(sub["end_date"]) if pd.notna(sub["end_date"]) else TODAY
        will_churn = pd.notna(sub["end_date"])

        base_logins = np.random.randint(8, 40)  # baseline weekly logins for this account
        base_users = np.random.randint(1, 25)

        current = start
        week_idx = 0
        total_weeks = max(1, (end - start).days // 7)

        while current <= end:
            # Decline engineering: in the final 8 weeks before churn, taper usage down
            weeks_remaining = (end - current).days // 7
            if will_churn and weeks_remaining <= 8:
                decay_factor = max(0.15, weeks_remaining / 8)
            else:
                decay_factor = 1.0 + np.random.normal(0, 0.05)  # small natural noise

            login_count = max(0, int(base_logins * decay_factor * np.random.uniform(0.8, 1.2)))
            active_users = max(0, int(base_users * decay_factor * np.random.uniform(0.85, 1.15)))

            rows.append({
                "event_id": f"EVT{event_counter:07d}",
                "customer_id": customer_id,
                "event_date": current.date(),
                "feature_used": random.choice(FEATURES),
                "active_users_count": active_users,
                "login_count": login_count,
            })
            event_counter += 1
            current += timedelta(weeks=1)
            week_idx += 1

    df = pd.DataFrame(rows)
    return df


# ----------------------------------------------------------------------------
# 5. SUPPORT_TICKETS
# ----------------------------------------------------------------------------
def generate_support_tickets(customers_df, subscriptions_df):
    rows = []
    ticket_counter = 1

    cust_sub = subscriptions_df.sort_values("start_date").drop_duplicates(
        "customer_id", keep="last")

    for _, sub in cust_sub.iterrows():
        customer_id = sub["customer_id"]
        start = pd.Timestamp(sub["start_date"])
        end = pd.Timestamp(sub["end_date"]) if pd.notna(sub["end_date"]) else TODAY
        will_churn = pd.notna(sub["end_date"])

        # Number of tickets over the account lifetime (Poisson-ish)
        tenure_months = max(1, (end - start).days // 30)
        n_tickets = np.random.poisson(lam=min(8, tenure_months * 0.4))

        # Engineered pattern: churned accounts get an extra cluster of
        # high-priority, low-CSAT tickets in the final 60 days
        for _ in range(n_tickets):
            created = start + timedelta(days=int(np.random.uniform(0, (end - start).days or 1)))
            priority = np.random.choice(PRIORITIES, p=[0.45, 0.30, 0.18, 0.07])
            csat = np.random.choice([1, 2, 3, 4, 5], p=[0.05, 0.10, 0.20, 0.35, 0.30])
            resolution_hours = int(np.random.exponential(scale=18)) + 1

            rows.append({
                "ticket_id": f"TKT{ticket_counter:07d}",
                "customer_id": customer_id,
                "created_date": created.date(),
                "priority": priority,
                "category": random.choice(TICKET_CATEGORIES),
                "resolution_hours": resolution_hours,
                "csat_score": csat,
            })
            ticket_counter += 1

        if will_churn:
            extra_tickets = np.random.randint(2, 5)
            window_start = max(start, end - timedelta(days=60))
            for _ in range(extra_tickets):
                created = window_start + timedelta(
                    days=int(np.random.uniform(0, max(1, (end - window_start).days))))
                priority = np.random.choice(["High", "Urgent"], p=[0.6, 0.4])
                csat = np.random.choice([1, 2, 3], p=[0.5, 0.35, 0.15])
                resolution_hours = int(np.random.exponential(scale=36)) + 4

                rows.append({
                    "ticket_id": f"TKT{ticket_counter:07d}",
                    "customer_id": customer_id,
                    "created_date": created.date(),
                    "priority": priority,
                    "category": random.choice(["Billing", "Performance Issue", "Bug Report"]),
                    "resolution_hours": resolution_hours,
                    "csat_score": csat,
                })
                ticket_counter += 1

    df = pd.DataFrame(rows)

    # Inject a few out-of-range CSAT scores (data entry error pattern, e.g. 0 or 7)
    bad_idx = df.sample(n=15, random_state=SEED).index
    df.loc[bad_idx, "csat_score"] = np.random.choice([0, 6, 7, -1], size=len(bad_idx))

    return df


# ----------------------------------------------------------------------------
# Messiness pass (nulls in non-critical columns, stray formatting)
# ----------------------------------------------------------------------------
def add_missing_values(df, col, rate=0.02):
    idx = df.sample(frac=rate, random_state=SEED).index
    df.loc[idx, col] = np.nan
    return df


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
def main():
    print("Generating customers...")
    customers = generate_customers()

    print("Generating subscriptions...")
    subscriptions = generate_subscriptions(customers)

    print("Generating invoices...")
    invoices = generate_invoices(subscriptions)

    print("Generating usage events...")
    usage_events = generate_usage_events(customers, subscriptions)

    print("Generating support tickets...")
    support_tickets = generate_support_tickets(customers, subscriptions)

    # Inject a few stray missing values in non-critical fields
    customers = add_missing_values(customers, "industry", rate=0.015)
    usage_events = add_missing_values(usage_events, "feature_used", rate=0.02)
    support_tickets = add_missing_values(support_tickets, "resolution_hours", rate=0.02)

    # A handful of invoice amounts saved as text with a stray currency symbol
    # (simulates an export glitch -- forces a real cleaning step in Phase 2)
    str_idx = invoices.sample(n=10, random_state=SEED).index
    invoices["amount_due"] = invoices["amount_due"].astype(object)
    invoices.loc[str_idx, "amount_due"] = invoices.loc[str_idx, "amount_due"].apply(
        lambda x: f"${x}")

    # Save
    customers.to_csv(f"{OUT_DIR}/customers.csv", index=False)
    subscriptions.to_csv(f"{OUT_DIR}/subscriptions.csv", index=False)
    invoices.to_csv(f"{OUT_DIR}/invoices.csv", index=False)
    usage_events.to_csv(f"{OUT_DIR}/usage_events.csv", index=False)
    support_tickets.to_csv(f"{OUT_DIR}/support_tickets.csv", index=False)

    print("\n--- Row counts ---")
    print(f"customers:       {len(customers):,}")
    print(f"subscriptions:   {len(subscriptions):,}")
    print(f"invoices:        {len(invoices):,}")
    print(f"usage_events:    {len(usage_events):,}")
    print(f"support_tickets: {len(support_tickets):,}")
    total = len(customers) + len(subscriptions) + len(invoices) + len(usage_events) + len(support_tickets)
    print(f"TOTAL ROWS:      {total:,}")
    print(f"\nFiles written to: {OUT_DIR}")


if __name__ == "__main__":
    main()
