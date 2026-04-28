import pandas as pd
import mysql.connector
from dotenv import load_dotenv
import os

load_dotenv()

def insert_new_customers(csv_path='new_customers_30days.csv'):
    conn = mysql.connector.connect(
        host=os.getenv("MYSQL_HOST", "localhost"),
        port=int(os.getenv("MYSQL_PORT", 3306)),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DB")
    )
    cursor = conn.cursor()

    df = pd.read_csv(csv_path)
    print(f"CSV 로드 완료: {len(df)}명")

    sql = """
        INSERT IGNORE INTO new_customers (
            CLIENTNUM, Attrition_Flag, Customer_Age, Gender, Dependent_count,
            Education_Level, Marital_Status, Income_Category, Card_Category,
            Months_on_book, Total_Relationship_Count, Months_Inactive_12_mon,
            Contacts_Count_12_mon, Credit_Limit, Total_Revolving_Bal,
            Avg_Open_To_Buy, Total_Amt_Chng_Q4_Q1, Total_Trans_Amt,
            Total_Trans_Ct, Total_Ct_Chng_Q4_Q1, Avg_Utilization_Ratio, data_date
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
    """

    rows = [tuple(row) for row in df[[
        'CLIENTNUM', 'Attrition_Flag', 'Customer_Age', 'Gender', 'Dependent_count',
        'Education_Level', 'Marital_Status', 'Income_Category', 'Card_Category',
        'Months_on_book', 'Total_Relationship_Count', 'Months_Inactive_12_mon',
        'Contacts_Count_12_mon', 'Credit_Limit', 'Total_Revolving_Bal',
        'Avg_Open_To_Buy', 'Total_Amt_Chng_Q4_Q1', 'Total_Trans_Amt',
        'Total_Trans_Ct', 'Total_Ct_Chng_Q4_Q1', 'Avg_Utilization_Ratio', 'data_date'
    ]].values]

    cursor.executemany(sql, rows)
    conn.commit()

    print(f"✅ {cursor.rowcount}명 DB 적재 완료!")
    cursor.close()
    conn.close()

if __name__ == "__main__":
    insert_new_customers()