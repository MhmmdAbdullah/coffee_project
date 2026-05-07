"""
save_mining_results.py
Jalankan data mining dari PostgreSQL → simpan hasil ke Supabase
Jalankan: python save_mining_results.py
"""

import pandas as pd
import numpy as np
import json
import os
import warnings
warnings.filterwarnings('ignore')

from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from urllib.parse import quote_plus

from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.cluster import KMeans
from sklearn.tree import DecisionTreeClassifier
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import (silhouette_score, accuracy_score,
                              r2_score, mean_squared_error,
                              classification_report)
from mlxtend.frequent_patterns import apriori, association_rules
from mlxtend.preprocessing import TransactionEncoder
from itertools import combinations

load_dotenv()
engine_local    = create_engine(os.getenv('LOCAL_DB_URL'))
engine_supabase = create_engine(os.getenv('SUPABASE_DB_URL'))

# ══════════════════════════════════════════════════════════
# LOAD DATA FROM POSTGRESQL
# ══════════════════════════════════════════════════════════
print("Loading data from PostgreSQL...")

query = """
    SELECT
        f.order_id        AS "Order ID",
        c.customer_id     AS "Customer ID",
        c.loyalty_card    AS "Loyalty Card",
        p.coffee_type     AS "Coffee Type",
        p.coffee_name     AS "Coffee Name",
        p.roast_type      AS "Roast Type",
        p.size_kg         AS "Size",
        f.unit_price      AS "Unit Price",
        p.price_per_100g  AS "Price per 100g",
        f.quantity        AS "Quantity",
        f.sales_amount    AS "Sales",
        f.profit          AS "Profit",
        f.profit_margin   AS "Profit Margin",
        c.country         AS "Country",
        d.year            AS "Year",
        d.month           AS "Month"
    FROM fact_sales f
    JOIN dim_date     d ON f.date_id     = d.date_id
    JOIN dim_customer c ON f.customer_sk = c.customer_sk
    JOIN dim_product  p ON f.product_sk  = p.product_sk
    JOIN dim_location l ON f.location_id = l.location_id
"""
df = pd.read_sql(query, engine_local)
print(f"✓ {len(df)} rows loaded")

# Encode
coffee_map = {'Rob':0,'Exc':1,'Lib':2,'Ara':3}
coffee_inv = {v:k for k,v in coffee_map.items()}
le_roast   = LabelEncoder()
le_country = LabelEncoder()
le_loyalty = LabelEncoder()
df['coffee_enc']  = df['Coffee Type'].map(coffee_map)
df['roast_enc']   = le_roast.fit_transform(df['Roast Type'])
df['country_enc'] = le_country.fit_transform(df['Country'])
df['loyalty_enc'] = le_loyalty.fit_transform(df['Loyalty Card'].fillna('No'))

results = {}  # dict untuk simpan semua hasil

# ══════════════════════════════════════════════════════════
# 1. CLUSTERING
# ══════════════════════════════════════════════════════════
print("\n[1/4] Running Clustering...")

cust = df.groupby('Customer ID').agg(
    total_spent  =('Sales','sum'),
    total_orders =('Order ID','count'),
    avg_order    =('Sales','mean'),
    loyalty      =('loyalty_enc','first')
).reset_index()

scaler  = StandardScaler()
X_clust = scaler.fit_transform(cust[['total_spent','total_orders','avg_order','loyalty']])

# Elbow
inertias = {}
for k in range(2,7):
    km_test = KMeans(n_clusters=k, random_state=42, n_init=10)
    km_test.fit(X_clust)
    inertias[k] = round(km_test.inertia_, 2)

km = KMeans(n_clusters=3, random_state=42, n_init=10)
cust['cluster'] = km.fit_predict(X_clust)
sil = silhouette_score(X_clust, cust['cluster'])

cluster_summary = cust.groupby('cluster').agg(
    customer_count=('Customer ID','count'),
    avg_spent     =('total_spent','mean'),
    avg_orders    =('total_orders','mean')
).round(2).reset_index()

# Label tiap cluster
def label_cluster(row):
    if row['avg_spent'] > 100:
        return 'High-Value'
    elif row['avg_orders'] > 2:
        return 'Frequent'
    else:
        return 'Casual'

cluster_summary['label'] = cluster_summary.apply(label_cluster, axis=1)

results['clustering'] = {
    'silhouette_score': round(sil, 4),
    'n_clusters': 3,
    'elbow': inertias,
    'segments': cluster_summary.to_dict('records')
}
print(f"  ✓ Silhouette: {sil:.4f}")

# ══════════════════════════════════════════════════════════
# 2. ASSOCIATION RULES
# ══════════════════════════════════════════════════════════
print("\n[2/4] Running Association Rules...")

basket = (df.groupby(['Order ID','Coffee Type'])['Quantity']
           .sum().unstack(fill_value=0)
           .map(lambda x: 1 if x > 0 else 0))
records = basket.apply(lambda row: list(row[row==1].index), axis=1).tolist()
multi   = [r for r in records if len(r) > 1]

top_rules = []
if len(multi) > 0:
    te     = TransactionEncoder()
    te_arr = te.fit_transform(multi)
    bdf    = pd.DataFrame(te_arr, columns=te.columns_)
    freq   = apriori(bdf, min_support=0.08, use_colnames=True)
    if len(freq) > 0:
        rules = association_rules(freq, metric='lift', min_threshold=0.9)
        rules = rules.sort_values('lift', ascending=False)
        for _, r in rules.head(6).iterrows():
            top_rules.append({
                'antecedent':  ', '.join(list(r['antecedents'])),
                'consequent':  ', '.join(list(r['consequents'])),
                'support':     round(float(r['support']),   3),
                'confidence':  round(float(r['confidence']),3),
                'lift':        round(float(r['lift']),       3)
            })

# Fallback co-occurrence
cooccur = {}
for rec in multi:
    for pair in combinations(sorted(rec), 2):
        cooccur[pair] = cooccur.get(pair, 0) + 1
top_cooccur = [
    {'pair': f"{p[0]} + {p[1]}", 'count': c}
    for p, c in sorted(cooccur.items(), key=lambda x: -x[1])[:6]
]

results['association'] = {
    'total_orders':    len(records),
    'multi_item_orders': len(multi),
    'rules_found':     len(top_rules),
    'top_rules':       top_rules,
    'top_cooccurrence': top_cooccur
}
print(f"  ✓ {len(top_rules)} rules found, {len(multi)} multi-item orders")

# ══════════════════════════════════════════════════════════
# 3. CLASSIFICATION
# ══════════════════════════════════════════════════════════
print("\n[3/4] Running Classification...")

X_clf = df[['roast_enc','Size','Unit Price','Quantity','country_enc','loyalty_enc','Price per 100g']]
y_clf = df['coffee_enc']

X_tr,X_te,y_tr,y_te = train_test_split(X_clf,y_clf,test_size=0.2,random_state=42,stratify=y_clf)
clf = DecisionTreeClassifier(max_depth=4, min_samples_split=10, random_state=42)
clf.fit(X_tr, y_tr)

y_pred   = clf.predict(X_te)
acc      = accuracy_score(y_te, y_pred)
cv       = cross_val_score(clf, X_clf, y_clf, cv=5, scoring='accuracy')
baseline = 1 / len(coffee_map)

# Feature importances
feat_imp = [
    {'feature': f, 'importance': round(float(i), 4)}
    for f, i in sorted(zip(X_clf.columns, clf.feature_importances_), key=lambda x: -x[1])
]

# Per-class report
report = classification_report(y_te, y_pred,
    target_names=[coffee_inv[i] for i in sorted(coffee_inv)],
    output_dict=True)
class_report = []
for cls in [coffee_inv[i] for i in sorted(coffee_inv)]:
    if cls in report:
        class_report.append({
            'class':     cls,
            'precision': round(report[cls]['precision'], 3),
            'recall':    round(report[cls]['recall'],    3),
            'f1':        round(report[cls]['f1-score'],  3),
            'support':   int(report[cls]['support'])
        })

results['classification'] = {
    'model':         'Decision Tree (max_depth=4)',
    'accuracy':      round(acc, 4),
    'accuracy_pct':  round(acc*100, 1),
    'cv_mean':       round(float(cv.mean()), 4),
    'cv_std':        round(float(cv.std()),  4),
    'baseline':      round(baseline, 4),
    'vs_baseline':   round(acc/baseline, 2),
    'train_samples': len(X_tr),
    'test_samples':  len(X_te),
    'feature_importances': feat_imp,
    'class_report':  class_report
}
print(f"  ✓ Accuracy: {acc:.4f} ({acc*100:.1f}%)")

# ══════════════════════════════════════════════════════════
# 4. REGRESSION
# ══════════════════════════════════════════════════════════
print("\n[4/4] Running Regression...")

X_reg = df[['Quantity','Size','coffee_enc','roast_enc','Month','loyalty_enc','Price per 100g']]
y_reg = df['Sales']

X_tr,X_te,y_tr,y_te = train_test_split(X_reg,y_reg,test_size=0.2,random_state=42)
reg = LinearRegression()
reg.fit(X_tr, y_tr)
y_pred_r = reg.predict(X_te)

r2   = r2_score(y_te, y_pred_r)
rmse = float(np.sqrt(mean_squared_error(y_te, y_pred_r)))
mae  = float(np.mean(np.abs(y_te - y_pred_r)))

coefficients = [
    {'feature': f, 'coefficient': round(float(c), 4),
     'direction': 'positive' if c > 0 else 'negative'}
    for f, c in sorted(zip(X_reg.columns, reg.coef_), key=lambda x: -abs(x[1]))
]

results['regression'] = {
    'model':         'Multiple Linear Regression',
    'r2_score':      round(r2, 4),
    'r2_pct':        round(r2*100, 1),
    'rmse':          round(rmse, 4),
    'mae':           round(mae,  4),
    'intercept':     round(float(reg.intercept_), 4),
    'train_samples': len(X_tr),
    'test_samples':  len(X_te),
    'coefficients':  coefficients
}
print(f"  ✓ R²: {r2:.4f} ({r2*100:.1f}%)")

# ══════════════════════════════════════════════════════════
# SAVE TO SUPABASE
# ══════════════════════════════════════════════════════════
print("\nSaving to Supabase...")

# Flatten results into rows untuk tabel mining_results
rows = []

# Clustering rows
for seg in results['clustering']['segments']:
    rows.append({
        'technique':  'clustering',
        'metric_key': f"cluster_{seg['cluster']}_label",
        'metric_value': str(seg['label']),
        'detail': json.dumps(seg)
    })
rows.append({
    'technique':    'clustering',
    'metric_key':   'silhouette_score',
    'metric_value': str(results['clustering']['silhouette_score']),
    'detail':       json.dumps(results['clustering']['elbow'])
})

# Association rows
rows.append({
    'technique':    'association',
    'metric_key':   'rules_found',
    'metric_value': str(results['association']['rules_found']),
    'detail':       json.dumps(results['association']['top_rules'])
})
rows.append({
    'technique':    'association',
    'metric_key':   'multi_item_orders',
    'metric_value': str(results['association']['multi_item_orders']),
    'detail':       json.dumps(results['association']['top_cooccurrence'])
})

# Classification rows
rows.append({
    'technique':    'classification',
    'metric_key':   'accuracy',
    'metric_value': str(results['classification']['accuracy']),
    'detail':       json.dumps(results['classification']['feature_importances'])
})
rows.append({
    'technique':    'classification',
    'metric_key':   'class_report',
    'metric_value': str(results['classification']['cv_mean']),
    'detail':       json.dumps(results['classification']['class_report'])
})

# Regression rows
rows.append({
    'technique':    'regression',
    'metric_key':   'r2_score',
    'metric_value': str(results['regression']['r2_score']),
    'detail':       json.dumps(results['regression']['coefficients'])
})
rows.append({
    'technique':    'regression',
    'metric_key':   'rmse',
    'metric_value': str(results['regression']['rmse']),
    'detail':       json.dumps({'mae': results['regression']['mae'], 'intercept': results['regression']['intercept']})
})

# Save full results JSON as single row
rows.append({
    'technique':    'summary',
    'metric_key':   'full_results',
    'metric_value': 'ok',
    'detail':       json.dumps(results)
})

df_results = pd.DataFrame(rows)

# Save to Supabase
df_results.to_sql('mining_results', engine_supabase, if_exists='replace', index=False)
print(f"  ✓ {len(rows)} result rows saved to Supabase (table: mining_results)")

# Also save locally
with open('mining_results.json', 'w') as f:
    json.dump(results, f, indent=2)
print("  ✓ mining_results.json saved locally")

# ══════════════════════════════════════════════════════════
# SUMMARY
# ══════════════════════════════════════════════════════════
print("\n" + "="*50)
print(" MINING RESULTS SUMMARY")
print("="*50)
print(f"  Clustering  : Silhouette = {results['clustering']['silhouette_score']}")
print(f"  Association : {results['association']['rules_found']} rules found")
print(f"  Classification: Accuracy = {results['classification']['accuracy_pct']}%")
print(f"  Regression  : R² = {results['regression']['r2_pct']}%")
print("\n✅ All results saved to Supabase!")