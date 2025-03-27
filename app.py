# app.py
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import RunReportRequest
from google.oauth2 import service_account

# 페이지 설정
st.set_page_config(page_title="말씀동행 서비스 GA & DB 실시간 데이터 조회", layout="wide")
st.title("말씀동행 데이터 조회")

# Google API 인증
credentials = service_account.Credentials.from_service_account_file(
    'service-account.json'
)

# GA4 데이터 조회 함수
def get_ga4_data():
    client = BetaAnalyticsDataClient(credentials=credentials)
    request = RunReportRequest(
        property="properties/GA4속성ID",
        date_ranges=[{"start_date": "30daysAgo", "end_date": "today"}],
        dimensions=[{"name": "pagePath"}],
        metrics=[{"name": "screenPageViews"}],
    )
    response = client.run_report(request)
    df = pd.DataFrame([{
        '페이지': row.dimension_values[0].value,
        '조회수': int(row.metric_values[0].value)
    } for row in response.rows])
    return df

# DB 데이터 조회 함수
def get_db_data():
    engine = create_engine('postgresql://user:password@host:port/dbname')
    df = pd.read_sql("SELECT * FROM your_table", engine)
    return df

# 버튼 생성 (중요 UX)
if st.button('🔄 실시간 데이터 가져오기'):
    with st.spinner('⏳ 데이터를 가져오는 중...'):
        df_ga4 = get_ga4_data()
        df_db = get_db_data()

        st.success('✅ 데이터 로딩 완료!')

        st.subheader('GA4 데이터')
        st.dataframe(df_ga4)

        st.subheader('DB 데이터')
        st.dataframe(df_db)

        # Excel 다운로드 기능 추가
        def to_excel(df1, df2):
            output = pd.ExcelWriter("report.xlsx")
            df1.to_excel(output, sheet_name='GA4', index=False)
            df2.to_excel(output, sheet_name='DB', index=False)
            output.save()
            return output.path

        excel_path = to_excel(df_ga4, df_db)

        with open(excel_path, "rb") as file:
            btn = st.download_button(
                label="📥 엑셀 다운로드",
                data=file,
                file_name="실시간_데이터.xlsx",
                mime="application/vnd.ms-excel"
            )

else:
    st.info('👆 위 버튼을 클릭하면 최신 데이터가 즉시 로드됩니다.')
