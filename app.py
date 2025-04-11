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
