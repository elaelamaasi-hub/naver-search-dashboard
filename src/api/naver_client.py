import requests
from typing import Dict, Any, Optional
from ..config.settings import APIConfig

class NaverSearchClient:
    """네이버 8대 검색 채널(뉴스, 블로그, 웹, 이미지, 지식iN, 지역, 카페, 백과사전) API 클라이언트"""

    def __init__(self, headers: Dict[str, str]):
        self.auth_type = headers.get("_auth_type", "ncloud_apigw")
        # 실제 HTTP 전송용 헤더에서 내부 제어 키 제거
        self.headers = {k: v for k, v in headers.items() if not k.startswith("_")}

    def search_channel(
        self,
        channel: str,
        query: str,
        display: int = 100,
        start: int = 1,
        sort: str = "sim"
    ) -> Dict[str, Any]:
        """
        단일 채널에 대한 검색 요청을 수행합니다.
        
        Args:
            channel: 'news', 'blog', 'webkr', 'image', 'kin', 'local', 'cafearticle', 'encyc'
            query: 검색어
            display: 출력 건수 (최대 100, 지역은 최대 5)
            start: 시작 위치 (1~1000)
            sort: 정렬 방식 ('sim': 유사도/정확도순, 'date': 날짜순)
        """
        endpoint = APIConfig.get_search_endpoint(channel, auth_type=self.auth_type)
        if not endpoint:
            return {
                "success": False,
                "error": f"지원하지 않는 채널입니다: {channel}",
                "channel": channel,
                "total": 0,
                "items": []
            }

        # 지역 API의 경우 display 최대값이 5임
        if channel == "local":
            display = min(display, 5)
        else:
            display = min(display, 100)

        params = {
            "query": query,
            "display": display,
            "start": start
        }
        # sort 파라미터 지원 채널: news, blog, cafearticle, image, kin, local(comment/random)
        if channel in ["news", "blog", "cafearticle", "image", "kin"]:
            params["sort"] = sort
        elif channel == "local" and sort == "date":
            params["sort"] = "comment"

        try:
            response = requests.get(
                endpoint,
                headers=self.headers,
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "channel": channel,
                    "channel_name": APIConfig.CHANNELS.get(channel, {}).get("name", channel),
                    "total": data.get("total", 0),
                    "start": data.get("start", 1),
                    "display": data.get("display", len(data.get("items", []))),
                    "items": data.get("items", [])
                }
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                try:
                    err_json = response.json()
                    error_msg = f"{err_json.get('errorMessage', response.text)} (코드: {err_json.get('errorCode', response.status_code)})"
                except Exception:
                    pass
                return {
                    "success": False,
                    "channel": channel,
                    "channel_name": APIConfig.CHANNELS.get(channel, {}).get("name", channel),
                    "error": error_msg,
                    "total": 0,
                    "items": []
                }
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "channel": channel,
                "channel_name": APIConfig.CHANNELS.get(channel, {}).get("name", channel),
                "error": "요청 시간 초과 (타임아웃)",
                "total": 0,
                "items": []
            }
        except Exception as e:
            return {
                "success": False,
                "channel": channel,
                "channel_name": APIConfig.CHANNELS.get(channel, {}).get("name", channel),
                "error": str(e),
                "total": 0,
                "items": []
            }
