from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from typing import Dict, Any, List, Optional
import pandas as pd

from ..config.settings import APIConfig
from ..api.naver_client import NaverSearchClient
from ..api.datalab_client import NaverDataLabClient
from ..utils.text_utils import clean_html, extract_domain, extract_text_features
from ..utils.date_utils import parse_naver_date, filter_by_date_range

DAY_OF_WEEK_KOR = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]

class MarketDataCollector:
    """멀티 키워드 및 멀티 채널 데이터 통합 수집기"""

    def __init__(self, headers: Dict[str, str]):
        self.headers = headers
        self.search_client = NaverSearchClient(headers)
        self.datalab_client = NaverDataLabClient(headers)

    def collect_keyword_channel(
        self,
        keyword: str,
        channel: str,
        display: int = 100,
        sort: str = "sim",
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """단일 키워드와 단일 채널에 대해 데이터를 수집하고 정제합니다."""
        res = self.search_client.search_channel(
            channel=channel,
            query=keyword,
            display=display,
            sort=sort
        )
        
        if not res.get("success"):
            return {
                "keyword": keyword,
                "channel": channel,
                "channel_name": APIConfig.CHANNELS.get(channel, {}).get("name", channel),
                "total": 0,
                "items": [],
                "error": res.get("error", "알 수 없는 오류")
            }

        items = res.get("items", [])
        cleaned_items = []
        date_key = APIConfig.CHANNELS.get(channel, {}).get("date_key")

        for it in items:
            item_copy = it.copy()
            # 텍스트 HTML 엔티티 및 태그 정제
            for field in ["title", "description", "bloggername", "cafename", "address", "roadAddress", "category"]:
                if field in item_copy:
                    item_copy[field] = clean_html(item_copy[field])
            
            # 날짜 및 요일 정규화
            parsed_d = None
            if date_key and date_key in item_copy:
                parsed_d = parse_naver_date(item_copy[date_key])
            elif "pubDate" in item_copy:
                parsed_d = parse_naver_date(item_copy["pubDate"])
            elif "postdate" in item_copy:
                parsed_d = parse_naver_date(item_copy["postdate"])
                
            item_copy["parsed_date"] = str(parsed_d) if parsed_d else ""
            item_copy["day_of_week"] = DAY_OF_WEEK_KOR[parsed_d.weekday()] if parsed_d else "미상"
            item_copy["keyword"] = keyword
            item_copy["channel"] = channel
            item_copy["channel_name"] = APIConfig.CHANNELS.get(channel, {}).get("name", channel)

            # 출처/게시자/도메인 표준화
            raw_link = item_copy.get("originallink") or item_copy.get("link") or ""
            domain = extract_domain(raw_link)
            item_copy["domain"] = domain

            if channel == "news":
                item_copy["source_name"] = domain
            elif channel == "blog":
                item_copy["source_name"] = item_copy.get("bloggername") or domain or "블로거"
            elif channel == "cafearticle":
                item_copy["source_name"] = item_copy.get("cafename") or domain or "네이버카페"
            elif channel == "local":
                item_copy["source_name"] = item_copy.get("category") or "지역업체"
            elif channel == "webkr":
                item_copy["source_name"] = domain
            elif channel == "encyc":
                item_copy["source_name"] = "백과사전"
            elif channel == "kin":
                item_copy["source_name"] = "지식iN"
            elif channel == "image":
                item_copy["source_name"] = domain
            else:
                item_copy["source_name"] = "기타"

            # 텍스트 통계 지표 및 감성 분석
            title_text = item_copy.get("title", "")
            desc_text = item_copy.get("description", "")
            text_stats = extract_text_features(title_text, desc_text)
            item_copy.update(text_stats)

            cleaned_items.append(item_copy)

        # 날짜 필터링 적용
        if start_date and end_date and date_key:
            cleaned_items = filter_by_date_range(cleaned_items, "parsed_date", start_date, end_date)

        return {
            "keyword": keyword,
            "channel": channel,
            "channel_name": APIConfig.CHANNELS.get(channel, {}).get("name", channel),
            "total": res.get("total", 0),
            "items": cleaned_items,
            "error": None
        }

    def collect_all(
        self,
        keywords: List[str],
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        time_unit: str = "date",
        sort: str = "sim",
        display: int = 100
    ) -> Dict[str, Any]:
        """
        모든 키워드에 대해 8대 검색 채널과 데이터랩 트렌드를 병렬 수집합니다.
        """
        channels = list(APIConfig.CHANNELS.keys())
        search_results: Dict[str, Dict[str, Any]] = {kw: {} for kw in keywords}
        
        # 1. 8대 검색 채널 병렬 수집
        with ThreadPoolExecutor(max_workers=8) as executor:
            future_to_req = {}
            for kw in keywords:
                for ch in channels:
                    future = executor.submit(
                        self.collect_keyword_channel,
                        keyword=kw,
                        channel=ch,
                        display=display,
                        sort=sort,
                        start_date=start_date,
                        end_date=end_date
                    )
                    future_to_req[future] = (kw, ch)

            for future in as_completed(future_to_req):
                kw, ch = future_to_req[future]
                try:
                    res = future.result()
                    search_results[kw][ch] = res
                except Exception as e:
                    search_results[kw][ch] = {
                        "keyword": kw,
                        "channel": ch,
                        "channel_name": APIConfig.CHANNELS.get(ch, {}).get("name", ch),
                        "total": 0,
                        "items": [],
                        "error": str(e)
                    }

        # 2. 데이터랩 트렌드 수집
        trend_result = None
        if start_date and end_date:
            keyword_groups = [
                {"groupName": kw, "keywords": [kw]}
                for kw in keywords[:5]
            ]
            trend_result = self.datalab_client.get_search_trend(
                keyword_groups=keyword_groups,
                start_date=start_date.strftime("%Y-%m-%d"),
                end_date=end_date.strftime("%Y-%m-%d"),
                time_unit=time_unit
            )

        return {
            "search_results": search_results,
            "trend_result": trend_result
        }
