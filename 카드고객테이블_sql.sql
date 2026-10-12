Use bankchurners;
SHOW TABLES;

Use bankchurners;
Describe customers;

USE bankchurners;

CREATE TABLE IF NOT EXISTS new_customers (
    CLIENTNUM BIGINT,
    Attrition_Flag TEXT,
    Customer_Age BIGINT,
    Gender TEXT,
    Dependent_count BIGINT,
    Education_Level TEXT,
    Marital_Status TEXT,
    Income_Category TEXT,
    Card_Category TEXT,
    Months_on_book BIGINT,
    Total_Relationship_Count BIGINT,
    Months_Inactive_12_mon BIGINT,
    Contacts_Count_12_mon BIGINT,
    Credit_Limit DOUBLE,
    Total_Revolving_Bal BIGINT,
    Avg_Open_To_Buy DOUBLE,
    Total_Amt_Chng_Q4_Q1 DOUBLE,
    Total_Trans_Amt BIGINT,
    Total_Trans_Ct BIGINT,
    Total_Ct_Chng_Q4_Q1 DOUBLE,
    Avg_Utilization_Ratio DOUBLE,
    data_date DATE
);