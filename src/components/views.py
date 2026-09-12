import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from typing import Dict, Any, List, Tuple

from ..config.settings import APIConfig
from ..utils.text_utils import generate_wordcloud_image

def render_summary_metrics(summary_df: pd.DataFrame, trend_df: pd.DataFrame):
    """주요 시장 지표 요약 메트릭 카드 렌더링"""
    if summary_df.empty:
        return

    col1, col2, col3, col4 = st.columns(4)

    total_market_buzz = summary_df["총 버즈량"].sum() if "총 버즈량" in summary_df.columns else 0
    top_keyword_row = summary_df.iloc[0] if not summary_df.empty else None
    top_keyword_name = top_keyword_row["키워드"] if top_keyword_row is not None else "-"
    top_keyword_buzz = top_keyword_row["총 버즈량"] if top_keyword_row is not None else 0

    with col1:
        st.metric(
            label="총 검색 문서량 (전체 채널)",
            value=f"{total_market_buzz:,} 건"
        )

    with col2:
        st.metric(
            label="버즈량 1위 키워드",
            value=top_keyword_name,
            delta=f"{top_keyword_buzz:,} 건"
        )

    with col3:
        if not trend_df.empty and "트렌드 지수" in trend_df.columns:
            peak_row = trend_df.sort_values(by="트렌드 지수", ascending=False).iloc[0]
            st.metric(
                label="최고 트렌드 지수 기록",
                value=f"{peak_row['검색어']} ({peak_row['트렌드 지수']})",
                delta=str(peak_row['날짜'].date() if hasattr(peak_row['날짜'], 'date') else peak_row['날짜'])
            )
        else:
            st.metric(label="트렌드 분석 대상", value=f"{len(summary_df)} 개 키워드")

    with col4:
        # 가장 문서 수가 많은 채널 산출
        channel_names = [info["name"] for info in APIConfig.CHANNELS.values()]
        avail_channels = [c for c in channel_names if c in summary_df.columns]
        if avail_channels:
            channel_totals = summary_df[avail_channels].sum()
            top_channel = channel_totals.idxmax()
            top_ch_count = channel_totals.max()
            st.metric(
                label="최다 유통 채널",
                value=top_channel,
                delta=f"{top_ch_count:,} 건"
            )
        else:
            st.metric(label="조회 채널 수", value="8개 채널")

def render_wordcloud_section(word_freqs: List[Tuple[str, int]], keyword: str):
    """워드클라우드 섹션 렌더링"""
    if not word_freqs:
        st.info(f"'{keyword}'에 대한 텍스트 분석 데이터가 충분하지 않습니다.")
        return

    freq_dict = dict(word_freqs)
    wc = generate_wordcloud_image(freq_dict)
    
    if wc is not None:
        fig, ax = plt.subplots(figsize=(10, 5), dpi=150)
        ax.imshow(wc, interpolation="bilinear")
        ax.axis("off")
        st.pyplot(fig, use_container_width=True)
        plt.close(fig)
    else:
        st.warning("워드클라우드 이미지를 생성할 수 없어 빈도수 표로 대체합니다.")
        freq_df = pd.DataFrame(word_freqs, columns=["키워드", "빈도"])
        st.dataframe(freq_df, use_container_width=True)

def render_channel_details_tab(
    search_results: Dict[str, Dict[str, Any]],
    selected_keyword: str
):
    """
    선택된 키워드에 대해 8개 채널별 세부 수집 결과(뉴스, 블로그, 카페 등) 및 이미지 갤러리를 탭으로 렌더링
    """
    kw_data = search_results.get(selected_keyword, {})
    if not kw_data:
        st.info("수집된 채널 데이터가 없습니다.")
        return

    # 8개 채널 탭 생성
    tabs = st.tabs([
        "📰 뉴스",
        "📝 블로그",
        "☕ 카페글",
        "💬 지식iN",
        "🌐 웹문서",
        "🖼️ 이미지 갤러리",
        "📍 지역(업체)",
        "📖 백과사전"
    ])

    tab_channel_keys = [
        "news", "blog", "cafearticle", "kin", "webkr", "image", "local", "encyc"
    ]

    for tab, ch_key in zip(tabs, tab_channel_keys):
        with tab:
            ch_res = kw_data.get(ch_key, {})
            ch_name = ch_res.get("channel_name", ch_key)
            total_count = ch_res.get("total", 0)
            items = ch_res.get("items", [])
            error = ch_res.get("error")

            if error:
                st.error(f"데이터 조회 실패: {error}")
                continue

            st.caption(f"총 {total_count:,}건 중 수집된 {len(items)}건 표시")

            if not items:
                st.info(f"수집된 {ch_name} 데이터가 없습니다.")
                continue

            # CSV 다운로드 버튼 제공
            df_items = pd.DataFrame(items)
            csv_data = df_items.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                label=f"📥 {ch_name} 데이터 CSV 다운로드",
                data=csv_data,
                file_name=f"{selected_keyword}_{ch_key}_{pd.Timestamp.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                key=f"csv_dl_{selected_keyword}_{ch_key}"
            )

            # 이미지 채널의 경우 이미지 갤러리 렌더링
            if ch_key == "image":
                cols = st.columns(4)
                for i, it in enumerate(items):
                    with cols[i % 4]:
                        thumb = it.get("thumbnail") or it.get("link")
                        title = it.get("title", f"이미지 {i+1}")
                        link = it.get("link", "#")
                        try:
                            st.image(thumb, use_container_width=True)
                            st.caption(f"[{title}]({link})")
                        except Exception:
                            st.write(f"[{title}]({link})")
            else:
                # 일반 채널 리스트 뷰
                for idx, it in enumerate(items[:50]): # 최대 50개 카드 렌더링
                    title = it.get("title", "제목 없음")
                    desc = it.get("description", "")
                    link = it.get("link") or it.get("originallink", "#")
                    date_str = it.get("parsed_date") or it.get("pubDate") or it.get("postdate", "")

                    with st.container():
                        sub_col1, sub_col2 = st.columns([4, 1])
                        with sub_col1:
                            st.markdown(f"**[{idx+1}] [{title}]({link})**")
                        with sub_col2:
                            if date_str:
                                st.caption(f"📅 {date_str}")
                        if desc:
                            st.caption(desc)

                        # 부가 정보 (블로거명, 카페명, 주소 등)
                        extra_info = []
                        if "bloggername" in it and it["bloggername"]:
                            extra_info.append(f"작성자: {it['bloggername']}")
                        if "cafename" in it and it["cafename"]:
                            extra_info.append(f"카페: {it['cafename']}")
                        if "roadAddress" in it and it["roadAddress"]:
                            extra_info.append(f"주소: {it['roadAddress']}")
                        elif "address" in it and it["address"]:
                            extra_info.append(f"주소: {it['address']}")
                            
                        if extra_info:
                            st.caption(" • ".join(extra_info))
                        st.divider()
