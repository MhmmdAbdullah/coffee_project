import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

# ══════════════════════════════════════════════════════════
# LOAD ENV
# ══════════════════════════════════════════════════════════
load_dotenv()

LOCAL_URL = os.getenv("LOCAL_DB_URL")
SUPABASE_URL = os.getenv("SUPABASE_DB_URL")

print("LOCAL DB    :", LOCAL_URL)
print("SUPABASE DB :", SUPABASE_URL)

engine_local = create_engine(LOCAL_URL)
engine_supabase = create_engine(SUPABASE_URL)

# ══════════════════════════════════════════════════════════
# STEP 1 — LOAD CSV
# ══════════════════════════════════════════════════════════
print("\n[1] Loading CSV files...")

df_orders = pd.read_csv("data/orders.csv")
df_customers = pd.read_csv("data/customers.csv")
df_products = pd.read_csv("data/products.csv")

print(f"Orders    : {df_orders.shape}")
print(f"Customers : {df_customers.shape}")
print(f"Products  : {df_products.shape}")

# ══════════════════════════════════════════════════════════
# STEP 2 — CLEANING
# ══════════════════════════════════════════════════════════
print("\n[2] Cleaning data...")

# ─────────────────────────────────────────────────────────
# CLEAN COLUMN NAMES
# ─────────────────────────────────────────────────────────
df_orders.columns = [c.strip() for c in df_orders.columns]
df_customers.columns = [c.strip() for c in df_customers.columns]
df_products.columns = [c.strip() for c in df_products.columns]

# ─────────────────────────────────────────────────────────
# ORDERS CLEANING
# ─────────────────────────────────────────────────────────

# DATE
df_orders["Order Date"] = pd.to_datetime(
    df_orders["Order Date"],
    errors="coerce"
)

# EMAIL
df_orders["Email"] = (
    df_orders["Email"]
    .replace("0", np.nan)
    .replace("", np.nan)
)

# NUMERIC
numeric_cols = [
    "Quantity",
    "Unit Price",
    "Sales",
    "Size"
]

for col in numeric_cols:
    df_orders[col] = pd.to_numeric(
        df_orders[col],
        errors="coerce"
    )

# PROFIT
df_orders["Profit"] = pd.to_numeric(
    df_orders["Profit"]
    .astype(str)
    .str.replace(",", "")
    .str.strip(),
    errors="coerce"
).fillna(0)

# PROFIT MARGIN
df_orders["Profit Margin"] = (
    df_orders["Profit Margin"]
    .astype(str)
    .str.replace("%", "")
    .str.strip()
)

df_orders["Profit Margin"] = pd.to_numeric(
    df_orders["Profit Margin"],
    errors="coerce"
).fillna(0)

mask = df_orders["Profit Margin"] > 1

df_orders.loc[mask, "Profit Margin"] = (
    df_orders.loc[mask, "Profit Margin"] / 100
)

# REMOVE NULL DATE
df_orders = df_orders.dropna(subset=["Order Date"])

print("\nYear distribution:")
print(df_orders["Order Date"].dt.year.value_counts().sort_index())

print("\nNull dates:")
print(df_orders["Order Date"].isna().sum())

# ─────────────────────────────────────────────────────────
# CUSTOMERS CLEANING
# ─────────────────────────────────────────────────────────
df_customers["Email"] = (
    df_customers["Email"]
    .replace("", np.nan)
)

df_customers["Phone Number"] = (
    df_customers["Phone Number"]
    .replace("", np.nan)
)

# ─────────────────────────────────────────────────────────
# PRODUCTS CLEANING
# ─────────────────────────────────────────────────────────
product_numeric_cols = [
    "Unit Price",
    "Price per 100g",
    "Profit"
]

for col in product_numeric_cols:
    df_products[col] = pd.to_numeric(
        df_products[col],
        errors="coerce"
    )

# ══════════════════════════════════════════════════════════
# STEP 3 — BUILD DIMENSIONS
# ══════════════════════════════════════════════════════════
print("\n[3] Building dimensions...")

# ─────────────────────────────────────────────────────────
# DIM CUSTOMER
# ─────────────────────────────────────────────────────────
dim_customer = (
    df_customers[
        [
            "Customer ID",
            "Customer Name",
            "Email",
            "Phone Number",
            "Address Line 1",
            "City",
            "Country",
            "Postcode",
            "Loyalty Card"
        ]
    ]
    .drop_duplicates()
)

dim_customer.columns = [
    "customer_id",
    "customer_name",
    "email",
    "phone_number",
    "address_line1",
    "city",
    "country",
    "postcode",
    "loyalty_card"
]

# ─────────────────────────────────────────────────────────
# DIM PRODUCT
# ─────────────────────────────────────────────────────────
coffee_map = {
    "Ara": "Arabica",
    "Rob": "Robusta",
    "Lib": "Liberica",
    "Exc": "Excelsa"
}

roast_map = {
    "L": "Light",
    "M": "Medium",
    "D": "Dark"
}

dim_product = (
    df_products[
        [
            "Product ID",
            "Coffee Type",
            "Roast Type",
            "Size",
            "Unit Price",
            "Price per 100g",
            "Profit"
        ]
    ]
    .drop_duplicates()
)

dim_product["coffee_name"] = (
    dim_product["Coffee Type"]
    .map(coffee_map)
)

dim_product["roast_name"] = (
    dim_product["Roast Type"]
    .map(roast_map)
)

dim_product.columns = [
    "product_id",
    "coffee_type",
    "roast_type",
    "size_kg",
    "unit_price",
    "price_per_100g",
    "profit_per_unit",
    "coffee_name",
    "roast_name"
]

dim_product = dim_product[
    [
        "product_id",
        "coffee_type",
        "coffee_name",
        "roast_type",
        "roast_name",
        "size_kg",
        "unit_price",
        "price_per_100g",
        "profit_per_unit"
    ]
]

# ─────────────────────────────────────────────────────────
# DIM LOCATION
# ─────────────────────────────────────────────────────────
dim_location = pd.DataFrame({
    "country": [
        "United States",
        "Ireland",
        "United Kingdom"
    ],
    "region": [
        "North America",
        "Northern Europe",
        "Northern Europe"
    ],
    "continent": [
        "Americas",
        "Europe",
        "Europe"
    ]
})

# ─────────────────────────────────────────────────────────
# DIM DATE
# ─────────────────────────────────────────────────────────
dates = pd.DataFrame({
    "full_date": df_orders["Order Date"].dt.date.unique()
})

dates["full_date"] = pd.to_datetime(dates["full_date"])

dates["date_id"] = (
    dates["full_date"]
    .dt.strftime("%Y%m%d")
    .astype(int)
)

dates["day"] = dates["full_date"].dt.day
dates["month"] = dates["full_date"].dt.month
dates["month_name"] = dates["full_date"].dt.month_name()
dates["quarter"] = dates["full_date"].dt.quarter
dates["year"] = dates["full_date"].dt.year
dates["weekday"] = dates["full_date"].dt.day_name()
dates["is_weekend"] = dates["full_date"].dt.dayofweek >= 5

dim_date = dates[
    [
        "date_id",
        "full_date",
        "day",
        "month",
        "month_name",
        "quarter",
        "year",
        "weekday",
        "is_weekend"
    ]
]

# ══════════════════════════════════════════════════════════
# STEP 4 — LOAD DIMENSIONS
# ══════════════════════════════════════════════════════════
print("\n[4] Loading dimensions...")

with engine_local.connect() as conn:

    # CLEAN TABLES
    conn.execute(text("""
        TRUNCATE TABLE
            fact_sales,
            dim_date,
            dim_location,
            dim_customer,
            dim_product
        RESTART IDENTITY CASCADE;
    """))
    conn.commit()

# INSERT DIMENSIONS
dim_customer.to_sql(
    "dim_customer",
    engine_local,
    if_exists="append",
    index=False
)

dim_product.to_sql(
    "dim_product",
    engine_local,
    if_exists="append",
    index=False
)

dim_location.to_sql(
    "dim_location",
    engine_local,
    if_exists="append",
    index=False
)

dim_date.to_sql(
    "dim_date",
    engine_local,
    if_exists="append",
    index=False
)

print("✓ Dimensions loaded")

# ══════════════════════════════════════════════════════════
# STEP 5 — BUILD FACT TABLE
# ══════════════════════════════════════════════════════════
print("\n[5] Building fact table...")

with engine_local.connect() as conn:

    customer_lookup = pd.read_sql(
        "SELECT customer_sk, customer_id FROM dim_customer",
        conn
    )

    product_lookup = pd.read_sql(
        "SELECT product_sk, product_id FROM dim_product",
        conn
    )

    location_lookup = pd.read_sql(
        "SELECT location_id, country FROM dim_location",
        conn
    )

# MERGE LOOKUPS
fact_sales = (
    df_orders
    .merge(customer_lookup,
           left_on="Customer ID",
           right_on="customer_id",
           how="left")
    .merge(product_lookup,
           left_on="Product ID",
           right_on="product_id",
           how="left")
    .merge(location_lookup,
           left_on="Country",
           right_on="country",
           how="left")
)

fact_sales["date_id"] = (
    fact_sales["Order Date"]
    .dt.strftime("%Y%m%d")
    .astype(int)
)

fact_sales = fact_sales[
    [
        "Order ID",
        "date_id",
        "customer_sk",
        "product_sk",
        "location_id",
        "Quantity",
        "Unit Price",
        "Sales",
        "Profit",
        "Profit Margin"
    ]
]

fact_sales.columns = [
    "order_id",
    "date_id",
    "customer_sk",
    "product_sk",
    "location_id",
    "quantity",
    "unit_price",
    "sales_amount",
    "profit",
    "profit_margin"
]

print(f"Fact rows: {len(fact_sales)}")

# INSERT FACT
fact_sales.to_sql(
    "fact_sales",
    engine_local,
    if_exists="append",
    index=False
)

print("✓ Fact table loaded")

# ══════════════════════════════════════════════════════════
# STEP 6 — VALIDATION
# ══════════════════════════════════════════════════════════
print("\n[6] Validation...")

with engine_local.connect() as conn:

    tables = [
        "dim_date",
        "dim_location",
        "dim_customer",
        "dim_product",
        "fact_sales"
    ]

    for tbl in tables:
        count = conn.execute(
            text(f"SELECT COUNT(*) FROM {tbl}")
        ).scalar()

        print(f"{tbl}: {count} rows")

    print("\nSales by year:")

    result = conn.execute(text("""
        SELECT
            d.year,
            COUNT(*) AS total_rows,
            ROUND(SUM(f.sales_amount)::numeric, 2) AS total_sales
        FROM fact_sales f
        JOIN dim_date d
            ON f.date_id = d.date_id
        GROUP BY d.year
        ORDER BY d.year;
    """))

    for row in result:
        print(row)

# ══════════════════════════════════════════════════════════
# STEP 7 — SYNC TO SUPABASE
# ══════════════════════════════════════════════════════════
print("\n[7] Syncing to Supabase...")

with engine_supabase.connect() as conn:

    conn.execute(text("""
        TRUNCATE TABLE
            fact_sales,
            dim_date,
            dim_location,
            dim_customer,
            dim_product
        RESTART IDENTITY CASCADE;
    """))

    conn.commit()

tables = [
    "dim_date",
    "dim_location",
    "dim_customer",
    "dim_product",
    "fact_sales"
]

with engine_local.connect() as src:

    for tbl in tables:

        df_tbl = pd.read_sql(
            f"SELECT * FROM {tbl}",
            src
        )

        df_tbl.to_sql(
            tbl,
            engine_supabase,
            if_exists="append",
            index=False
        )

        print(f"✓ {tbl}: {len(df_tbl)} rows synced")

print("\n✅ PIPELINE COMPLETE")