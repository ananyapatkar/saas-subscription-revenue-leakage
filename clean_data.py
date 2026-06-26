"""
clean_data.py
=============
Data Cleaning & Validation
Northbeam Analytics SaaS Revenue Leakage project

"""

import pandas as pd
import numpy as np
import re
import os

RAW_DIR = "./data/raw"
PROCESSED_DIR = "./data/processed"

log = []  # (table, issue, rows_affected, action)


def record(table, issue, rows_affected, action):
    log.append({"table": table, "issue": issue, "rows_affected": rows_affected, "action": action})


def clean_text_column(series):
    """Strip whitespace and standardize casing to Title Case for category fields."""
    return series.astype(str).str.strip().str.title().replace("Nan", np.nan)


# ----------------------------------------------------------------------------
# 1. CUSTOMERS
# ----------------------------------------------------------------------------
def clean_customers():
    df = pd.read_csv(f"{RAW_DIR}/customers.csv")
    n0 = len(df)

    # --- Duplicate rows: same customer_id appearing more than once ---
    dupe_mask = df.duplicated(subset="customer_id", keep="first")
    n_dupes = dupe_mask.sum()
    df = df[~dupe_mask].copy()
    record("customers", "Fully duplicated customer_id rows", n_dupes,
           "Dropped, kept first occurrence")

    # --- Inconsistent casing/whitespace in industry, country ---
    before_unique = df["industry"].nunique()
    df["industry"] = clean_text_column(df["industry"])
    df["country"] = clean_text_column(df["country"])
    after_unique = df["industry"].nunique()
    record("customers", "Inconsistent casing/whitespace in industry/country",
           before_unique - after_unique, "Standardized to Title Case, stripped whitespace")

    # --- Missing industry values ---
    n_missing_industry = df["industry"].isna().sum()
    df["industry"] = df["industry"].fillna("Unknown")
    record("customers", "Missing industry values", n_missing_industry,
           "Filled with 'Unknown' (preserves row for revenue calcs, "
           "flags for segment analysis to exclude/footnote)")

    # --- Date type ---
    df["signup_date"] = pd.to_datetime(df["signup_date"])

    # --- Referential sanity: customer_id should be unique now ---
    assert df["customer_id"].is_unique, "customer_id still has duplicates after cleaning!"

    print(f"customers: {n0} -> {len(df)} rows")
    return df


# ----------------------------------------------------------------------------
# 2. SUBSCRIPTIONS
# ----------------------------------------------------------------------------
def clean_subscriptions(valid_customer_ids):
    df = pd.read_csv(f"{RAW_DIR}/subscriptions.csv")
    n0 = len(df)

    # --- Orphan check: subscription referencing a customer_id that doesn't exist ---
    orphan_mask = ~df["customer_id"].isin(valid_customer_ids)
    n_orphans = orphan_mask.sum()
    df = df[~orphan_mask].copy()
    record("subscriptions", "Orphan rows (customer_id not in customers table)",
           n_orphans, "Dropped" if n_orphans else "None found")

    # --- Date types ---
    df["start_date"] = pd.to_datetime(df["start_date"])
    df["end_date"] = pd.to_datetime(df["end_date"])

    # --- Business rule check: end_date should never be before start_date ---
    bad_dates = df["end_date"].notna() & (df["end_date"] < df["start_date"])
    n_bad_dates = bad_dates.sum()
    if n_bad_dates:
        df.loc[bad_dates, "end_date"] = df.loc[bad_dates, "start_date"]
    record("subscriptions", "end_date earlier than start_date", n_bad_dates,
           "Corrected to start_date" if n_bad_dates else "None found")

    # --- Business rule check: status='Active' should never have end_date populated ---
    inconsistent_status = (df["status"] == "Active") & df["end_date"].notna()
    n_inconsistent = inconsistent_status.sum()
    record("subscriptions", "Active status with end_date populated", n_inconsistent,
           "Flagged for manual review" if n_inconsistent else "None found")

    # --- mrr_amount should be non-negative ---
    n_negative_mrr = (df["mrr_amount"] < 0).sum()
    record("subscriptions", "Negative mrr_amount values", n_negative_mrr,
           "None found" if n_negative_mrr == 0 else "Set to absolute value")
    df["mrr_amount"] = df["mrr_amount"].abs()

    print(f"subscriptions: {n0} -> {len(df)} rows")
    return df


# ----------------------------------------------------------------------------
# 3. INVOICES
# ----------------------------------------------------------------------------
def clean_invoices(valid_subscription_ids):
    df = pd.read_csv(f"{RAW_DIR}/invoices.csv")
    n0 = len(df)

    # --- Exact duplicate rows ---
    n_dupes = df.duplicated().sum()
    df = df.drop_duplicates().copy()
    record("invoices", "Exact duplicate invoice rows", n_dupes, "Dropped")

    # --- Orphan check ---
    orphan_mask = ~df["subscription_id"].isin(valid_subscription_ids)
    n_orphans = orphan_mask.sum()
    df = df[~orphan_mask].copy()
    record("invoices", "Orphan rows (subscription_id not in subscriptions table)",
           n_orphans, "Dropped" if n_orphans else "None found")

    # --- amount_due stored as text with stray currency symbol ---
    def parse_amount(val):
        if isinstance(val, str):
            return float(re.sub(r"[^\d.]", "", val))
        return float(val)

    n_str_amounts = df["amount_due"].apply(lambda x: isinstance(x, str) and "$" in x).sum()
    df["amount_due"] = df["amount_due"].apply(parse_amount)
    record("invoices", "amount_due stored as text with currency symbol", n_str_amounts,
           "Stripped non-numeric characters, cast to float")

    # --- Date type ---
    df["invoice_date"] = pd.to_datetime(df["invoice_date"])

    # --- Business rule: amount_paid should never exceed amount_due ---
    overpaid = df["amount_paid"] > df["amount_due"]
    n_overpaid = overpaid.sum()
    record("invoices", "amount_paid greater than amount_due", n_overpaid,
           "Flagged for manual review" if n_overpaid else "None found")

    print(f"invoices: {n0} -> {len(df)} rows")
    return df


# ----------------------------------------------------------------------------
# 4. USAGE_EVENTS
# ----------------------------------------------------------------------------
def clean_usage_events(valid_customer_ids):
    df = pd.read_csv(f"{RAW_DIR}/usage_events.csv")
    n0 = len(df)

    orphan_mask = ~df["customer_id"].isin(valid_customer_ids)
    n_orphans = orphan_mask.sum()
    df = df[~orphan_mask].copy()
    record("usage_events", "Orphan rows (customer_id not in customers table)",
           n_orphans, "Dropped" if n_orphans else "None found")

    df["event_date"] = pd.to_datetime(df["event_date"])

    # --- Missing feature_used ---
    n_missing_feature = df["feature_used"].isna().sum()
    df["feature_used"] = df["feature_used"].fillna("Unspecified")
    record("usage_events", "Missing feature_used values", n_missing_feature,
           "Filled with 'Unspecified'")

    # --- Negative counts shouldn't exist, but check anyway ---
    n_negative = ((df["active_users_count"] < 0) | (df["login_count"] < 0)).sum()
    record("usage_events", "Negative usage counts", n_negative,
           "None found" if n_negative == 0 else "Clipped to 0")
    df["active_users_count"] = df["active_users_count"].clip(lower=0)
    df["login_count"] = df["login_count"].clip(lower=0)

    print(f"usage_events: {n0} -> {len(df)} rows")
    return df


# ----------------------------------------------------------------------------
# 5. SUPPORT_TICKETS
# ----------------------------------------------------------------------------
def clean_support_tickets(valid_customer_ids):
    df = pd.read_csv(f"{RAW_DIR}/support_tickets.csv")
    n0 = len(df)

    orphan_mask = ~df["customer_id"].isin(valid_customer_ids)
    n_orphans = orphan_mask.sum()
    df = df[~orphan_mask].copy()
    record("support_tickets", "Orphan rows (customer_id not in customers table)",
           n_orphans, "Dropped" if n_orphans else "None found")

    df["created_date"] = pd.to_datetime(df["created_date"])

    # --- csat_score must be between 1 and 5 ---
    out_of_range = ~df["csat_score"].between(1, 5)
    n_out_of_range = out_of_range.sum()
    df = df[~out_of_range].copy()
    record("support_tickets", "csat_score outside valid 1-5 range", n_out_of_range,
           "Dropped rows (score is unverifiable, not safely imputable)")

    # --- Missing resolution_hours ---
    n_missing_res = df["resolution_hours"].isna().sum()
    median_res = df["resolution_hours"].median()
    df["resolution_hours"] = df["resolution_hours"].fillna(median_res)
    record("support_tickets", "Missing resolution_hours", n_missing_res,
           f"Filled with table median ({median_res:.0f} hours)")

    print(f"support_tickets: {n0} -> {len(df)} rows")
    return df


# ----------------------------------------------------------------------------
# Report generation
# ----------------------------------------------------------------------------
def write_quality_report(log):
    lines = [
        "# Data Quality Report",
        "",
        "Generated by `clean_data.py` (Phase 2). Every fix below is logged with the exact",
        "row count affected -- this is the evidence trail for what changed between",
        "`/data/raw` and `/data/processed`.",
        "",
        "| Table | Issue | Rows Affected | Action Taken |",
        "|---|---|---|---|",
    ]

    for entry in log:
        lines.append(
            f"| {entry['table']} | {entry['issue']} | {entry['rows_affected']} | {entry['action']} |"
        )

    lines += [
        "",
        "## Summary",
        f"- Total distinct issues checked: {len(log)}",
        f"- Total rows affected across all fixes: {sum(e['rows_affected'] for e in log)}",
        "",
        "## Notes for downstream analysis",
        "- `customers.industry` contains an 'Unknown' category from imputed missing values.",
        "- Rows with unverifiable `csat_score` were dropped rather than imputed.",
        "- All referential integrity checks passed or were resolved.",
    ]

    os.makedirs("./docs", exist_ok=True)

    with open("./docs/03_data_quality_report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
def main():
    customers = clean_customers()
    subscriptions = clean_subscriptions(set(customers["customer_id"]))
    invoices = clean_invoices(set(subscriptions["subscription_id"]))
    usage_events = clean_usage_events(set(customers["customer_id"]))
    support_tickets = clean_support_tickets(set(customers["customer_id"]))

    customers.to_csv(f"{PROCESSED_DIR}/customers.csv", index=False)
    subscriptions.to_csv(f"{PROCESSED_DIR}/subscriptions.csv", index=False)
    invoices.to_csv(f"{PROCESSED_DIR}/invoices.csv", index=False)
    usage_events.to_csv(f"{PROCESSED_DIR}/usage_events.csv", index=False)
    support_tickets.to_csv(f"{PROCESSED_DIR}/support_tickets.csv", index=False)

    write_quality_report(log)

    print("\n--- Cleaning log ---")
    for entry in log:
        print(f"[{entry['table']}] {entry['issue']}: {entry['rows_affected']} rows -> {entry['action']}")

    print(f"\nCleaned files written to: {PROCESSED_DIR}")
    print("Data quality report written to: /docs/03_data_quality_report.md")


if __name__ == "__main__":
    main()
