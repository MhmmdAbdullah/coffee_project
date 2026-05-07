-- ============================================================
--  DATA WAREHOUSE: Coffee Sales Retail Analysis
--  Schema   : Star Schema
--  Source   : 3 sheets — orders (999 rows), customers (1000), products (48)
-- ============================================================

DROP TABLE IF EXISTS fact_sales;
DROP TABLE IF EXISTS dim_product;
DROP TABLE IF EXISTS dim_customer;
DROP TABLE IF EXISTS dim_date;
DROP TABLE IF EXISTS dim_location;

-- DIMENSION: Date
CREATE TABLE dim_date (
    date_id    INT PRIMARY KEY,
    full_date  DATE NOT NULL,
    day INT, month INT, month_name VARCHAR(20),
    quarter INT, year INT, weekday VARCHAR(15), is_weekend BOOLEAN
);

-- DIMENSION: Customer  ← customers sheet (9 columns)
CREATE TABLE dim_customer (
    customer_sk   SERIAL PRIMARY KEY,
    customer_id   VARCHAR(20) NOT NULL UNIQUE,
    customer_name VARCHAR(100),
    email         VARCHAR(150),
    phone_number  VARCHAR(30),
    address_line1 VARCHAR(150),
    city          VARCHAR(100),
    country       VARCHAR(50),
    postcode      VARCHAR(20),
    loyalty_card  VARCHAR(3)      -- 'Yes' / 'No'
);

-- DIMENSION: Product  ← products sheet (7 columns incl. price_per_100g & profit_per_unit)
CREATE TABLE dim_product (
    product_sk     SERIAL PRIMARY KEY,
    product_id     VARCHAR(20) NOT NULL UNIQUE,
    coffee_type    VARCHAR(5),
    coffee_name    VARCHAR(20),
    roast_type     VARCHAR(2),
    roast_name     VARCHAR(10),
    size_kg        DECIMAL(4,2),
    unit_price     DECIMAL(10,4),
    price_per_100g DECIMAL(10,4),   -- from products sheet
    profit_per_unit DECIMAL(10,5)   -- from products sheet
);

-- DIMENSION: Location
CREATE TABLE dim_location (
    location_id SERIAL PRIMARY KEY,
    country     VARCHAR(50) NOT NULL UNIQUE,
    region      VARCHAR(50),
    continent   VARCHAR(30)
);

-- FACT TABLE
CREATE TABLE fact_sales (
    sale_id       BIGSERIAL PRIMARY KEY,
    order_id      VARCHAR(20)   NOT NULL,
    date_id       INT           NOT NULL,
    customer_sk   INT           NOT NULL,
    product_sk    INT           NOT NULL,
    location_id   INT           NOT NULL,
    quantity      INT           NOT NULL,
    unit_price    DECIMAL(10,4) NOT NULL,
    sales_amount  DECIMAL(10,2) NOT NULL,
    profit        DECIMAL(10,4) NOT NULL,
    profit_margin DECIMAL(6,4)  NOT NULL,
    CONSTRAINT fk_date     FOREIGN KEY (date_id)     REFERENCES dim_date(date_id),
    CONSTRAINT fk_customer FOREIGN KEY (customer_sk) REFERENCES dim_customer(customer_sk),
    CONSTRAINT fk_product  FOREIGN KEY (product_sk)  REFERENCES dim_product(product_sk),
    CONSTRAINT fk_location FOREIGN KEY (location_id) REFERENCES dim_location(location_id)
);

-- ETL: dim_location
INSERT INTO dim_location (country, region, continent) VALUES
  ('United States','North America','Americas'),
  ('Ireland','Northern Europe','Europe'),
  ('United Kingdom','Northern Europe','Europe');

-- ETL: dim_product (from products sheet — all 48 rows with price_per_100g & profit_per_unit)
INSERT INTO dim_product (product_id,coffee_type,coffee_name,roast_type,roast_name,size_kg,unit_price,price_per_100g,profit_per_unit) VALUES
  ('A-L-0.2','Ara','Arabica','L','Light',0.2,3.885,1.9425,0.34965),
  ('A-L-0.5','Ara','Arabica','L','Light',0.5,7.770,1.5540,0.69930),
  ('A-L-1','Ara','Arabica','L','Light',1.0,12.950,1.2950,1.16550),
  ('A-L-2.5','Ara','Arabica','L','Light',2.5,29.785,1.1914,2.68065),
  ('A-M-0.2','Ara','Arabica','M','Medium',0.2,3.375,1.6875,0.30375),
  ('A-M-0.5','Ara','Arabica','M','Medium',0.5,6.750,1.3500,0.60750),
  ('A-M-1','Ara','Arabica','M','Medium',1.0,11.250,1.1250,1.01250),
  ('A-M-2.5','Ara','Arabica','M','Medium',2.5,25.875,1.0350,2.32875),
  ('A-D-0.2','Ara','Arabica','D','Dark',0.2,2.985,1.4925,0.26865),
  ('A-D-0.5','Ara','Arabica','D','Dark',0.5,5.970,1.1940,0.53730),
  ('A-D-1','Ara','Arabica','D','Dark',1.0,9.950,0.9950,0.89550),
  ('A-D-2.5','Ara','Arabica','D','Dark',2.5,22.885,0.9154,2.05965),
  ('R-L-0.2','Rob','Robusta','L','Light',0.2,3.585,1.7925,0.21510),
  ('R-L-0.5','Rob','Robusta','L','Light',0.5,7.170,1.4340,0.43020),
  ('R-L-1','Rob','Robusta','L','Light',1.0,11.950,1.1950,0.71700),
  ('R-L-2.5','Rob','Robusta','L','Light',2.5,27.485,1.0994,1.64910),
  ('R-M-0.2','Rob','Robusta','M','Medium',0.2,2.985,1.4925,0.17910),
  ('R-M-0.5','Rob','Robusta','M','Medium',0.5,5.970,1.1940,0.35820),
  ('R-M-1','Rob','Robusta','M','Medium',1.0,9.950,0.9950,0.59700),
  ('R-M-2.5','Rob','Robusta','M','Medium',2.5,22.885,0.9154,1.37310),
  ('R-D-0.2','Rob','Robusta','D','Dark',0.2,2.685,1.3425,0.16110),
  ('R-D-0.5','Rob','Robusta','D','Dark',0.5,5.370,1.0740,0.32220),
  ('R-D-1','Rob','Robusta','D','Dark',1.0,8.950,0.8950,0.53700),
  ('R-D-2.5','Rob','Robusta','D','Dark',2.5,20.585,0.8234,1.23510),
  ('L-L-0.2','Lib','Liberica','L','Light',0.2,4.755,2.3775,0.61815),
  ('L-L-0.5','Lib','Liberica','L','Light',0.5,9.510,1.9020,1.23630),
  ('L-L-1','Lib','Liberica','L','Light',1.0,15.850,1.5850,2.06050),
  ('L-L-2.5','Lib','Liberica','L','Light',2.5,36.455,1.4582,4.73915),
  ('L-M-0.2','Lib','Liberica','M','Medium',0.2,4.365,2.1825,0.56745),
  ('L-M-0.5','Lib','Liberica','M','Medium',0.5,8.730,1.7460,1.13490),
  ('L-M-1','Lib','Liberica','M','Medium',1.0,14.550,1.4550,1.89150),
  ('L-M-2.5','Lib','Liberica','M','Medium',2.5,33.465,1.3386,4.35045),
  ('L-D-0.2','Lib','Liberica','D','Dark',0.2,3.885,1.9425,0.50505),
  ('L-D-0.5','Lib','Liberica','D','Dark',0.5,7.770,1.5540,1.01010),
  ('L-D-1','Lib','Liberica','D','Dark',1.0,12.950,1.2950,1.68350),
  ('L-D-2.5','Lib','Liberica','D','Dark',2.5,29.785,1.1914,3.87205),
  ('E-L-0.2','Exc','Excelsa','L','Light',0.2,4.455,2.2275,0.49005),
  ('E-L-0.5','Exc','Excelsa','L','Light',0.5,8.910,1.7820,0.98010),
  ('E-L-1','Exc','Excelsa','L','Light',1.0,14.850,1.4850,1.63350),
  ('E-L-2.5','Exc','Excelsa','L','Light',2.5,34.155,1.3662,3.75705),
  ('E-M-0.2','Exc','Excelsa','M','Medium',0.2,4.125,2.0625,0.45375),
  ('E-M-0.5','Exc','Excelsa','M','Medium',0.5,8.250,1.6500,0.90750),
  ('E-M-1','Exc','Excelsa','M','Medium',1.0,13.750,1.3750,1.51250),
  ('E-M-2.5','Exc','Excelsa','M','Medium',2.5,31.625,1.2650,3.47875),
  ('E-D-0.2','Exc','Excelsa','D','Dark',0.2,3.645,1.8225,0.40095),
  ('E-D-0.5','Exc','Excelsa','D','Dark',0.5,7.290,1.4580,0.80190),
  ('E-D-1','Exc','Excelsa','D','Dark',1.0,12.150,1.2150,1.33650),
  ('E-D-2.5','Exc','Excelsa','D','Dark',2.5,27.945,1.1178,3.07395);

-- ETL: Staging tables
CREATE TABLE IF NOT EXISTS stg_orders (
    order_id VARCHAR(20), order_date DATE, customer_id VARCHAR(20),
    product_id VARCHAR(20), quantity INT, customer_name VARCHAR(100),
    email VARCHAR(150), country VARCHAR(50), coffee_type VARCHAR(5),
    roast_type VARCHAR(2), size_kg DECIMAL(4,2), unit_price DECIMAL(10,4),
    sales_amount DECIMAL(10,2), profit DECIMAL(10,4), profit_margin DECIMAL(6,4)
);

CREATE TABLE IF NOT EXISTS stg_customers (
    customer_id VARCHAR(20), customer_name VARCHAR(100), email VARCHAR(150),
    phone_number VARCHAR(30), address_line1 VARCHAR(150), city VARCHAR(100),
    country VARCHAR(50), postcode VARCHAR(20), loyalty_card VARCHAR(3)
);

-- ETL: Load dim_customer from stg_customers
INSERT IGNORE INTO dim_customer
  (customer_id,customer_name,email,phone_number,address_line1,city,country,postcode,loyalty_card)
SELECT customer_id,customer_name,NULLIF(email,''),NULLIF(phone_number,''),
       address_line1,city,country,postcode,loyalty_card
FROM stg_customers;

-- ETL: Load fact_sales
INSERT INTO fact_sales
  (order_id,date_id,customer_sk,product_sk,location_id,quantity,unit_price,sales_amount,profit,profit_margin)
SELECT o.order_id,
    CAST(DATE_FORMAT(o.order_date,'%Y%m%d') AS UNSIGNED),
    c.customer_sk, p.product_sk, l.location_id,
    o.quantity, o.unit_price, o.sales_amount, o.profit, o.profit_margin
FROM stg_orders o
JOIN dim_customer c ON o.customer_id=c.customer_id
JOIN dim_product  p ON o.product_id=p.product_id
JOIN dim_location l ON o.country=l.country
JOIN dim_date     d ON d.full_date=o.order_date;

-- ANALYTICAL QUERIES

-- Q1: Revenue by Year
SELECT d.year, COUNT(DISTINCT f.order_id) AS orders, SUM(f.sales_amount) AS total_sales,
    SUM(f.profit) AS total_profit, ROUND(AVG(f.profit_margin)*100,2) AS avg_margin_pct
FROM fact_sales f JOIN dim_date d ON f.date_id=d.date_id GROUP BY d.year ORDER BY d.year;

-- Q2: Coffee Type + Price per 100g
SELECT p.coffee_name, SUM(f.sales_amount) AS total_sales, SUM(f.profit) AS total_profit,
    AVG(p.price_per_100g) AS avg_price_100g, ROUND(SUM(f.profit)/SUM(f.sales_amount)*100,2) AS margin_pct
FROM fact_sales f JOIN dim_product p ON f.product_sk=p.product_sk
GROUP BY p.coffee_name ORDER BY total_sales DESC;

-- Q3: Loyalty Card Impact
SELECT c.loyalty_card, COUNT(DISTINCT c.customer_sk) AS customers,
    COUNT(DISTINCT f.order_id) AS orders, SUM(f.sales_amount) AS total_sales,
    ROUND(AVG(f.sales_amount),2) AS avg_order_value
FROM fact_sales f JOIN dim_customer c ON f.customer_sk=c.customer_sk
GROUP BY c.loyalty_card;

-- Q4: Top 10 Customers (with city & loyalty)
SELECT c.customer_name, c.city, c.country, c.loyalty_card,
    COUNT(DISTINCT f.order_id) AS orders, SUM(f.sales_amount) AS total_spent
FROM fact_sales f JOIN dim_customer c ON f.customer_sk=c.customer_sk
GROUP BY c.customer_name, c.city, c.country, c.loyalty_card
ORDER BY total_spent DESC LIMIT 10;

-- Q5: Monthly Trend
SELECT d.year, d.month, d.month_name, SUM(f.sales_amount) AS monthly_sales
FROM fact_sales f JOIN dim_date d ON f.date_id=d.date_id
GROUP BY d.year, d.month, d.month_name ORDER BY d.year, d.month;
