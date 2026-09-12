import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from typing import List, Tuple, Optional

# 일관되고 미려한 모던 테마 컬러 팔레트
COLOR_PALETTE = [
    "#03C75A", # 네이버 그린
    "#3B82F6", # 인디고 블루
    "#F59E0B", # 앰버 오렌지
    "#EC4899", # 핑크
    "#8B5CF6", # 퍼플
    "#10B981", # 에메랄드
    "#6366F1", # 바이올렛
    "#14B8A6"  # 틸
]

def render_trend_chart(trend_df: pd.DataFrame) -> go.Figure:
    """데이터랩 검색어 트렌드 시계열 인터랙티브 라인 차트"""
    if trend_df.empty:
        fig = go.Figure()
        fig.update_layout(title="트렌드 데이터가 없습니다")
        return fig

    fig = px.line(
        trend_df,
        x="날짜",
        y="트렌드 지수",
        color="검색어",
        markers=True,
        color_discrete_sequence=COLOR_PALETTE,
        title="<b>네이버 데이터랩 검색어 트렌드 추이</b> (상대 검색 비율 0~100)"
    )
    fig.update_layout(
        template="plotly_white",
        hovermode="x unified",
        margin=dict(l=20, r=20, t=50, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(showgrid=True, gridcolor="#F3F4F6", title="일자"),
        yaxis=dict(showgrid=True, gridcolor="#F3F4F6", title="트렌드 지수 (최대 100)")
    )
    fig.update_traces(line=dict(width=2.5), marker=dict(size=6))
    return fig

def render_channel_bar_chart(dist_df: pd.DataFrame) -> go.Figure:
    """키워드별 8대 채널 문서 수 비교 막대 차트"""
    if dist_df.empty:
        return go.Figure()

    fig = px.bar(
        dist_df,
        x="채널",
        y="문서수",
        color="키워드",
        barmode="group",
        color_discrete_sequence=COLOR_PALETTE,
        title="<b>채널별 총 검색 문서 수(Total Count) 비교</b>"
    )
    fig.update_layout(
        template="plotly_white",
        margin=dict(l=20, r=20, t=50, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(title="검색 채널"),
        yaxis=dict(showgrid=True, gridcolor="#F3F4F6", title="누적 문서 수 (건)")
    )
    return fig

def render_channel_share_bar_chart(dist_df: pd.DataFrame, keyword: Optional[str] = None) -> go.Figure:
    """
    [파이차트 대체] 채널별 점유율을 나타내는 100% 누적 가로 막대 차트
    """
    if dist_df.empty:
        return go.Figure()

    df_plot = dist_df.copy()
    if keyword:
        df_plot = df_plot[df_plot["키워드"] == keyword]

    # 키워드별 합계로 나누어 점유율(%) 계산
    totals = df_plot.groupby("키워드")["문서수"].transform("sum")
    df_plot["점유율(%)"] = (df_plot["문서수"] / totals * 100).round(1)

    fig = px.bar(
        df_plot,
        y="키워드",
        x="점유율(%)",
        color="채널",
        orientation="h",
        color_discrete_sequence=COLOR_PALETTE,
        title="<b>채널별 버즈 점유율(Share of Voice, %)</b>",
        text="점유율(%)"
    )
    fig.update_layout(
        template="plotly_white",
        barmode="stack",
        margin=dict(l=20, r=20, t=50, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(title="점유 비중 (%)", range=[0, 100]),
        yaxis=dict(title="")
    )
    fig.update_traces(texttemplate="%{text}%", textposition="inside")
    return fig

def render_timeseries_chart(df: pd.DataFrame, channel_name: str) -> go.Figure:
    """날짜별 문서 발행량 추이 라인/영역 차트"""
    if df.empty or "parsed_date" not in df.columns or "keyword" not in df.columns:
        return go.Figure()

    df_valid = df[df["parsed_date"] != ""].copy()
    if df_valid.empty:
        return go.Figure()

    ts_counts = df_valid.groupby(["parsed_date", "keyword"]).size().reset_index(name="발행건수")
    ts_counts["parsed_date"] = pd.to_datetime(ts_counts["parsed_date"])
    ts_counts = ts_counts.sort_values(by="parsed_date")

    fig = px.line(
        ts_counts,
        x="parsed_date",
        y="발행건수",
        color="keyword",
        markers=True,
        color_discrete_sequence=COLOR_PALETTE,
        title=f"<b>[{channel_name}] 날짜별 문서 발행 추이</b>"
    )
    fig.update_layout(
        template="plotly_white",
        hovermode="x unified",
        margin=dict(l=20, r=20, t=50, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(title="발행일자", showgrid=True, gridcolor="#F3F4F6"),
        yaxis=dict(title="수집 문서 수 (건)", showgrid=True, gridcolor="#F3F4F6")
    )
    fig.update_traces(line=dict(width=2.5), marker=dict(size=6))
    return fig

def render_boxplot_chart(df: pd.DataFrame, col: str = "desc_len", col_name: str = "본문 글자수") -> go.Figure:
    """키워드별 텍스트 길이 분포 박스플롯 (사분위수 및 이상치 시각화)"""
    if df.empty or col not in df.columns:
        return go.Figure()

    fig = px.box(
        df,
        x="keyword",
        y=col,
        color="keyword",
        points="all", # 모든 데이터 포인트 산점 표시
        color_discrete_sequence=COLOR_PALETTE,
        title=f"<b>키워드별 {col_name} 분포 (Box Plot)</b>"
    )
    fig.update_layout(
        template="plotly_white",
        margin=dict(l=20, r=20, t=50, b=20),
        showlegend=False,
        xaxis=dict(title="검색 키워드"),
        yaxis=dict(title=f"{col_name} (자)", showgrid=True, gridcolor="#F3F4F6")
    )
    return fig

def render_top_sources_barchart(df: pd.DataFrame, channel_name: str, top_n: int = 12) -> go.Figure:
    """상위 출처/작성자/도메인 순위 가로 막대 차트"""
    if df.empty or "source_name" not in df.columns:
        return go.Figure()

    counts = df.groupby(["source_name", "keyword"]).size().reset_index(name="건수")
    top_sources = df["source_name"].value_counts().head(top_n).index.tolist()
    counts = counts[counts["source_name"].isin(top_sources)]
    
    # 정렬을 위해 전체 건수 순서 정의
    order = df["source_name"].value_counts().head(top_n).index.tolist()[::-1]

    fig = px.bar(
        counts,
        y="source_name",
        x="건수",
        color="keyword",
        orientation="h",
        category_orders={"source_name": order},
        color_discrete_sequence=COLOR_PALETTE,
        title=f"<b>[{channel_name}] 상위 출처/작성자 TOP {top_n} 발행 분포</b>"
    )
    fig.update_layout(
        template="plotly_white",
        margin=dict(l=20, r=20, t=50, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(title="발행 건수 (건)", showgrid=True, gridcolor="#F3F4F6"),
        yaxis=dict(title="")
    )
    return fig

def render_crosstab_heatmap(ct: pd.DataFrame, title: str = "키워드 교차 히트맵") -> go.Figure:
    """교차표(Crosstab) 2D 히트맵 시각화"""
    if ct.empty:
        return go.Figure()

    # 합계 행과 열 제거 후 히트맵 표현
    ct_clean = ct.copy()
    if "합계" in ct_clean.index:
        ct_clean = ct_clean.drop(index="합계")
    if "합계" in ct_clean.columns:
        ct_clean = ct_clean.drop(columns="합계")

    fig = px.imshow(
        ct_clean,
        text_auto=True,
        aspect="auto",
        color_continuous_scale="Blues",
        title=f"<b>{title}</b>"
    )
    fig.update_layout(
        margin=dict(l=20, r=20, t=50, b=20),
        xaxis=dict(title=""),
        yaxis=dict(title="")
    )
    return fig

def render_word_freq_chart(word_freqs: List[Tuple[str, int]], keyword: str, channel_name: str = "") -> go.Figure:
    """핵심 연관 단어 빈도수 수평 막대 차트"""
    if not word_freqs:
        return go.Figure()

    top_words = word_freqs[:15][::-1]
    words = [w[0] for w in top_words]
    counts = [w[1] for w in top_words]

    fig = go.Figure(go.Bar(
        x=counts,
        y=words,
        orientation="h",
        marker=dict(
            color=counts,
            colorscale="Teal",
            line=dict(color="#059669", width=1)
        ),
        text=counts,
        textposition="auto"
    ))

    ch_text = f" [{channel_name}]" if channel_name else ""
    fig.update_layout(
        template="plotly_white",
        title=f"<b>'{keyword}'{ch_text} 핵심 연관 키워드 TOP 15</b>",
        margin=dict(l=20, r=20, t=40, b=20),
        xaxis=dict(showgrid=True, gridcolor="#F3F4F6", title="등장 빈도 (회)"),
        yaxis=dict(title="")
    )
    return fig

def render_length_scatter_chart(df: pd.DataFrame, channel_name: str) -> go.Figure:
    """글자수 vs 단어수 산점도(Scatter Plot) 및 상관관계 추세선"""
    if df.empty or "title_len" not in df.columns or "desc_len" not in df.columns:
        return go.Figure()

    fig = px.scatter(
        df,
        x="title_len",
        y="desc_len",
        color="keyword",
        size="word_count",
        hover_data=["title", "source_name"],
        color_discrete_sequence=COLOR_PALETTE,
        title=f"<b>[{channel_name}] 제목 글자수 vs 본문 글자수 상관관계 산점도</b>"
    )
    fig.update_layout(
        template="plotly_white",
        margin=dict(l=20, r=20, t=50, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(title="제목 글자수 (자)", showgrid=True, gridcolor="#F3F4F6"),
        yaxis=dict(title="설명/본문 글자수 (자)", showgrid=True, gridcolor="#F3F4F6")
    )
    return fig
