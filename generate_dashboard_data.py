import pandas as pd
import json
import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()
engine = create_engine(os.getenv('LOCAL_DB_URL'))

print("Fetching data from PostgreSQL...")

query = """
    SELECT
        f.order_id        AS "orderId",
        c.customer_id     AS "customerId",
        c.customer_name   AS "customerName",
        c.country         AS "country",
        c.city            AS "city",
        c.postcode        AS "postcode",
        c.loyalty_card    AS "loyaltyCard",
        p.coffee_name     AS "coffee",
        p.roast_name      AS "roast",
        p.size_kg         AS "size",
        f.quantity        AS "qty",
        f.unit_price      AS "unitPrice",
        p.price_per_100g  AS "per100g",
        f.sales_amount    AS "sales",
        f.profit          AS "profit",
        f.profit_margin   AS "margin",
        d.year            AS "year",
        d.month           AS "month",
        TO_CHAR(d.full_date, 'Mon') AS "monthName"
    FROM fact_sales f
    JOIN dim_date     d ON f.date_id     = d.date_id
    JOIN dim_customer c ON f.customer_sk = c.customer_sk
    JOIN dim_product  p ON f.product_sk  = p.product_sk
    JOIN dim_location l ON f.location_id = l.location_id
    ORDER BY d.full_date
"""

df = pd.read_sql(query, engine)
print(f"✓ {len(df)} rows fetched")

# Convert ke list of dicts
rows = []
for _, r in df.iterrows():
    rows.append({
        'orderId':      r['orderId'],
        'customerId':   r['customerId'],
        'customerName': r['customerName'],
        'country':      r['country'],
        'city':         str(r['city'])      if pd.notna(r['city'])      else '',
        'postcode':     str(r['postcode'])  if pd.notna(r['postcode'])  else '',
        'loyaltyCard':  str(r['loyaltyCard']) if pd.notna(r['loyaltyCard']) else 'No',
        'coffee':       r['coffee'],
        'roast':        r['roast'],
        'size':         float(r['size']),
        'qty':          int(r['qty']),
        'unitPrice':    round(float(r['unitPrice']), 4),
        'per100g':      round(float(r['per100g']), 4) if pd.notna(r['per100g']) else 0,
        'sales':        round(float(r['sales']), 2),
        'profit':       round(float(r['profit']), 4),
        'margin':       round(float(r['margin']), 4),
        'year':         int(r['year']),
        'month':        int(r['month']),
        'monthName':    r['monthName']
    })

print(f"✓ {len(rows)} rows converted")

# Save JSON backup
with open('dashboard_data.json', 'w', encoding='utf-8') as f:
    json.dump(rows, f, ensure_ascii=False)
print("✓ dashboard_data.json saved")

# ── Inject ke HTML ────────────────────────────────────────
print("Injecting into dashboard HTML...")

html_path = 'dashboard/dashboard_coffee.html'
with open(html_path, 'r', encoding='utf-8') as f:
    html = f.read()

start_marker = 'const RAW = '
end_marker   = '];\n\nlet charts'

start_idx = html.find(start_marker)
end_idx   = html.find(end_marker)

if start_idx == -1 or end_idx == -1:
    print("ERROR: Marker tidak ditemukan di HTML!")
    print(f"  start_marker found: {start_idx != -1}")
    print(f"  end_marker found  : {end_idx != -1}")
else:
    new_data = 'const RAW = ' + json.dumps(rows, ensure_ascii=False) + ';'
    html_new = html[:start_idx] + new_data + '\n\nlet charts' + html[end_idx + len(end_marker):]

    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_new)

    print("✓ Dashboard updated with fresh database data!")
    print(f"  Total Sales : ${sum(r['sales'] for r in rows):,.2f}")
    print(f"  Total Profit: ${sum(r['profit'] for r in rows):,.2f}")
    print(f"  Total Rows  : {len(rows)}")