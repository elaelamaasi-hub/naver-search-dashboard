import requests
import json
from typing import Dict, Any, List, Optional
from ..config.settings import APIConfig

class NaverDataLabClient:
    """네이버 데이터랩(DataLab) 검색어 트렌드 API 클라이언트"""

    def __init__(self, headers: Dict[str, str]):
        self.auth_type = headers.get("_auth_type", "ncloud_apigw")
        # 실제 HTTP 전송용 헤더에서 내부 제어 키 제거
        self.headers = {k: v for k, v in headers.items() if not k.startswith("_")}
        self.headers["Content-Type"] = "application/json"

    def get_search_trend(
        self,
        keyword_groups: List[Dict[str, Any]],
        start_date: str,
        end_date: str,
        time_unit: str = "date",
        device: Optional[str] = None,
        gender: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        네이버 데이터랩 검색어 트렌드(상대적 검색량 지수 0~100)를 요청합니다.
        
        Args:
            keyword_groups: 최대 5개 그룹. [{"groupName": "그룹명", "keywords": ["키워드1", "키워드2"]}]
            start_date: YYYY-MM-DD
            end_date: YYYY-MM-DD
            time_unit: 'date' (일간), 'week' (주간), 'month' (월간)
            device: 'pc', 'mo' 또는 None (전체)
            gender: 'm', 'f' 또는 None (전체)
        """
        endpoint = APIConfig.get_trend_endpoint(auth_type=self.auth_type)

        # 네이버 API 제한: 최대 5개 그룹
        limited_groups = keyword_groups[:5]
        
        payload = {
            "startDate": start_date,
            "endDate": end_date,
            "timeUnit": time_unit,
            "keywordGroups": limited_groups
        }
        if device in ["pc", "mo"]:
            payload["device"] = device
        if gender in ["m", "f"]:
            payload["gender"] = gender

        try:
            response = requests.post(
                endpoint,
                headers=self.headers,
                data=json.dumps(payload),
                timeout=12
            )

            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "startDate": data.get("startDate"),
                    "endDate": data.get("endDate"),
                    "timeUnit": data.get("timeUnit"),
                    "results": data.get("results", [])
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
                    "error": error_msg,
                    "results": []
                }
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": "요청 시간 초과 (타임아웃)",
                "results": []
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "results": []
            }
