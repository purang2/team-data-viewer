import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import RunReportRequest
from google.oauth2 import service_account
from sshtunnel import SSHTunnelForwarder
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import re
from collections import Counter

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

def get_questions_as_freq_dict():
    ssh = st.secrets["ssh"]
    query = "SELECT question_text FROM user_questions"

    starter_questions = [
        "가족과의 갈등을 어떻게 풀어야 할까요?",
        "친구관계에서 상처받았을 때는 어떻게 해야 할까요?",
        "대인관계가 어려울 때 어떻게 해야 할까요?",
        "직장 안에서 갈등이 생겼을 때 어떻게 대처해야 할까요?",
        "기도는 어떻게 하면 좋을까요?",
        "성경 읽기가 어려워요.",
        "예배생활이 게을러졌어요.",
        "영적으로 메말랐다고 느낄 때 어떻게 회복할 수 있을까요?",
        "중요한 결정을 앞두고 있어요.",
        "미래가 불안해요.",
        "스트레스 관리가 필요해요.",
        "감사와 기쁨을 잃었을 때, 어떻게 회복하면 좋을까요?",
        "고난이 찾아왔을 때, 하나님을 신뢰하기가 어려워요.",
        "좌절하고 낙심이 클 때, 어떻게 회복할 수 있을까요?",
        "재정적 어려움이나 질병으로 힘들 때 어떻게 극복해야 할까요?",
        "실패 후 다시 일어서고 싶어요. 어떻게 재기할 수 있을까요?",
        "슬픔과 상실 가운데 있을 때, 어떻게 위로를 얻을 수 있을까요?"
    ]
    with SSHTunnelForwarder(
        (ssh["ssh_host"], ssh["ssh_port"]),
        ssh_username=ssh["ssh_username"],
        ssh_password=ssh["ssh_password"],
        remote_bind_address=(ssh["db_host"], ssh["db_port"])
    ) as tunnel:

        local_port = tunnel.local_bind_port
        engine = create_engine(
            f'postgresql://{ssh["db_user"]}:{ssh["db_password"]}@localhost:{local_port}/{ssh["db_name"]}'
        )
        df = pd.read_sql(query, engine)

    # 스타터 질문 제외
    filtered_df = df[~df['question_text'].isin(starter_questions)]

    texts = " ".join(filtered_df['question_text'].dropna().tolist())
    words = re.findall(r'[가-힣]{2,}', texts)  # 두 글자 이상 한글 단어만 추출

    freq_dict = dict(Counter(words))

    return freq_dict


def render_wordcloud_freq(freq_dict):
    wc = WordCloud(
        font_path='fonts/Pretendard-Regular.ttf',
        background_color='white',
        width=1200,
        height=600,
        max_words=200,            # 단어 수 최대한 많게 설정
        max_font_size=80,         # 글자 크기를 줄여 단어 밀도 증가
        relative_scaling=0.3,     # 상대적 크기 차이를 더 줄임(골고루 분포)
        prefer_horizontal=0.9,    # 약간의 세로배치 허용으로 밀도 높임
        colormap='tab20c',        # 더욱 다양한 색상 조합 사용
        margin=1                  # 단어 간 여백을 최소화
    ).generate_from_frequencies(freq_dict)
    fig, ax = plt.subplots(figsize=(15, 7))
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
        freq_dict = get_questions_as_freq_dict()
        if freq_dict:
            fig = render_wordcloud_freq(freq_dict)
            st.pyplot(fig)
        else:
            st.warning("질문 데이터가 부족합니다.")
else:
    st.info("👆 버튼을 눌러 최신 데이터를 조회합니다.")
