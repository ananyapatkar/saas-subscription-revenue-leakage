# SaaS Subscription Revenue Leakage & Customer Churn Intelligence

An end-to-end Data Analytics project that replicates a real-world analytics workflow inside a B2B SaaS company. Starting with synthetic data generation, the project progresses through data cleaning, financial reconciliation, SQL-based business analysis, exploratory data analysis (EDA), and an executive Power BI dashboard to identify revenue leakage and customer churn drivers.

The project demonstrates how data analysts transform raw operational data into actionable business insights for Finance, Customer Success, and Executive Leadership.

---

# Business Problem

**Northbeam Analytics** (fictional B2B SaaS company) provides project management software through three subscription plans:

* Starter
* Growth
* Enterprise

The company serves approximately **3,000 customers** and generates nearly **$10.8M Annual Recurring Revenue (ARR)**.

Over six consecutive quarters, **Net Revenue Retention (NRR)** declined from **112% to 96%**, indicating that revenue lost from existing customers exceeded expansion revenue.

Leadership lacked visibility into the root causes of revenue loss and needed answers to questions such as:

* Is revenue leaking through customer churn, plan downgrades, or failed payments?
* Which customer segments are most likely to churn?
* Does assigning a Customer Success Manager improve retention?
* Can declining product usage predict churn before cancellation?
* Which active customers require immediate intervention?

---

# Project Workflow

```text
Synthetic Data Generation (Python)
            │
            ▼
Data Cleaning & Validation
            │
            ▼
Financial Reconciliation (Excel)
            │
            ▼
MySQL Relational Database
            │
            ▼
SQL Business Analysis
            │
            ▼
Power BI Executive Dashboard
            │
            ▼
Business Recommendations
```

---

# Project Highlights

* Generated a realistic SaaS dataset containing **182,000+ records** across five relational tables.
* Built a normalized MySQL database using primary and foreign key relationships.
* Cleaned and validated data using Python while enforcing referential integrity.
* Performed financial reconciliation in Excel to verify billed versus collected revenue.
* Developed SQL queries for KPI reporting, revenue waterfalls, churn diagnostics, cohort analysis, and customer risk identification.
* Built an interactive Power BI dashboard tailored for executives and Customer Success teams.
* Delivered business recommendations backed by quantified financial impact.

---

# Tech Stack

| Technology | Purpose                                         |
| ---------- | ----------------------------------------------- |
| Python     | Data generation, cleaning, validation, EDA      |
| MySQL      | Data modeling and business analysis             |
| Excel      | Revenue reconciliation and financial validation |
| Power BI   | Executive dashboards and KPI reporting          |
| Pandas     | Data manipulation                               |
| NumPy      | Synthetic data generation                       |                             
| Faker      | Synthetic customer generation                   |

---

# Dataset

The project uses a fully synthetic dataset consisting of approximately **182,000 records**.

| Table           | Description                                   |
| --------------- | --------------------------------------------- |
| customers       | Customer profile and firmographic information |
| subscriptions   | Subscription lifecycle and revenue            |
| invoices        | Billing, collections and payment status       |
| usage_events    | Product engagement metrics                    |
| support_tickets | Customer support interactions                 |

---

# Financial Reconciliation

To ensure analytical accuracy, a separate Excel-based reconciliation process was performed before dashboard development.

The reconciliation validates:

* Total invoices generated
* Total revenue billed
* Total revenue collected
* Monthly revenue leakage
* Revenue gap caused by failed and refunded invoices

This mirrors a common finance validation process used before publishing executive dashboards and KPI reports.

---

# SQL Analysis

Business analysis was performed using MySQL across multiple SQL scripts.

Key analyses include:

* ARR and MRR calculations
* Net Revenue Retention (NRR)
* Gross Revenue Retention (GRR)
* Revenue Waterfall Analysis
* Customer Churn Diagnostics
* Cohort Analysis
* Collection Rate
* Customer Risk Ranking
* Weekly Customer Success Action List

---

# Power BI Dashboard

The project includes an interactive executive dashboard designed for Finance and Customer Success stakeholders.

Executive KPIs
Annual Recurring Revenue
Active Customers
Logo Churn Rate
Collection Rate
Average Customer Satisfaction (CSAT)
Revenue Analytics
MRR Trend by Plan Tier
New MRR by Subscription Change Type
Revenue Lost by Plan Tier
Monthly Revenue Gap
Collection Rate Trend
Customer Analytics
Churn Rate by Industry
Ticket Priority Distribution
Feature Adoption Analysis

Interactive filters and cross-highlighting allow users to explore performance across customer segments and subscription plans.

----


# Key Business Insights

### Customer Success Managers Reduce Churn

Enterprise customers without a dedicated Customer Success Manager churn at more than twice the rate of customers with assigned CSMs.

---

### Failed Payments Drive Revenue Leakage

Failed and refunded invoices consistently create an 8–11% monthly revenue gap independent of customer churn.

---

### Product Usage Predicts Churn

Customer engagement declines significantly during the weeks leading up to cancellation, providing an opportunity for proactive intervention.

---

### Support Experience Influences Retention

Low customer satisfaction scores and high-priority support tickets are strongly associated with increased churn.

---

# Skills Demonstrated

* Data Cleaning & Validation
* Data Modeling
* SQL Analytics
* KPI Development
* Revenue Analysis
* Customer Churn Analysis
* Financial Reconciliation
* Power BI Dashboard Development
* DAX Measures
* Business Storytelling
* Executive Reporting

---

# Repository Structure

```text
python/
sql/
dashboard/
data/
excel/
README.md
```

---

# How to Run

1. Generate synthetic data using Python.
2. Clean and validate all datasets.
3. Perform Excel revenue reconciliation.
4. Create the MySQL schema and import cleaned CSV files.
5. Execute SQL analysis scripts.
6. Open the Power BI dashboard.

---

# Business Value

This project simulates the responsibilities of a Data Analyst within a SaaS organization by combining data engineering, SQL analysis, financial validation, exploratory analytics, and executive dashboarding into a complete business intelligence solution.

It demonstrates not only technical proficiency but also the ability to translate data into actionable recommendations that improve customer retention and revenue performance.
