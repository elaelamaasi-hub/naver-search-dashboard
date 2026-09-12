import os
from typing import Optional, Dict
from dotenv import load_dotenv

# Load .env file automatically
load_dotenv(override=True)

class APIConfig:
    """네이버 API 설정 및 엔드포인트 정의"""
    # 1. 네이버 클라우드 플랫폼 NAVER API HUB
    NCLOUD_APIHUB_BASE_URL = "https://naverapihub.apigw.ntruss.com"
    # 2. 네이버 개발자 센터 레거시 오픈 API
    LEGACY_OPENAPI_BASE_URL = "https://openapi.naver.com/v1"

    # 채널별 표시 이름 및 최대 수집 가능 건수
    CHANNELS = {
        "news": {"name": "뉴스", "max_display": 100, "has_date": True, "date_key": "pubDate"},
        "blog": {"name": "블로그", "max_display": 100, "has_date": True, "date_key": "postdate"},
        "webkr": {"name": "웹문서", "max_display": 100, "has_date": False, "date_key": None},
        "image": {"name": "이미지", "max_display": 100, "has_date": False, "date_key": None},
        "kin": {"name": "지식iN", "max_display": 100, "has_date": False, "date_key": None},
        "local": {"name": "지역", "max_display": 5, "has_date": False, "date_key": None},
        "cafearticle": {"name": "카페글", "max_display": 100, "has_date": True, "date_key": None},
        "encyc": {"name": "백과사전", "max_display": 100, "has_date": False, "date_key": None},
    }

    @classmethod
    def get_search_endpoint(cls, channel: str, auth_type: str = "ncloud_apigw") -> str:
        """인증 방식에 따른 검색 채널별 엔드포인트 URL 반환"""
        if auth_type == "ncloud_apigw":
            return f"{cls.NCLOUD_APIHUB_BASE_URL}/search/v1/{channel}"
        else:
            if channel == "image":
                return f"{cls.LEGACY_OPENAPI_BASE_URL}/search/image"
            return f"{cls.LEGACY_OPENAPI_BASE_URL}/search/{channel}.json"

    @classmethod
    def get_trend_endpoint(cls, auth_type: str = "ncloud_apigw") -> str:
        """인증 방식에 따른 검색어 트렌드 엔드포인트 URL 반환"""
        if auth_type == "ncloud_apigw":
            return f"{cls.NCLOUD_APIHUB_BASE_URL}/search-trend/v1/search"
        else:
            return f"{cls.LEGACY_OPENAPI_BASE_URL}/datalab/search"

def get_api_credentials(
    manual_client_id: Optional[str] = None,
    manual_client_secret: Optional[str] = None,
    auth_type: str = "ncloud_apigw"
) -> Dict[str, str]:
    """
    네이버 API 호출용 헤더를 생성합니다.
    UI에서 직접 입력한 값이 있으면 우선 사용하고, 없을 경우 .env 환경변수를 참조합니다.
    """
    load_dotenv(override=True)
    client_id = manual_client_id.strip() if manual_client_id else (
        os.getenv("NAVER_CLIENT_ID", "").strip() or os.getenv("NCLOUD_API_KEY_ID", "").strip()
    )
    client_secret = manual_client_secret.strip() if manual_client_secret else (
        os.getenv("NAVER_CLIENT_SECRET", "").strip() or os.getenv("NCLOUD_API_KEY", "").strip()
    )
    
    if not client_id or not client_secret:
        return {}
    
    # 10자리 키인 경우 네이버 클라우드 API 허브로 자동 감지
    effective_auth_type = auth_type
    if len(client_id) == 10 and auth_type == "naver_developers":
        effective_auth_type = "ncloud_apigw"

    if effective_auth_type == "ncloud_apigw":
        return {
            "X-NCP-APIGW-API-KEY-ID": client_id,
            "X-NCP-APIGW-API-KEY": client_secret,
            "_auth_type": "ncloud_apigw"
        }
    else:
        return {
            "X-Naver-Client-Id": client_id,
            "X-Naver-Client-Secret": client_secret,
            "_auth_type": "naver_developers"
        }
