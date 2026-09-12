import streamlit as st
import os
import pandas as pd
from datetime import date, timedelta

from src.config.settings import get_api_credentials, APIConfig
from src.services.collector import MarketDataCollector
from src.services.eda_service import MarketEDAService
from src.components.charts import (
    render_trend_chart,
    render_channel_bar_chart,
    render_channel_share_bar_chart,
    render_word_freq_chart
)
from src.components.views import (
    render_summary_metrics,
    render_wordcloud_section
)

# 스트림릿 페이지 기본 설정
st.set_page_config(
    page_title="네이버 마켓 인사이트 EDA 대시보드",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 커스텀 스타일 (네이버 그린 & 클린 모던 테마)
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 800;
        color: #1E293B;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        color: #64748B;
        font-size: 1.05rem;
        margin-bottom: 1.5rem;
    }
    .stMetric {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        padding: 12px 16px;
        border-radius: 10px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02);
    }
    .naver-badge {
        background-color: #03C75A;
        color: white;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 0.8rem;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# 세션 상태 초기화
if "analysis_data" not in st.session_state:
    st.session_state.analysis_data = None
if "searched_keywords" not in st.session_state:
    st.session_state.searched_keywords = []

# --- 사이드바 설정 영역 ---
st.sidebar.markdown("## ⚙️ 설정 및 검색 조건")

# 1. API 인증 정보
with st.sidebar.expander("🔑 네이버 API 인증 설정", expanded=True):
    auth_type = st.radio(
        "인증 규격 선택",
        options=["ncloud_apigw", "naver_developers"],
        format_func=lambda x: "네이버 클라우드 API 허브 (공식 권장)" if x == "ncloud_apigw" else "네이버 개발자 센터 (레거시 오픈 API)",
        index=0
    )
    
    from dotenv import load_dotenv
    load_dotenv(override=True)
    
    def _get_val(key: str) -> str:
        v = os.getenv(key, "")
        if not v and hasattr(st, "secrets") and key in st.secrets:
            v = str(st.secrets[key])
        return v

    default_client_id = _get_val("NAVER_CLIENT_ID") or _get_val("NCLOUD_API_KEY_ID")
    default_client_secret = _get_val("NAVER_CLIENT_SECRET") or _get_val("NCLOUD_API_KEY")
    
    client_id_input = st.text_input(
        "Client ID / API Key ID",
        value=default_client_id,
        type="password" if default_client_id else "default",
        placeholder=".env 파일 또는 직접 입력"
    )
    client_secret_input = st.text_input(
        "Client Secret / API Key",
        value=default_client_secret,
        type="password",
        placeholder=".env 파일 또는 직접 입력"
    )
    
    if client_id_input and client_secret_input:
        st.caption("✅ 인증키가 설정되었습니다.")
    else:
        st.caption("⚠️ `.env` 파일에 키를 입력하거나 위 입력칸에 입력해 주세요.")
        
    st.markdown("""
    <small>
    • [네이버 개발자 센터](https://developers.naver.com)<br>
    • [네이버 클라우드 API HUB 가이드](https://api.ncloud-docs.com/docs/naver-api-hub-overview)
    </small>
    """, unsafe_allow_html=True)

# 2. 검색어 입력
st.sidebar.markdown("### 🔎 분석 키워드")
keywords_str = st.sidebar.text_input(
    "검색어 (, 로 구분)",
    value="인공지능, 챗GPT, 생성형AI",
    help="쉼표(,)로 구분하여 최대 5개까지 비교 분석을 권장합니다."
)

# 3. 기간 설정
st.sidebar.markdown("### 📅 분석 기간")
today = date.today()
col_p1, col_p2 = st.sidebar.columns(2)
with col_p1:
    if st.button("최근 1개월", use_container_width=True):
        st.session_state.temp_start = today - timedelta(days=30)
        st.session_state.temp_end = today
with col_p2:
    if st.button("최근 3개월", use_container_width=True):
        st.session_state.temp_start = today - timedelta(days=90)
        st.session_state.temp_end = today

default_start = st.session_state.get("temp_start", today - timedelta(days=30))
default_end = st.session_state.get("temp_end", today)

date_range = st.sidebar.date_input(
    "조회 기간 선택",
    value=(default_start, default_end),
    max_value=today
)

start_date, end_date = default_start, default_end
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range[0], date_range[1]
elif isinstance(date_range, (list, tuple)) and len(date_range) == 1:
    start_date = end_date = date_range[0]

# 4. 고급 수집 옵션
with st.sidebar.expander("🛠️ 수집 옵션 상세"):
    time_unit = st.selectbox(
        "트렌드 집계 주기",
        options=["date", "week", "month"],
        format_func=lambda x: {"date": "일간 (Date)", "week": "주간 (Week)", "month": "월간 (Month)"}[x],
        index=0
    )
    sort_option = st.selectbox(
        "검색 결과 정렬 기준",
        options=["sim", "date"],
        format_func=lambda x: "유사도/정확도순 (sim)" if x == "sim" else "날짜순 (date)",
        index=0
    )
    display_limit = st.slider("채널별 수집 건수 (1회 최대)", min_value=10, max_value=100, value=100, step=10)

# 실행 버튼
run_button = st.sidebar.button(
    "🚀 시장 데이터 수집 및 EDA 분석 시작",
    type="primary",
    use_container_width=True
)

# --- 메인 화면 렌더링 ---
st.markdown('<div class="main-title">📈 네이버 마켓 인사이트 탐색적 데이터 분석(EDA)</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title"><span class="naver-badge">NAVER API</span> 8대 검색 채널 및 데이터랩 트렌드 기반 멀티 키워드 시장 동향 심층 분석</div>', unsafe_allow_html=True)

# 실행 트리거 처리
if run_button:
    # 1. 키워드 전처리
    raw_keywords = [k.strip() for k in keywords_str.split(",") if k.strip()]
    if not raw_keywords:
        st.error("분석할 검색어를 최소 1개 이상 입력해 주세요.")
        st.stop()

    # 2. 인증 헤더 준비
    headers = get_api_credentials(
        manual_client_id=client_id_input,
        manual_client_secret=client_secret_input,
        auth_type=auth_type
    )

    if not headers:
        st.error("⚠️ 네이버 API 자격증명이 필요합니다. 사이드바의 설정창이나 `.env` 파일에 Client ID와 Secret을 입력해 주세요.")
        st.stop()

    with st.spinner(f"네이버 8대 채널 및 데이터랩 트렌드 데이터를 수집 및 분석 중입니다... ({', '.join(raw_keywords)})"):
        collector = MarketDataCollector(headers)
        data = collector.collect_all(
            keywords=raw_keywords,
            start_date=start_date,
            end_date=end_date,
            time_unit=time_unit,
            sort=sort_option,
            display=display_limit
        )
        st.session_state.analysis_data = data
        st.session_state.searched_keywords = raw_keywords
    st.success(f"총 {len(raw_keywords)}개 키워드에 대한 데이터 수집 및 전처리가 완료되었습니다!")

# 분석 데이터가 있는 경우 대시보드 표시
analysis_data = st.session_state.analysis_data
keywords = st.session_state.searched_keywords

if analysis_data:
    search_results = analysis_data["search_results"]
    trend_result = analysis_data["trend_result"]

    # 기본 데이터프레임 계산
    summary_df = MarketEDAService.get_summary_metrics(search_results)
    channel_dist_df = MarketEDAService.get_channel_distribution(search_results)
    trend_df = MarketEDAService.get_trend_dataframe(trend_result)

    # 1. 상단 메트릭 요약
    render_summary_metrics(summary_df, trend_df)
    st.markdown("<br>", unsafe_allow_html=True)

    # 2. 10개 메인 분석 탭 (통합 인사이트 + 8대 채널별 심층 EDA + Excel 일괄 다운로드)
    (
        tab_summary,
        tab_news,
        tab_blog,
        tab_cafe,
        tab_web,
        tab_encyc,
        tab_kin,
        tab_local,
        tab_image,
        tab_excel
    ) = st.tabs([
        "📊 통합 마켓 인사이트",
        "📰 뉴스 심층 EDA",
        "📝 블로그 심층 EDA",
        "☕ 카페글 심층 EDA",
        "🌐 웹문서 심층 EDA",
        "📖 백과사전 심층 EDA",
        "💬 지식iN 심층 EDA",
        "📍 지역(업체) 심층 EDA",
        "🖼️ 이미지 심층 EDA",
        "📥 엑셀(Excel) 일괄 다운로드"
    ])

    # 탭 0: 통합 마켓 인사이트
    with tab_summary:
        st.markdown("### 📌 키워드별 검색 문서 수(Total Count) 집계")
        st.dataframe(
            summary_df.style.highlight_max(axis=0, color="#D1FAE5"),
            use_container_width=True
        )

        st.markdown("### 📈 네이버 데이터랩 시계열 트렌드 추이")
        if not trend_df.empty:
            st.plotly_chart(render_trend_chart(trend_df), key="summary_trend_chart", use_container_width=True)
        else:
            st.info("데이터랩 트렌드 데이터가 없습니다.")

        st.markdown("### 🏢 채널별 문서 점유율 비교 (파이차트 제외: 누적 가로 막대 차트)")
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            st.plotly_chart(render_channel_bar_chart(channel_dist_df), key="summary_channel_bar", use_container_width=True)
        with col_c2:
            st.plotly_chart(render_channel_share_bar_chart(channel_dist_df), key="summary_channel_share", use_container_width=True)

    # 탭 1 ~ 8: 8대 채널별 심층 EDA (각 탭마다 5개 이상 그래프 + 5개 이상 통계표)
    from src.components.channel_eda_view import render_channel_deep_eda

    with tab_news:
        render_channel_deep_eda(search_results, "news", keywords)

    with tab_blog:
        render_channel_deep_eda(search_results, "blog", keywords)

    with tab_cafe:
        render_channel_deep_eda(search_results, "cafearticle", keywords)

    with tab_web:
        render_channel_deep_eda(search_results, "webkr", keywords)

    with tab_encyc:
        render_channel_deep_eda(search_results, "encyc", keywords)

    with tab_kin:
        render_channel_deep_eda(search_results, "kin", keywords)

    with tab_local:
        render_channel_deep_eda(search_results, "local", keywords)

    with tab_image:
        render_channel_deep_eda(search_results, "image", keywords)

    # 탭 9: 엑셀(Excel) 일괄 다운로드
    with tab_excel:
        st.markdown("### 📥 전체 채널 EDA 통계 및 원본 데이터 Multi-sheet Excel 다운로드")
        st.markdown("""
        대시보드에서 분석된 모든 채널의 정제된 원본 데이터 및 통계 요약을 **1개의 엑셀 통합 문서(.xlsx)**로 묶어 다운로드할 수 있습니다.
        
        **포함된 엑셀 시트 목록:**
        - `종합_마켓_요약`: 키워드별 8대 채널 누적 문서수 및 총 버즈량
        - `검색어_트렌드`: 데이터랩 기간별 일자/주간/월간 상대 지수 시계열
        - `채널_뉴스`, `채널_블로그`, `채널_카페글`, `채널_웹문서`, `채널_백과사전`, `채널_지식iN`, `채널_지역`, `채널_이미지`: 각 채널별 텍스트 통계(글자수, 단어수, 감성지수, 출처, 링크 등)
        """)

        with st.spinner("다중 시트 엑셀 파일을 생성 중입니다..."):
            excel_bytes = MarketEDAService.generate_multisheet_excel(search_results, trend_df)

        st.download_button(
            label="📊 전체 데이터 엑셀(.xlsx) 일괄 다운로드",
            data=excel_bytes,
            file_name=f"naver_market_eda_all_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary"
        )

else:
    # 데이터 수집 전 초기 가이드 화면
    st.info("👈 좌측 사이드바에서 분석할 검색어와 기간을 설정한 후 **[시장 데이터 수집 및 EDA 분석 시작]** 버튼을 눌러주세요.")

    st.markdown("""
    ### 🌟 제공 기능 안내
    1. **8대 채널 통합 수집**: 뉴스, 블로그, 웹문서, 이미지, 지식iN, 지역, 카페글, 백과사전을 공식 네이버 API로 수집합니다.
    2. **검색어 트렌드(DataLab)**: 기간별 일간/주간/월간 상대적 검색량 추이를 인터랙티브 라인 차트로 시각화합니다.
    3. **시장 버즈량 점유율**: 키워드 간 각 채널별 문서 수(Total Count)를 비교하여 시장 영향력을 파악합니다.
    4. **텍스트 마이닝 & 워드클라우드**: 수집된 콘텐츠 제목 및 요약문에서 자주 등장하는 연관 키워드를 자동 추출합니다.
    5. **갤러리 뷰 & CSV 내보내기**: 이미지 갤러리 및 각 채널별 원본 데이터를 브라우징하고 CSV로 다운로드할 수 있습니다.
    
    ### 💡 API 키 설정 방법
    - 프로젝트 루트의 `.env` 파일에 아래와 같이 입력하거나 사이드바에서 직접 입력할 수 있습니다:
    ```bash
    NAVER_CLIENT_ID=네이버에서_발급받은_Client_ID
    NAVER_CLIENT_SECRET=네이버에서_발급받은_Client_Secret
    ```
    """)
