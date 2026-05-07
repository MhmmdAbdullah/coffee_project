import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from urllib.parse import quote_plus
import os

load_dotenv()

# ── KONEKSI ───────────────────────────────────────────────
LOCAL_URL    = os.getenv('LOCAL_DB_URL')
supabase_raw = os.getenv('SUPABASE_DB_URL')

print("LOCAL URL   :", LOCAL_URL)
print("SUPABASE URL:", supabase_raw)

engine_local    = create_engine(LOCAL_URL)
engine_supabase = create_engine(supabase_raw)

# ══════════════════════════════════════════════════════════
# STEP 1: LOAD CSV
# ══════════════════════════════════════════════════════════
print("\nLoading CSV files...")
df_orders    = pd.read_csv('data/orders.csv')
df_customers = pd.read_csv('data/customers.csv')
df_products  = pd.read_csv('data/products.csv')

# ══════════════════════════════════════════════════════════
# STEP 2: CLEANING
# ══════════════════════════════════════════════════════════
print("Cleaning data...")

# ── ORDERS ────────────────────────────────────────────────
df_orders.columns = [c.strip() for c in df_orders.columns]

# Fix Order Date → datetime
df_orders['Order Date'] = pd.to_datetime(df_orders['Order Date'], errors='coerce')

# Fix Email kosong
df_orders['Email'] = df_orders['Email'].replace('0', np.nan)
df_orders['Email'] = df_orders['Email'].replace('', np.nan)

# Fix Profit — ada yang string, ada yang angka
df_orders['Profit'] = pd.to_numeric(
    df_orders['Profit'].astype(str).str.replace(',', '').str.strip(),
    errors='coerce'
)

# Fix Profit Margin — format "6%" → 0.06
df_orders['Profit Margin'] = (
    df_orders['Profit Margin']
    .astype(str)
    .str.replace('%', '')
    .str.strip()
)
df_orders['Profit Margin'] = pd.to_numeric(df_orders['Profit Margin'], errors='coerce')
# Kalau nilainya > 1 berarti masih persen (misal 6 bukan 0.06)
mask = df_orders['Profit Margin'] > 1
df_orders.loc[mask, 'Profit Margin'] = df_orders.loc[mask, 'Profit Margin'] / 100

# Fix Profit — hapus null, isi 0
df_orders['Profit'] = pd.to_numeric(
    df_orders['Profit'].astype(str).str.replace(',', '').str.strip(),
    errors='coerce'
).fillna(0)  # ← tambah .fillna(0) di sini

# Fix Quantity & Size → numeric
df_orders['Quantity']   = pd.to_numeric(df_orders['Quantity'],   errors='coerce').fillna(0).astype(int)
df_orders['Unit Price'] = pd.to_numeric(df_orders['Unit Price'], errors='coerce')
df_orders['Sales']      = pd.to_numeric(df_orders['Sales'],      errors='coerce')
df_orders['Size']       = pd.to_numeric(df_orders['Size'],       errors='coerce')

# ── CUSTOMERS ─────────────────────────────────────────────
df_customers.columns = [c.strip() for c in df_customers.columns]
df_customers['Email']        = df_customers['Email'].replace('', np.nan)
df_customers['Phone Number'] = df_customers['Phone Number'].replace('', np.nan)

# ── PRODUCTS ──────────────────────────────────────────────
df_products.columns = [c.strip() for c in df_products.columns]
df_products['Unit Price']     = pd.to_numeric(df_products['Unit Price'],     errors='coerce')
df_products['Price per 100g'] = pd.to_numeric(df_products['Price per 100g'], errors='coerce')
df_products['Profit']         = pd.to_numeric(df_products['Profit'],         errors='coerce')

# ── MERGE semua ───────────────────────────────────────────
df = df_orders.merge(
    df_customers[['Customer ID','Phone Number','Address Line 1','City','Postcode','Loyalty Card']],
    on='Customer ID', how='left'
).merge(
    df_products[['Product ID','Price per 100g']].rename(columns={'Price per 100g':'price_per_100g'}),
    on='Product ID', how='left'
)

coffee_map = {'Rob':'Robusta','Exc':'Excelsa','Lib':'Liberica','Ara':'Arabica'}
roast_map  = {'M':'Medium','L':'Light','D':'Dark'}
df['coffee_name'] = df['Coffee Type'].map(coffee_map)
df['roast_name']  = df['Roast Type'].map(roast_map)
df['year']        = df['Order Date'].dt.year
df['month']       = df['Order Date'].dt.month

print(f"  ✓ Merged: {df.shape[0]} rows × {df.shape[1]} cols")

# Drop baris yang order_date null (tidak bisa masuk dim_date)
df_orders_clean = df_orders.dropna(subset=['Order Date']).copy()
print(f"  ✓ Valid order dates: {len(df_orders_clean)} rows")

# ══════════════════════════════════════════════════════════
# STEP 3: LOAD KE LOCAL POSTGRESQL (DOCKER)
# ══════════════════════════════════════════════════════════
print("\nLoading to local PostgreSQL (Docker)...")

# Load staging tables
df_customers.to_sql('stg_customers', engine_local, if_exists='replace', index=False)
df_orders_clean.to_sql('stg_orders', engine_local, if_exists='replace', index=False)
df_products.to_sql('stg_products', engine_local, if_exists='replace', index=False)
print("  ✓ Staging tables loaded")

with engine_local.connect() as conn:

    # ── Populate dim_customer ────────────────────────────
    conn.execute(text("""
        INSERT INTO dim_customer
          (customer_id, customer_name, email, phone_number,
           address_line1, city, country, postcode, loyalty_card)
        SELECT
            "Customer ID",
            "Customer Name",
            NULLIF("Email", ''),
            NULLIF("Phone Number", ''),
            "Address Line 1",
            "City",
            "Country",
            "Postcode"::text,
            "Loyalty Card"
        FROM stg_customers
        ON CONFLICT (customer_id) DO NOTHING;
    """))
    conn.commit()
    print("  ✓ dim_customer populated")

    # ── Populate dim_product ─────────────────────────────
    conn.execute(text("""
        INSERT INTO dim_product
          (product_id, coffee_type, coffee_name, roast_type, roast_name,
           size_kg, unit_price, price_per_100g, profit_per_unit)
        SELECT
            "Product ID",
            "Coffee Type",
            CASE "Coffee Type"
                WHEN 'Ara' THEN 'Arabica'
                WHEN 'Rob' THEN 'Robusta'
                WHEN 'Lib' THEN 'Liberica'
                WHEN 'Exc' THEN 'Excelsa'
            END,
            "Roast Type",
            CASE "Roast Type"
                WHEN 'M' THEN 'Medium'
                WHEN 'L' THEN 'Light'
                WHEN 'D' THEN 'Dark'
            END,
            "Size"::numeric,
            "Unit Price"::numeric,
            "Price per 100g"::numeric,
            "Profit"::numeric
        FROM stg_products
        ON CONFLICT (product_id) DO NOTHING;
    """))
    conn.commit()
    print("  ✓ dim_product populated")

    # ── Populate dim_location ────────────────────────────
    conn.execute(text("""
        INSERT INTO dim_location (country, region, continent)
        VALUES
            ('United States', 'North America',   'Americas'),
            ('Ireland',       'Northern Europe', 'Europe'),
            ('United Kingdom','Northern Europe', 'Europe')
        ON CONFLICT (country) DO NOTHING;
    """))
    conn.commit()
    print("  ✓ dim_location populated")

    # ── Populate dim_date ────────────────────────────────
    conn.execute(text("""
        INSERT INTO dim_date
          (date_id, full_date, day, month, month_name,
           quarter, year, weekday, is_weekend)
        SELECT DISTINCT
            CAST(TO_CHAR("Order Date"::date, 'YYYYMMDD') AS INT),
            "Order Date"::date,
            EXTRACT(DAY     FROM "Order Date"::date)::INT,
            EXTRACT(MONTH   FROM "Order Date"::date)::INT,
            TO_CHAR("Order Date"::date, 'Month'),
            EXTRACT(QUARTER FROM "Order Date"::date)::INT,
            EXTRACT(YEAR    FROM "Order Date"::date)::INT,
            TO_CHAR("Order Date"::date, 'Day'),
            CASE WHEN EXTRACT(DOW FROM "Order Date"::date) IN (0,6)
                 THEN TRUE ELSE FALSE END
        FROM stg_orders
        WHERE "Order Date" IS NOT NULL
        ON CONFLICT (date_id) DO NOTHING;
    """))
    conn.commit()
    print("  ✓ dim_date populated")

    # ── Populate fact_sales ──────────────────────────────
    conn.execute(text("""
    INSERT INTO fact_sales
      (order_id, date_id, customer_sk, product_sk, location_id,
       quantity, unit_price, sales_amount, profit, profit_margin)
    SELECT
        o."Order ID",
        CAST(TO_CHAR(o."Order Date"::date, 'YYYYMMDD') AS INT),
        c.customer_sk,
        p.product_sk,
        l.location_id,
        o."Quantity"::numeric,
        o."Unit Price"::numeric,
        o."Sales"::numeric,
        COALESCE(o."Profit"::numeric, 0),
        COALESCE(o."Profit Margin"::numeric, 0)
    FROM stg_orders o
    JOIN dim_customer c ON o."Customer ID"  = c.customer_id
    JOIN dim_product  p ON o."Product ID"   = p.product_id
    JOIN dim_location l ON o."Country"      = l.country
    JOIN dim_date     d ON d.full_date       = o."Order Date"::date
    ON CONFLICT DO NOTHING;
"""))
    conn.commit()
    print("  ✓ fact_sales populated")

# Verifikasi row counts
with engine_local.connect() as conn:
    for tbl in ['dim_date','dim_location','dim_customer','dim_product','fact_sales']:
        count = conn.execute(text(f"SELECT COUNT(*) FROM {tbl}")).scalar()
        print(f"     {tbl}: {count} rows")

# ══════════════════════════════════════════════════════════
# STEP 4: SYNC KE SUPABASE
# ══════════════════════════════════════════════════════════
print("\nSyncing to Supabase...")

tables = ['dim_date','dim_location','dim_customer','dim_product','fact_sales']
with engine_local.connect() as src:
    for tbl in tables:
        df_tbl = pd.read_sql(f"SELECT * FROM {tbl}", src)
        df_tbl.to_sql(tbl, engine_supabase, if_exists='replace', index=False)
        print(f"  ✓ {tbl}: {len(df_tbl)} rows synced")

print("\n✅ Pipeline complete! Data available on Supabase.")