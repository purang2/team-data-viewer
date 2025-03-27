import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import RunReportRequest
from google.oauth2 import service_account
from sshtunnel import SSHTunnelForwarder


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
        property="482752996",
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

# --- DB 함수 (SSH 터널링 포함, 완전한 버전) ---
def get_db_data():
    ssh_host = st.secrets["ssh"]["ssh_host"]
    ssh_port = st.secrets["ssh"]["ssh_port"]
    ssh_username = st.secrets["ssh"]["ssh_username"]
    ssh_password = st.secrets["ssh"]["ssh_password"]

    db_host = st.secrets["ssh"]["db_host"]
    db_port = st.secrets["ssh"]["db_port"]
    db_name = st.secrets["ssh"]["db_name"]
    db_user = st.secrets["ssh"]["db_user"]
    db_password = st.secrets["ssh"]["db_password"]

    query = """
    SELECT verse_ref, verse_text, COUNT(*) AS count
    FROM verse_statistics
    GROUP BY verse_ref, verse_text
    ORDER BY count DESC
    LIMIT 30;
    """

    with SSHTunnelForwarder(
        (ssh_host, ssh_port),
        ssh_username=ssh_username,
        ssh_password=ssh_password,
        remote_bind_address=(db_host, db_port)
    ) as tunnel:

        local_port = tunnel.local_bind_port
        engine = create_engine(
            f'postgresql://{db_user}:{db_password}@localhost:{local_port}/{db_name}'
        )

        df_db = pd.read_sql(query, engine)

    return df_db

# --- 버튼 클릭시 데이터 로드 ---
if st.button("🔄 실시간 데이터 조회"):
    with st.spinner('⏳ 데이터를 불러오는 중...'):
        ga4_data = get_ga4_data()
        db_data = get_db_data()

        st.subheader("🔹 GA4 데이터")
        st.line_chart(ga4_data.set_index('날짜')['조회수'])

        st.subheader("🔸 DB 인기 구절 Top 30")
        st.dataframe(db_data, use_container_width=True)

else:
    st.info("👆 버튼을 눌러 최신 데이터를 조회합니다.")
