import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import RunReportRequest
from google.oauth2 import service_account
from sshtunnel import SSHTunnelForwarder
from wordcloud import WordCloud
import matplotlib.pyplot as plt

st.set_page_config(page_title="📊 성경챗봇 데이터 Viewer", layout="wide")

st.markdown("<h1 style='text-align: center; color: #FF4B4B;'>📊 성경챗봇 데이터 Viewer</h1>", unsafe_allow_html=True)

pretendard_css = """
<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');

html, body, [class*="css"]  {
    font-family: 'Pretendard', sans-serif;
}
</style>
"""
st.markdown(pretendard_css, unsafe_allow_html=True)


# GA4 함수
def get_ga4_data(days):
    credentials = service_account.Credentials.from_service_account_info(st.secrets["gcp_service_account"])
    client = BetaAnalyticsDataClient(credentials=credentials)

    request = RunReportRequest(
        property="properties/482752996",
        date_ranges=[{"start_date": f"{days}daysAgo", "end_date": "today"}],
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

def get_ga4_summary(days):
    credentials = service_account.Credentials.from_service_account_info(st.secrets["gcp_service_account"])
    client = BetaAnalyticsDataClient(credentials=credentials)

    request = RunReportRequest(
        property="properties/482752996",
        date_ranges=[{"start_date": f"{days}daysAgo", "end_date": "today"}],
        dimensions=[{"name": "date"}],
        metrics=[{"name": "activeUsers"}, {"name": "eventCount"}, {"name": "newUsers"}],
    )

    response = client.run_report(request)
    rows = response.rows
    if not rows:
        return {"활성 사용자 수": 0, "이벤트 수": 0, "새 사용자 수": 0}

    active_users = sum(int(r.metric_values[0].value) for r in rows)
    event_count = sum(int(r.metric_values[1].value) for r in rows)
    new_users = sum(int(r.metric_values[2].value) for r in rows)

    return {"활성 사용자 수": active_users, "이벤트 수": event_count, "새 사용자 수": new_users}

# DB 함수
def get_db_data():
    ssh = st.secrets["ssh"]
    query = """
    SELECT verse_ref, verse_text, COUNT(*) AS count
    FROM verse_statistics
    GROUP BY verse_ref, verse_text
    ORDER BY count DESC
    LIMIT 30;
    """

    with SSHTunnelForwarder(
        (ssh["ssh_host"], ssh["ssh_port"]),
        ssh_username=ssh["ssh_username"],
        ssh_password=ssh["ssh_password"],
        remote_bind_address=(ssh["db_host"], ssh["db_port"])
    ) as tunnel:

        local_port = tunnel.local_bind_port
        engine = create_engine(f'postgresql://{ssh["db_user"]}:{ssh["db_password"]}@localhost:{local_port}/{ssh["db_name"]}')
        df_db = pd.read_sql(query, engine)

    return df_db

def get_questions_as_text():
    ssh = st.secrets["ssh"]
    query = "SELECT question_text FROM user_questions"

    with SSHTunnelForwarder(
        (ssh["ssh_host"], ssh["ssh_port"]),
        ssh_username=ssh["ssh_username"],
        ssh_password=ssh["ssh_password"],
        remote_bind_address=(ssh["db_host"], ssh["db_port"])
    ) as tunnel:

        local_port = tunnel.local_bind_port
        engine = create_engine(f'postgresql://{ssh["db_user"]}:{ssh["db_password"]}@localhost:{local_port}/{ssh["db_name"]}')
        df = pd.read_sql(query, engine)

    freq = df['question_text'].value_counts()
    template_questions = freq[freq > 30].index.tolist()
    filtered_df = df[~df['question_text'].isin(template_questions)]

    return " ".join(filtered_df['question_text'].dropna().tolist())

def render_wordcloud_raw(text):
    wc = WordCloud(
        font_path='fonts/Pretendard-Regular.ttf',
        background_color='white', width=800, height=400
    ).generate(text)

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.imshow(wc, interpolation='bilinear')
    ax.axis('off')
    return fig

if st.button("🔄 실시간 데이터 조회"):
    with st.spinner('⏳ 데이터를 불러오는 중...'):
        ga4_data_full = get_ga4_data(30)
        ga4_data_week = get_ga4_data(7)
        summary_full = get_ga4_summary(30)
        summary_week = get_ga4_summary(7)
        db_data = get_db_data()

        st.subheader("🔹 구글 애널리틱스 | 말씀동행")
        st.markdown("## 🔹 요약 통계 (전체 데이터)")
        col1, col2, col3 = st.columns(3)
        col1.metric("👥 활성 사용자 수", f"{summary_full['활성 사용자 수']:,}")
        col2.metric("✨ 이벤트 수", f"{summary_full['이벤트 수']:,}")
        col3.metric("🆕 새 사용자 수", f"{summary_full['새 사용자 수']:,}")

        st.markdown("## 🔹 요약 통계 (최근 일주일)")
        col1, col2, col3 = st.columns(3)
        col1.metric("👥 활성 사용자 수", f"{summary_week['활성 사용자 수']:,}")
        col2.metric("✨ 이벤트 수", f"{summary_week['이벤트 수']:,}")
        col3.metric("🆕 새 사용자 수", f"{summary_week['새 사용자 수']:,}")

        st.subheader("🔹 GA4 데이터 (최근 30일)")
        st.line_chart(ga4_data_full.set_index('날짜')['조회수'])

        st.subheader("🔸 DB 인기 성경말씀 구절 Top 30")
        st.dataframe(db_data, use_container_width=True)

    st.subheader("💬 사용자가 가장 많이 고민한 단어는?")
    with st.spinner("워드클라우드 생성 중..."):
        text = get_questions_as_text()
        if text.strip():
            fig = render_wordcloud_raw(text)
            st.pyplot(fig)
        else:
            st.warning("질문 데이터가 부족합니다.")
else:
    st.info("👆 버튼을 눌러 최신 데이터를 조회합니다.")
