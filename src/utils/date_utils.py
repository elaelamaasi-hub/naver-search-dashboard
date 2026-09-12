from datetime import datetime, date
from typing import Optional, List, Dict, Any
from email.utils import parsedate_to_datetime

def parse_naver_date(raw_date: Optional[str]) -> Optional[date]:
    """
    네이버 API의 다양한 날짜 포맷을 datetime.date 객체로 변환합니다.
    1. RFC 822: 'Wed, 09 Sep 2026 14:20:00 +0900' (뉴스 등)
    2. YYYYMMDD: '20260909' (블로그 등)
    3. ISO: '2026-09-09'
    """
    if not raw_date:
        return None
        
    raw_str = str(raw_date).strip()
    
    # 1. YYYYMMDD 포맷
    if len(raw_str) == 8 and raw_str.isdigit():
        try:
            return datetime.strptime(raw_str, "%Y%m%d").date()
        except ValueError:
            pass
            
    # 2. RFC 822 (pubDate) 포맷
    try:
        dt = parsedate_to_datetime(raw_str)
        return dt.date()
    except Exception:
        pass
        
    # 3. YYYY-MM-DD 포맷
    try:
        return datetime.strptime(raw_str[:10], "%Y-%m-%d").date()
    except ValueError:
        pass
        
    return None

def filter_by_date_range(
    items: List[Dict[str, Any]],
    date_key: Optional[str],
    start_date: Optional[date],
    end_date: Optional[date]
) -> List[Dict[str, Any]]:
    """
    아이템 목록 중 날짜 범위 [start_date, end_date]에 해당하는 항목만 필터링합니다.
    date_key가 없거나 아이템에 날짜가 없으면 그대로 포함합니다.
    """
    if not date_key or not start_date or not end_date:
        return items
        
    filtered = []
    for item in items:
        raw_val = item.get(date_key)
        item_date = parse_naver_date(raw_val)
        if item_date is None:
            # 날짜 파싱이 안 되는 경우 기본 보존
            filtered.append(item)
        elif start_date <= item_date <= end_date:
            filtered.append(item)
            
    return filtered
