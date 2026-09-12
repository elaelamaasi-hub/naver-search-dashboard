import streamlit as st
import pandas as pd
from typing import Dict, Any, List

from ..config.settings import APIConfig
from ..services.eda_service import MarketEDAService
from .charts import (
    render_timeseries_chart,
    render_boxplot_chart,
    render_top_sources_barchart,
    render_crosstab_heatmap,
    render_word_freq_chart,
    render_length_scatter_chart
)

def render_channel_deep_eda(
    search_results: Dict[str, Dict[str, Any]],
    channel_code: str,
    keywords: List[str]
):
    """
    특정 채널에 대한 그래프 5개 이상, 통계표 5개 이상의 심층 EDA 페이지를 렌더링합니다.
    (파이차트 완전 배제)
    """
    ch_info = APIConfig.CHANNELS.get(channel_code, {"name": channel_code})
    channel_name = ch_info["name"]

    # 1. 채널 데이터프레임 로드
    df_all = MarketEDAService.get_channel_dataframe(search_results, channel_code)

    if df_all.empty:
        st.warning(f"[{channel_name}] 수집된 데이터가 없습니다. 검색어나 기간을 확인해 주세요.")
        return

    # 상단 컨트롤: 키워드 필터 (전체 비교 vs 개별 키워드)
    col_f1, col_f2 = st.columns([2, 3])
    with col_f1:
        kw_filter = st.selectbox(
            "분석 대상 키워드 필터",
            options=["전체 키워드 비교"] + keywords,
            key=f"filter_{channel_code}"
        )
    with col_f2:
        st.caption(f"💡 현재 수집 건수: **{len(df_all):,}건** | 공식 채널 총 문서량: **{df_all['total'].max() if 'total' in df_all.columns else 0:,}건**")

    df = df_all if kw_filter == "전체 키워드 비교" else df_all[df_all["keyword"] == kw_filter]
    if df.empty:
        st.info("선택한 조건에 해당하는 데이터가 없습니다.")
        return

    # --- [섹션 1] 핵심 기술통계 & 파레토 집중도 지표 (Key Metrics) ---
    st.markdown(f"### 📊 1. [{channel_name}] 기술통계 및 시장 집중도 요약")
    
    source_col = "source_name" if "source_name" in df.columns else "domain"
    conc_df, conc_meta = MarketEDAService.compute_source_concentration(df, source_col=source_col)
    
    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    with m_col1:
        st.metric("분석 표본 수", f"{len(df):,} 건")
    with m_col2:
        st.metric("평균 본문 글자수", f"{df['desc_len'].mean():.1f} 자" if 'desc_len' in df.columns else "-")
    with m_col3:
        if conc_meta:
            st.metric("출처 집중도 (HHI 지수)", f"{conc_meta['hhi_index']:,.0f}", delta=conc_meta['market_structure'])
        else:
            st.metric("출처 집중도", "-")
    with m_col4:
        if "sentiment_score" in df.columns:
            avg_sent = df["sentiment_score"].mean()
            sent_label = "긍정 우세" if avg_sent > 0.05 else ("부정 우세" if avg_sent < -0.05 else "중립")
            st.metric("평균 감성 지수", f"{avg_sent:+.3f}", delta=sent_label)
        else:
            st.metric("감성 지수", "-")

    # --- [섹션 2] 통계표 5개 이상 (5+ Statistical Tables) ---
    st.markdown(f"### 📋 2. [{channel_name}] 심층 통계 분석표 (총 6종)")

    t_tab1, t_tab2, t_tab3, t_tab4, t_tab5, t_tab6 = st.tabs([
        "① 종합 기술통계표",
        "② 키워드 x 출처 교차표",
        "③ 요일별 피봇테이블",
        "④ 출처 집중도 및 파레토 분석표",
        "⑤ 텍스트 감성(어조) 분석표",
        "⑥ 텍스트 극단값(이상치) 요약표"
    ])

    with t_tab1:
        st.markdown("#### [표 1] 텍스트 길이 및 정량 지표 기술통계 (Descriptive Statistics)")
        desc_stats = MarketEDAService.compute_descriptive_stats(df)
        st.dataframe(desc_stats, use_container_width=True)

    with t_tab2:
        st.markdown("#### [표 2] 키워드 x 상위 출처 교차 빈도표 (Crosstab)")
        crosstab_df = MarketEDAService.compute_crosstab(df, index_col="keyword", columns_col=source_col, top_n_cols=8)
        if not crosstab_df.empty:
            st.dataframe(crosstab_df.style.highlight_max(axis=1, color="#E0F2FE"), use_container_width=True)
        else:
            st.info("교차표를 생성할 범주 데이터가 부족합니다.")

    with t_tab3:
        st.markdown("#### [표 3] 키워드 x 요일별 발행 건수 및 평균 글자수 피봇테이블 (Pivot Table)")
        pivot_df = MarketEDAService.compute_pivot_table(df, index_col="keyword", columns_col="day_of_week")
        if not pivot_df.empty:
            st.dataframe(pivot_df, use_container_width=True)
        else:
            st.info("날짜 정보가 없어 요일 피봇테이블을 생성할 수 없습니다.")

    with t_tab4:
        st.markdown("#### [표 4] 상위 출처 발행 점유율 및 누적 파레토(Pareto) 분석표")
        if not conc_df.empty:
            st.dataframe(conc_df.style.bar(subset=["점유율(%)"], color="#A7F3D0"), use_container_width=True)
            st.caption("※ HHI(허핀달-허쉬만) 지수: 1,500 미만(경쟁적 분산), 1,500~2,500(다소 집중), 2,500 초과(고도 과점)")
        else:
            st.info("출처 데이터가 부족합니다.")

    with t_tab5:
        st.markdown("#### [표 5] 키워드별 긍정/중립/부정 어조 감성 통계표")
        sent_df = MarketEDAService.compute_sentiment_summary(df)
        if not sent_df.empty:
            st.dataframe(sent_df, use_container_width=True)
        else:
            st.info("감성 분석 데이터가 없습니다.")

    with t_tab6:
        st.markdown("#### [표 6] 최대/최소 글자수 및 극단 감성 지수 항목 (Outliers)")
        outliers_df = MarketEDAService.compute_outliers_summary(df)
        if not outliers_df.empty:
            st.dataframe(outliers_df, use_container_width=True)
        else:
            st.info("이상치 데이터가 없습니다.")

    st.markdown("<br>", unsafe_allow_html=True)

    # --- [섹션 3] 인터랙티브 그래프 5개 이상 (5+ Non-Pie Graphs) ---
    st.markdown(f"### 📈 3. [{channel_name}] 다차원 시각화 분석 (파이차트 제외, 총 6종)")

    # 1행: 시계열 추이 라인 차트 & 텍스트 길이 박스플롯
    g_col1, g_col2 = st.columns(2)
    with g_col1:
        st.markdown("#### [그래프 1] 날짜별 문서 발행량 추이")
        st.plotly_chart(
            render_timeseries_chart(df, channel_name),
            use_container_width=True,
            key=f"g1_ts_{channel_code}"
        )
    with g_col2:
        st.markdown("#### [그래프 2] 키워드별 본문 글자수 분포 (Box Plot)")
        st.plotly_chart(
            render_boxplot_chart(df, col="desc_len", col_name="설명/본문 글자수"),
            use_container_width=True,
            key=f"g2_box_{channel_code}"
        )

    # 2행: 상위 출처 가로 막대 차트 & 교차표 히트맵
    g_col3, g_col4 = st.columns(2)
    with g_col3:
        st.markdown(f"#### [그래프 3] 상위 {channel_name} 출처/작성자 순위")
        st.plotly_chart(
            render_top_sources_barchart(df, channel_name, top_n=12),
            use_container_width=True,
            key=f"g3_src_{channel_code}"
        )
    with g_col4:
        st.markdown("#### [그래프 4] 키워드 x 상위 출처 활동 히트맵 (Heatmap)")
        if not crosstab_df.empty:
            st.plotly_chart(
                render_crosstab_heatmap(crosstab_df, title=f"{channel_name} 키워드 x 출처 활동 매트릭스"),
                use_container_width=True,
                key=f"g4_hm_{channel_code}"
            )
        else:
            st.info("히트맵을 렌더링할 데이터가 충분하지 않습니다.")

    # 3행: 핵심 연관 키워드 막대 차트 & 글자수 상관관계 산점도
    g_col5, g_col6 = st.columns(2)
    with g_col5:
        st.markdown("#### [그래프 5] 핵심 연관 키워드 TOP 15")
        target_kw = keywords[0] if kw_filter == "전체 키워드 비교" else kw_filter
        top_words = MarketEDAService.analyze_top_words(search_results, target_kw, channel=channel_code, top_n=15)
        st.plotly_chart(
            render_word_freq_chart(top_words, target_kw, channel_name=channel_name),
            use_container_width=True,
            key=f"g5_wf_{channel_code}"
        )
    with g_col6:
        st.markdown("#### [그래프 6] 제목 글자수 vs 본문 글자수 상관관계 산점도 (Scatter)")
        st.plotly_chart(
            render_length_scatter_chart(df, channel_name),
            use_container_width=True,
            key=f"g6_sc_{channel_code}"
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # --- [섹션 4] 원본 데이터 탐색 및 CSV 다운로드 ---
    with st.expander(f"📥 [{channel_name}] 원본 데이터 브라우징 및 CSV 다운로드", expanded=False):
        col_d1, col_d2 = st.columns([3, 1])
        with col_d1:
            search_query = st.text_input(f"데이터 내 텍스트 검색 ({channel_name})", key=f"search_{channel_code}")
        with col_d2:
            csv_bytes = df.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                label=f"📥 {channel_name} 전체 CSV 다운로드",
                data=csv_bytes,
                file_name=f"naver_{channel_code}_eda_{pd.Timestamp.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                key=f"dl_csv_{channel_code}"
            )

        display_df = df.copy()
        if search_query:
            display_df = display_df[
                display_df["title"].str.contains(search_query, case=False, na=False) |
                display_df["description"].str.contains(search_query, case=False, na=False)
            ]

        # 이미지 채널의 경우 4열 갤러리 추가 표출
        if channel_code == "image":
            st.markdown("#### 🖼️ 이미지 갤러리 미리보기")
            img_cols = st.columns(4)
            for i, it in enumerate(display_df.to_dict("records")[:24]):
                with img_cols[i % 4]:
                    thumb = it.get("thumbnail") or it.get("link")
                    title = it.get("title", f"이미지 {i+1}")
                    link = it.get("link", "#")
                    try:
                        st.image(thumb, use_container_width=True)
                        st.caption(f"[{title[:20]}...]({link})")
                    except Exception:
                        st.write(f"[{title[:20]}]({link})")

        # 테이블 표시
        view_cols = [c for c in ["keyword", "title_clean", "source_name", "parsed_date", "day_of_week", "desc_len", "sentiment_label", "link"] if c in display_df.columns]
        st.dataframe(display_df[view_cols] if view_cols else display_df, use_container_width=True)
