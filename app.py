import streamlit as st
import pandas as pd
import numpy as np
import joblib
import json
import mysql.connector
from sklearn.preprocessing import LabelEncoder
from dotenv import load_dotenv
import os
import datetime

load_dotenv()

st.set_page_config(page_title="카드사 고객 이탈 모니터링", page_icon="📊", layout="wide")

# ── 모델 로드 ──────────────────────────────────────────────────
@st.cache_resource
def load_model():
    model = joblib.load('churn_model.pkl')
    with open('model_columns.json', 'r') as f:
        columns = json.load(f)
    return model, columns

model, model_columns = load_model()

# ── DB 연결 ───────────────────────────────────────────────────
def get_conn():
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST", "localhost"),
        port=int(os.getenv("MYSQL_PORT", 3306)),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DB")
    )

# ── 임계값 (노트북 분석 기반) ─────────────────────────────────
THRESHOLDS = {
    'Total_Trans_Ct':           {'op': '<=', 'value': 45.3,  'label': '거래건수',       'unit': '건'},
    'Total_Trans_Amt':          {'op': '<=', 'value': 2993,  'label': '거래금액',       'unit': '$'},
    'Total_Ct_Chng_Q4_Q1':      {'op': '<',  'value': 1.0,   'label': '거래건수 변화율', 'unit': ''},
    'Contacts_Count_12_mon':    {'op': '>=', 'value': 2.94,  'label': '고객센터 연락횟수','unit': '회'},
    'Total_Relationship_Count': {'op': '<=', 'value': 3,     'label': '보유 금융상품수', 'unit': '개'},
}

# ── 스코어링 ─────────────────────────────────────────────────
def score(df):
    cat_cols = ['Gender', 'Education_Level', 'Marital_Status',
                'Income_Category', 'Card_Category', 'Attrition_Flag']
    df_proc = df.copy()
    le = LabelEncoder()
    for col in cat_cols:
        if col in df_proc.columns:
            df_proc[col] = le.fit_transform(df_proc[col].astype(str))
    for col in model_columns:
        if col not in df_proc.columns:
            df_proc[col] = 0
    X = df_proc[model_columns]
    df = df.copy()
    df['churn_prob'] = model.predict_proba(X)[:, 1]
    df['risk_tier'] = np.where(df['churn_prob'] >= df['churn_prob'].quantile(0.80), '고위험', '일반')
    return df

# ── 주차 계산 ─────────────────────────────────────────────────
def get_week_range(offset=0):
    today = datetime.date.today()
    monday = today - datetime.timedelta(days=today.weekday()) + datetime.timedelta(weeks=offset)
    sunday = monday + datetime.timedelta(days=6)
    return monday, sunday

# ── 사이드바 ──────────────────────────────────────────────────
st.sidebar.title("📊 카드사 고객 이탈 모니터링")
menu = st.sidebar.radio("메뉴", ["이번 주 현황", "주간 히스토리"])

# ═══════════════════════════════════════════════════════════════
# 1. 이번 주 현황
# ═══════════════════════════════════════════════════════════════
if menu == "이번 주 현황":
    st.title("📋 이번 주 신규 고객 현황")

    monday, sunday = get_week_range(0)
    st.caption(f"기준 기간: {monday} ~ {sunday}")

    # DB 로드
    conn = get_conn()
    df = pd.read_sql(
        f"SELECT * FROM new_customers WHERE data_date BETWEEN '{monday}' AND '{sunday}'",
        conn
    )
    conn.close()

    if len(df) == 0:
        st.warning("이번 주 데이터가 없어요.")
    else:
        scored = score(df)
        high = scored[scored['risk_tier'] == '고위험']

        # ── 핵심 지표 ──
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("이번 주 신규 고객", f"{len(scored):,}명")
        col2.metric("⚠️ 고위험군", f"{len(high):,}명")
        col3.metric("고위험률", f"{len(high)/len(scored)*100:.1f}%")
        col4.metric("평균 이탈 확률", f"{high['churn_prob'].mean():.1%}" if len(high) > 0 else "N/A")

        st.divider()

        # ── 임계값 기준표 ──
        st.subheader("📌 고위험군 판별 임계값")
        threshold_data = []
        for col, info in THRESHOLDS.items():
            op_str = '이하' if info['op'] == '<=' else ('미만' if info['op'] == '<' else '이상')
            threshold_data.append({
                '변수': info['label'],
                '기준': f"{info['value']}{info['unit']} {op_str}이면 위험",
                '고위험군 평균': f"{high[col].mean():.1f}{info['unit']}" if len(high) > 0 else "N/A",
            })
        st.table(pd.DataFrame(threshold_data))

        st.divider()

        # ── 날짜별 추이 ──
        st.subheader("📈 날짜별 고위험군 추이")
        daily = scored.groupby('data_date').apply(
            lambda x: pd.Series({
                '전체': len(x),
                '고위험': (x['risk_tier'] == '고위험').sum(),
            })
        ).reset_index()
        st.line_chart(daily.set_index('data_date')[['고위험', '전체']])

        st.divider()

        # ── 고위험 고객 명단 ──
        st.subheader("⚠️ 고위험 고객 명단")
        show_cols = ['CLIENTNUM', 'data_date', 'Gender', 'Income_Category',
                     'Total_Trans_Ct', 'Total_Trans_Amt',
                     'Total_Relationship_Count', 'Contacts_Count_12_mon', 'churn_prob']
        show_cols = [c for c in show_cols if c in high.columns]

        st.dataframe(
            high[show_cols].sort_values('churn_prob', ascending=False).reset_index(drop=True),
            use_container_width=True
        )

        csv = high[show_cols].to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 고위험 명단 다운로드", csv,
                           file_name=f"high_risk_{monday}.csv", mime="text/csv")

# ═══════════════════════════════════════════════════════════════
# 2. 주간 히스토리
# ═══════════════════════════════════════════════════════════════
elif menu == "주간 히스토리":
    st.title("📅 주간 히스토리")

    conn = get_conn()
    df_all = pd.read_sql("SELECT * FROM new_customers", conn)
    conn.close()

    scored_all = score(df_all)
    scored_all['data_date'] = pd.to_datetime(scored_all['data_date'])
    scored_all['week'] = scored_all['data_date'].dt.to_period('W').apply(
        lambda r: r.start_time.strftime('%Y-%m-%d')
    )

    weekly = scored_all.groupby('week').apply(
        lambda x: pd.Series({
            '신규 고객수': len(x),
            '고위험군': (x['risk_tier'] == '고위험').sum(),
            '고위험률(%)': round((x['risk_tier'] == '고위험').mean() * 100, 1),
            '평균 이탈확률': round(x['churn_prob'].mean(), 3),
        })
    ).reset_index()

    # 전주 대비 증감
    weekly['고위험군 증감'] = weekly['고위험군'].diff().fillna(0).astype(int)

    st.subheader("📈 주차별 고위험군 추이")
    import plotly.express as px
    fig = px.line(weekly, x='week', y='고위험군', markers=True,
                  labels={'week': '주차', '고위험군': '고위험군 수'})
    fig.update_layout(xaxis_tickangle=0)
    st.plotly_chart(fig, use_container_width=True)
    st.divider()

    st.subheader("📋 주차별 현황 테이블")
    st.dataframe(weekly, use_container_width=True)