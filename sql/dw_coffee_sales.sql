DROP TABLE IF EXISTS fact_sales CASCADE;
DROP TABLE IF EXISTS dim_customer CASCADE;
DROP TABLE IF EXISTS dim_product CASCADE;
DROP TABLE IF EXISTS dim_location CASCADE;
DROP TABLE IF EXISTS dim_date CASCADE;

CREATE TABLE dim_date (
    date_id INT PRIMARY KEY,
    full_date DATE,
    day INT,
    month INT,
    month_name VARCHAR(20),
    quarter INT,
    year INT,
    weekday VARCHAR(20),
    is_weekend BOOLEAN
);

CREATE TABLE dim_customer (
    customer_sk SERIAL PRIMARY KEY,
    customer_id VARCHAR(20) UNIQUE,
    customer_name VARCHAR(100),
    email VARCHAR(150),
    phone_number VARCHAR(30),
    address_line1 VARCHAR(150),
    city VARCHAR(100),
    country VARCHAR(50),
    postcode VARCHAR(20),
    loyalty_card VARCHAR(10)
);

CREATE TABLE dim_product (
    product_sk SERIAL PRIMARY KEY,
    product_id VARCHAR(20) UNIQUE,
    coffee_type VARCHAR(10),
    coffee_name VARCHAR(50),
    roast_type VARCHAR(10),
    roast_name VARCHAR(20),
    size_kg NUMERIC(4,2),
    unit_price NUMERIC(10,2),
    price_per_100g NUMERIC(10,2),
    profit_per_unit NUMERIC(10,2)
);

CREATE TABLE dim_location (
    location_id SERIAL PRIMARY KEY,
    country VARCHAR(50) UNIQUE,
    region VARCHAR(50),
    continent VARCHAR(50)
);

CREATE TABLE fact_sales (
    sale_id BIGSERIAL PRIMARY KEY,
    order_id VARCHAR(20),

    date_id INT REFERENCES dim_date(date_id),
    customer_sk INT REFERENCES dim_customer(customer_sk),
    product_sk INT REFERENCES dim_product(product_sk),
    location_id INT REFERENCES dim_location(location_id),

    quantity INT,
    unit_price NUMERIC(10,2),
    sales_amount NUMERIC(10,2),
    profit NUMERIC(10,2),
    profit_margin NUMERIC(10,4)
);