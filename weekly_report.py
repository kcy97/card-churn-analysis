import pandas as pd
import numpy as np
import joblib
import json
import mysql.connector
from sklearn.preprocessing import LabelEncoder
from dotenv import load_dotenv
import os
import datetime
import requests
import schedule
import time

load_dotenv()

# ── 모델 로드 ──────────────────────────────────────────────────
model = joblib.load('churn_model.pkl')
with open('model_columns.json', 'r') as f:
    model_columns = json.load(f)

# ── DB 연결 ───────────────────────────────────────────────────
def get_conn():
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST", "localhost"),
        port=int(os.getenv("MYSQL_PORT", 3306)),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DB")
    )

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

# ── 저번 주 데이터 집계 ───────────────────────────────────────
def get_last_week_summary():
    today = datetime.date.today()
    last_monday = today - datetime.timedelta(days=today.weekday() + 7)
    last_sunday = last_monday + datetime.timedelta(days=6)

    conn = get_conn()
    df = pd.read_sql(
        f"SELECT * FROM new_customers WHERE data_date BETWEEN '{last_monday}' AND '{last_sunday}'",
        conn
    )
    conn.close()

    if len(df) == 0:
        return None, last_monday, last_sunday

    scored = score(df)
    high = scored[scored['risk_tier'] == '고위험']

    summary = {
        'period': f"{last_monday} ~ {last_sunday}",
        'total': len(scored),
        'high_risk': len(high),
        'high_risk_rate': round(len(high) / len(scored) * 100, 1),
        'avg_churn_prob': round(float(high['churn_prob'].mean()) * 100, 1),
        'avg_trans_ct': round(high['Total_Trans_Ct'].mean(), 1),
        'avg_trans_amt': round(high['Total_Trans_Amt'].mean(), 1),
        'avg_contacts': round(high['Contacts_Count_12_mon'].mean(), 1),
    }
    return summary, last_monday, last_sunday

# ── 전주 대비 증감 계산 ───────────────────────────────────────
def get_prev_week_high_risk():
    today = datetime.date.today()
    prev_monday = today - datetime.timedelta(days=today.weekday() + 14)
    prev_sunday = prev_monday + datetime.timedelta(days=6)

    conn = get_conn()
    df = pd.read_sql(
        f"SELECT * FROM new_customers WHERE data_date BETWEEN '{prev_monday}' AND '{prev_sunday}'",
        conn
    )
    conn.close()

    if len(df) == 0:
        return None

    scored = score(df)
    return len(scored[scored['risk_tier'] == '고위험'])

# ── Slack 발송 ────────────────────────────────────────────────
def send_slack_report():
    summary, last_monday, last_sunday = get_last_week_summary()
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")

    if summary is None:
        print("지난 주 데이터 없음. Slack 발송 스킵.")
        return

    prev_high = get_prev_week_high_risk()
    delta = summary['high_risk'] - prev_high if prev_high else 0
    delta_str = f"+{delta}명 ▲" if delta > 0 else (f"{delta}명 ▼" if delta < 0 else "변동 없음")
    delta_emoji = "🔴" if delta > 0 else ("🟢" if delta < 0 else "⚪")

    message = {
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "📊 카드사 고객 이탈 주간 리포트"}
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*기간:* {summary['period']}"}
            },
            {"type": "divider"},
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*신규 고객 수*\n{summary['total']:,}명"},
                    {"type": "mrkdwn", "text": f"*⚠️ 고위험군*\n{summary['high_risk']:,}명 ({summary['high_risk_rate']}%)"},
                    {"type": "mrkdwn", "text": f"*전주 대비*\n{delta_emoji} {delta_str}"},
                    {"type": "mrkdwn", "text": f"*평균 이탈 확률*\n{summary['avg_churn_prob']:.1f}%"},
                ]
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        "*고위험군 주요 지표*\n"
                        f"• 평균 거래건수: {summary['avg_trans_ct']}건\n"
                        f"• 평균 거래금액: ${summary['avg_trans_amt']:,.0f}\n"
                        f"• 평균 고객센터 연락횟수: {summary['avg_contacts']}회"
                    )
                }
            },
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": "🤖 카드사 이탈 모니터링 시스템 자동 발송"}
                ]
            }
        ]
    }

    response = requests.post(webhook_url, json=message)
    if response.status_code == 200:
        print(f"✅ Slack 주간 리포트 발송 완료! ({datetime.date.today()})")
    else:
        print(f"❌ Slack 발송 실패: {response.status_code}")

# ── 스케줄 설정 (매주 월요일 오전 9시) ───────────────────────
def run_scheduler():
    schedule.every().monday.at("09:00").do(send_slack_report)
    print("✅ 스케줄러 시작 — 매주 월요일 09:00 자동 발송")
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        # 테스트용: 바로 발송
        print("📤 테스트 발송 중...")
        send_slack_report()
    else:
        # 스케줄러 실행
        run_scheduler()