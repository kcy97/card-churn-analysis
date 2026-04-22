# 📊 카드사 고객 이탈 분석 프로젝트

## 프로젝트 개요
MySQL DB에 저장된 카드사 고객 데이터(10,127건)를 기반으로 고객 이탈 패턴을 파악하고,  
이탈 패턴 유사도 기반 위험군을 식별하여 선제적 고객 유지 전략 수립을 위한 의사결정을 지원한다.

## 데이터
| 항목 | 내용 |
|------|------|
| 출처 | BankChurners.csv (Kaggle) |
| 레코드 수 | 10,127명 |
| 변수 수 | 21개 |
| DB | MySQL (bankchurners) |
| 분석 환경 | Python 3.11 / Jupyter Notebook (VS Code) |
| 주요 라이브러리 | pandas, XGBoost, SHAP, scikit-learn, matplotlib, seaborn |

## 분석 단계
- **STAGE 1**: CSV → MySQL 적재
- **STAGE 2**: EDA (이탈률 16.1%, 행동 변수 중심 분석)
- **STAGE 3**: XGBoost 모델 (ROC-AUC 0.993, Recall 0.90)
- **STAGE 4**: 고위험 유지 고객 408명 추출 및 전략 도출

## 핵심 인사이트
- 이탈은 **누가**가 아닌 **어떻게 쓰는가**가 결정한다
- 거래건수/금액 감소 + 고객센터 연락 증가 → 가장 강력한 이탈 신호
- 고위험 유지 고객 선제 개입 시 연간 최대 **$365,146 거래액 보존** 가능

## 실행 방법
```bash
# 환경 변수 설정
cp .env.example .env  # .env 파일에 DB 정보 입력

# 패키지 설치
pip install -r requirements.txt

# 노트북 실행
jupyter notebook card_analysis.ipynb
```

## 산출물
| 파일 | 설명 |
|------|------|
| card_analysis(1).ipynb | 전체 분석 노트북 |
| fig_01_churn_overview.png | 이탈 현황 |
| fig_shap_bar.png | SHAP 변수 중요도 |
| fig_highrisk_profile.png | 고위험 vs 안전군 비교 |
| 발표자료.pptx | 발표 슬라이드 |
| 분석보고서.docx | 분석 보고서 |