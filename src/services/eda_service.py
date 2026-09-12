import io
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Tuple, Optional
from ..config.settings import APIConfig
from ..utils.text_utils import extract_keywords

class MarketEDAService:
    """수집된 네이버 시장 데이터에 대한 탐색적 데이터 분석(EDA) 서비스"""

    @staticmethod
    def get_summary_metrics(search_results: Dict[str, Dict[str, Any]]) -> pd.DataFrame:
        """
        각 키워드별 8대 채널의 total 검색 결과 건수를 종합하여 요약 데이터프레임을 생성합니다.
        """
        rows = []
        for kw, ch_map in search_results.items():
            total_sum = 0
            row = {"키워드": kw}
            for ch_code, ch_info in APIConfig.CHANNELS.items():
                ch_name = ch_info["name"]
                cnt = ch_map.get(ch_code, {}).get("total", 0)
                row[ch_name] = cnt
                total_sum += cnt
            row["총 버즈량"] = total_sum
            rows.append(row)
            
        df = pd.DataFrame(rows)
        if not df.empty and "총 버즈량" in df.columns:
            df = df.sort_values(by="총 버즈량", ascending=False).reset_index(drop=True)
        return df

    @staticmethod
    def get_channel_distribution(search_results: Dict[str, Dict[str, Any]]) -> pd.DataFrame:
        """
        키워드별 x 채널별 문서 수 분포 데이터프레임 (Long-format)
        """
        rows = []
        for kw, ch_map in search_results.items():
            for ch_code, ch_info in APIConfig.CHANNELS.items():
                ch_name = ch_info["name"]
                cnt = ch_map.get(ch_code, {}).get("total", 0)
                rows.append({
                    "키워드": kw,
                    "채널": ch_name,
                    "문서수": cnt,
                    "channel_code": ch_code
                })
        return pd.DataFrame(rows)

    @staticmethod
    def get_trend_dataframe(trend_result: Dict[str, Any]) -> pd.DataFrame:
        """
        데이터랩 검색어 트렌드 결과를 시계열 분석용 DataFrame으로 변환합니다.
        """
        if not trend_result or not trend_result.get("success"):
            return pd.DataFrame()
            
        rows = []
        for item in trend_result.get("results", []):
            title = item.get("title")
            for point in item.get("data", []):
                rows.append({
                    "날짜": point.get("period"),
                    "검색어": title,
                    "트렌드 지수": point.get("ratio")
                })
                
        df = pd.DataFrame(rows)
        if not df.empty:
            df["날짜"] = pd.to_datetime(df["날짜"])
            df = df.sort_values(by=["날짜", "검색어"]).reset_index(drop=True)
        return df

    @staticmethod
    def get_channel_dataframe(
        search_results: Dict[str, Dict[str, Any]],
        channel: str,
        keyword: Optional[str] = None
    ) -> pd.DataFrame:
        """
        특정 채널에 대해 모든 키워드(또는 지정 키워드)의 수집 아이템을 통합한 DataFrame을 반환합니다.
        """
        all_items = []
        for kw, ch_map in search_results.items():
            if keyword and kw != keyword:
                continue
            ch_data = ch_map.get(channel, {})
            items = ch_data.get("items", [])
            for it in items:
                all_items.append(it)
                
        if not all_items:
            return pd.DataFrame()
        return pd.DataFrame(all_items)

    @staticmethod
    def compute_descriptive_stats(df: pd.DataFrame) -> pd.DataFrame:
        """
        텍스트 길이, 단어 수, 어휘 다양성, 감성 지수에 대한 상세 기술통계표를 산출합니다.
        (count, mean, std, median, min, 25%, 75%, max, skewness, kurtosis)
        """
        if df.empty:
            return pd.DataFrame()

        target_cols = [
            ("title_len", "제목 글자수"),
            ("desc_len", "설명/본문 글자수"),
            ("total_len", "총 글자수"),
            ("word_count", "단어 수"),
            ("lexical_diversity", "어휘 다양성(TTR)"),
            ("sentiment_score", "감성 지수")
        ]

        stats_rows = []
        for col, label in target_cols:
            if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
                s = df[col].dropna()
                if len(s) > 0:
                    stats_rows.append({
                        "분석 항목": label,
                        "표본수(N)": int(s.count()),
                        "평균(Mean)": round(float(s.mean()), 2),
                        "표준편차(Std)": round(float(s.std(ddof=1) if len(s) > 1 else 0.0), 2),
                        "중앙값(Median)": round(float(s.median()), 2),
                        "최솟값(Min)": round(float(s.min()), 2),
                        "25% (Q1)": round(float(s.quantile(0.25)), 2),
                        "75% (Q3)": round(float(s.quantile(0.75)), 2),
                        "최댓값(Max)": round(float(s.max()), 2),
                        "왜도(Skewness)": round(float(s.skew() if len(s) > 2 else 0.0), 2),
                        "첨도(Kurtosis)": round(float(s.kurt() if len(s) > 3 else 0.0), 2)
                    })

        return pd.DataFrame(stats_rows)

    @staticmethod
    def compute_crosstab(
        df: pd.DataFrame,
        index_col: str = "keyword",
        columns_col: str = "source_name",
        top_n_cols: int = 10
    ) -> pd.DataFrame:
        """
        키워드 x 주요 범주(출처/요일 등)의 빈도 교차표(Crosstab)를 산출합니다.
        """
        if df.empty or index_col not in df.columns or columns_col not in df.columns:
            return pd.DataFrame()

        # 상위 N개 범주만 선별
        top_cats = df[columns_col].value_counts().head(top_n_cols).index.tolist()
        df_filtered = df[df[columns_col].isin(top_cats)]
        if df_filtered.empty:
            return pd.DataFrame()

        ct = pd.crosstab(
            df_filtered[index_col],
            df_filtered[columns_col],
            margins=True,
            margins_name="합계"
        )
        return ct

    @staticmethod
    def compute_pivot_table(
        df: pd.DataFrame,
        index_col: str = "keyword",
        columns_col: str = "day_of_week"
    ) -> pd.DataFrame:
        """
        키워드 x 요일/기간별 피봇테이블 (발행건수 및 평균 글자수)
        """
        if df.empty or index_col not in df.columns or columns_col not in df.columns:
            return pd.DataFrame()

        pivot = pd.pivot_table(
            df,
            index=index_col,
            columns=columns_col,
            values="title_len",
            aggfunc=["count", "mean"],
            fill_value=0
        )
        # 컬럼 멀티인덱스 정리
        pivot.columns = [f"{col[1]} ({'건수' if col[0] == 'count' else '평균글자수'})" for col in pivot.columns]
        return pivot.round(1)

    @staticmethod
    def compute_source_concentration(df: pd.DataFrame, source_col: str = "source_name", top_n: int = 15) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        언론사/작성자/도메인 집중도 분석 (발행건수, 점유율%, 누적점유율%, HHI 지수)
        """
        if df.empty or source_col not in df.columns:
            return pd.DataFrame(), {}

        counts = df[source_col].value_counts().reset_index()
        counts.columns = [source_col, "발행건수"]
        total_items = counts["발행건수"].sum()
        
        counts["점유율(%)"] = (counts["발행건수"] / total_items * 100).round(2)
        counts["누적점유율(%)"] = counts["점유율(%)"].cumsum().round(2)

        # HHI (허핀달-허쉬만 지수): 각 점유율(%)의 제곱합. 10,000점 만점
        # 1,500 미만: 경쟁적, 1,500~2,500: 다소 집중, 2,500 초과: 고도 집중
        hhi = float((counts["점유율(%)"] ** 2).sum())
        top3_share = float(counts["점유율(%)"].head(3).sum())
        top5_share = float(counts["점유율(%)"].head(5).sum())

        meta = {
            "total_sources": len(counts),
            "hhi_index": round(hhi, 1),
            "top3_share": round(top3_share, 2),
            "top5_share": round(top5_share, 2),
            "market_structure": "고도 과점/집중" if hhi > 2500 else ("다소 집중" if hhi > 1500 else "경쟁적 분산")
        }

        return counts.head(top_n), meta

    @staticmethod
    def compute_sentiment_summary(df: pd.DataFrame) -> pd.DataFrame:
        """키워드별 긍정/중립/부정 어조 감성 통계표"""
        if df.empty or "sentiment_label" not in df.columns or "keyword" not in df.columns:
            return pd.DataFrame()

        summary = []
        for kw, grp in df.groupby("keyword"):
            total = len(grp)
            counts = grp["sentiment_label"].value_counts()
            pos = counts.get("긍정", 0)
            neu = counts.get("중립", 0)
            neg = counts.get("부정", 0)
            avg_score = grp["sentiment_score"].mean() if "sentiment_score" in grp.columns else 0.0

            summary.append({
                "키워드": kw,
                "총 문서수": total,
                "긍정 건수": pos,
                "긍정 비중(%)": round(pos / total * 100, 2) if total else 0,
                "중립 건수": neu,
                "중립 비중(%)": round(neu / total * 100, 2) if total else 0,
                "부정 건수": neg,
                "부정 비중(%)": round(neg / total * 100, 2) if total else 0,
                "평균 감성 지수": round(float(avg_score), 3)
            })

        return pd.DataFrame(summary)

    @staticmethod
    def compute_outliers_summary(df: pd.DataFrame) -> pd.DataFrame:
        """가장 긴 제목, 가장 긴 본문, 최고/최저 감성 지수 이상치 요약표"""
        if df.empty:
            return pd.DataFrame()

        outliers = []
        if "title_len" in df.columns:
            max_t = df.loc[df["title_len"].idxmax()]
            min_t = df.loc[df["title_len"].idxmin()]
            outliers.append({
                "구분": "최대 제목 길이",
                "키워드": max_t.get("keyword", "-"),
                "측정값": f"{max_t.get('title_len', 0)} 자",
                "제목 / 출처": f"{max_t.get('title', '')[:35]}... ({max_t.get('source_name', '')})"
            })
            outliers.append({
                "구분": "최소 제목 길이",
                "키워드": min_t.get("keyword", "-"),
                "측정값": f"{min_t.get('title_len', 0)} 자",
                "제목 / 출처": f"{min_t.get('title', '')[:35]} ({min_t.get('source_name', '')})"
            })

        if "desc_len" in df.columns and df["desc_len"].max() > 0:
            max_d = df.loc[df["desc_len"].idxmax()]
            outliers.append({
                "구분": "최대 본문 요약 길이",
                "키워드": max_d.get("keyword", "-"),
                "측정값": f"{max_d.get('desc_len', 0)} 자",
                "제목 / 출처": f"{max_d.get('title', '')[:35]}... ({max_d.get('source_name', '')})"
            })

        if "sentiment_score" in df.columns:
            max_s = df.loc[df["sentiment_score"].idxmax()]
            min_s = df.loc[df["sentiment_score"].idxmin()]
            if max_s.get("sentiment_score", 0) > 0:
                outliers.append({
                    "구분": "최고 긍정 지수",
                    "키워드": max_s.get("keyword", "-"),
                    "측정값": f"+{max_s.get('sentiment_score', 0)}",
                    "제목 / 출처": f"{max_s.get('title', '')[:35]}... ({max_s.get('source_name', '')})"
                })
            if min_s.get("sentiment_score", 0) < 0:
                outliers.append({
                    "구분": "최고 부정 지수",
                    "키워드": min_s.get("keyword", "-"),
                    "측정값": f"{min_s.get('sentiment_score', 0)}",
                    "제목 / 출처": f"{min_s.get('title', '')[:35]}... ({min_s.get('source_name', '')})"
                })

        return pd.DataFrame(outliers)

    @staticmethod
    def analyze_top_words(
        search_results: Dict[str, Dict[str, Any]],
        keyword: str,
        channel: Optional[str] = None,
        top_n: int = 30
    ) -> List[Tuple[str, int]]:
        """특정 검색어 및 특정 채널의 텍스트에서 상위 핵심 단어를 추출합니다."""
        texts = []
        kw_data = search_results.get(keyword, {})
        for ch_key, ch_val in kw_data.items():
            if channel and ch_key != channel:
                continue
            for it in ch_val.get("items", []):
                t = it.get("title", "")
                d = it.get("description", "")
                if t:
                    texts.append(t)
                if d:
                    texts.append(d)

        custom_stop = {keyword.lower(), keyword.replace(" ", "")}
        return extract_keywords(texts, top_n=top_n, custom_stopwords=custom_stop)

    @staticmethod
    def generate_multisheet_excel(
        search_results: Dict[str, Dict[str, Any]],
        trend_df: pd.DataFrame
    ) -> bytes:
        """
        모든 채널의 원본 데이터 및 통계 요약을 1개의 다중 시트 Excel(.xlsx) 바이트 스트림으로 생성합니다.
        """
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            # 1. 종합 마켓 요약 시트
            summary_df = MarketEDAService.get_summary_metrics(search_results)
            if not summary_df.empty:
                summary_df.to_excel(writer, sheet_name="종합_마켓_요약", index=False)

            # 2. 검색어 트렌드 시계열 시트
            if not trend_df.empty:
                trend_df.to_excel(writer, sheet_name="검색어_트렌드", index=False)

            # 3. 채널별 시트 (최대 31자 시트명 제한 준수)
            for ch_code, ch_info in APIConfig.CHANNELS.items():
                ch_name = ch_info["name"]
                df_ch = MarketEDAService.get_channel_dataframe(search_results, ch_code)
                if not df_ch.empty:
                    # 엑셀 저장용 컬럼 정리
                    cols_to_drop = [c for c in ["thumbnail", "link", "originallink", "bloggerlink", "cafeurl"] if c in df_ch.columns]
                    save_df = df_ch.drop(columns=cols_to_drop, errors="ignore")
                    sheet_name = f"채널_{ch_name}"[:30]
                    save_df.to_excel(writer, sheet_name=sheet_name, index=False)

        output.seek(0)
        return output.getvalue()
