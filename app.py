import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import RunReportRequest
from google.oauth2 import service_account

st.set_page_config(page_title="📊 Team Data Viewer", layout="wide")

# Header 디자인
st.markdown("<h1 style='text-align: center; color: #FF4B4B;'>📊 Team Data Viewer</h1>", unsafe_allow_html=True)

# FONT : Pretendard
pretendard_css = """
<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');

html, body, [class*="css"]  {
    font-family: 'Pretendard', sans-serif;
}
</style>
"""

st.markdown(pretendard_css, unsafe_allow_html=True)



# --- GA4 함수 ---
def get_ga4_data():
    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"]
    )
    client = BetaAnalyticsDataClient(credentials=credentials)

    request = RunReportRequest(
        property="properties/482752996",
        date_ranges=[{"start_date": "30daysAgo", "end_date": "today"}],
        dimensions=[{"name": "date"}],
        metrics=[{"name": "screenPageViews"}],
    )
    response = client.run_report(request)
    df_ga4 = pd.DataFrame([{
        '날짜': row.dimension_values[0].value,
        '조회수': int(row.metric_values[0].value)
    } for row in response.rows])

    df_ga4['날짜'] = pd.to_datetime(df_ga4['날짜'])
    return df_ga4

# --- DB 함수 ---
def get_db_data():
    db_secret = st.secrets["db"]
    engine = create_engine(
        f"postgresql://{db_secret['user']}:{db_secret['password']}@{db_secret['host']}:{db_secret['port']}/{db_secret['dbname']}"
    )
    query = """
    SELECT verse_ref, verse_text, COUNT(*) AS count
    FROM verse_statistics
    GROUP BY verse_ref, verse_text
    ORDER BY count DESC
    LIMIT 30;
    """
    df_db = pd.read_sql(query, engine)
    return df_db

# 버튼 클릭 로직
if st.button("🔄 실시간 데이터 조회"):
    with st.spinner('⏳ 데이터를 불러오는 중...'):
        ga4_data = get_ga4_data()
        db_data = get_db_data()

        st.markdown("<h2 style='color:#4B89FF;'>GA4 최근 30일 조회수 추이</h2>", unsafe_allow_html=True)
        st.line_chart(ga4_data.set_index('날짜')['조회수'])

        st.markdown("<h3 style='color:#4B89FF;'>📅 GA4 데이터 테이블</h3>", unsafe_allow_html=True)
        ga4_data_styled = ga4_data.style.format({"조회수": "{:,.0f}"}).applymap(lambda x: 'color: blue', subset=['조회수'])
        st.dataframe(ga4_data_styled, use_container_width=True)

        st.markdown("---")
        st.markdown("<h2 style='color:#FF4B4B;'>🔥 인기 구절 Top 30</h2>", unsafe_allow_html=True)
        st.dataframe(db_data.style.format({"count": "{:,.0f}"}), use_container_width=True)

        # Excel 다운로드
        @st.cache_data
        def convert_to_excel(df_ga, df_db):
            with pd.ExcelWriter("report.xlsx") as writer:
                df_ga.to_excel(writer, sheet_name='GA4_Data', index=False)
                df_db.to_excel(writer, sheet_name='DB_Verse_Stats', index=False)
            with open("report.xlsx", "rb") as f:
                return f.read()

        excel_file = convert_to_excel(ga4_data, db_data)

        st.download_button(
            label="📥 Excel 다운로드",
            data=excel_file,
            file_name="Team_Data_Report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
else:
    st.markdown("<h3 style='text-align: center;'>👆 위 버튼을 눌러 최신 데이터를 확인하세요!</h3>", unsafe_allow_html=True)
