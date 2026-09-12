# 📈 네이버 마켓 인사이트 EDA 대시보드 (Naver Market Insights EDA Dashboard)

네이버 공식 오픈 API(8대 검색 API) 및 데이터랩(DataLab) 검색어 트렌드 API를 연동하여 마켓 인사이트 조사를 위한 탐색적 데이터 분석(EDA)을 수행하는 Streamlit 웹 애플리케이션입니다.

---

## 🚀 주요 기능
- **멀티 키워드 동시 비교**: 쉼표(`,`)로 구분된 다중 검색어(예: `아이폰, 갤럭시, 픽셀`)를 한 번에 비교 분석
- **네이버 8대 채널 전수 수집**: 뉴스, 블로그, 웹문서, 이미지, 지식iN, 지역(플레이스), 카페글, 백과사전
- **데이터랩 검색어 트렌드**: 기간(일/주/월)별 검색량 지수(0~100) 인터랙티브 시계열 분석 (Plotly)
- **시장 점유율(Share of Voice) 분석**: 채널별 전체 문서 수(Total Count) 집계 및 도넛/막대 차트 시각화
- **텍스트 마이닝 & 워드클라우드**: 수집된 제목과 요약문에서 한글/영문 핵심 연관어 빈도 순위 및 시각화
- **채널별 원본 데이터 브라우저 & 이미지 갤러리**: 수집 데이터 탐색 및 채널별 CSV 다운로드 지원
- **유연한 인증 관리**: `.env` 환경변수 자동 로드 및 스트림릿 사이드바 직접 입력 UI 제공 (네이버 개발자 센터 및 네이버 클라우드 API Gateway 지원)

---

## 📂 프로젝트 구조
```
naver-search-dashboard/
├── .env.example              # 환경변수 예시 파일
├── .env                      # 네이버 API 키 보관 파일 (.gitignore 적용)
├── .gitignore                # Git 제외 파일 정의
├── pyproject.toml            # uv 기반 의존성 정의
├── README.md                 # 프로젝트 문서
├── app.py                    # Streamlit 대시보드 진입점
└── src/
    ├── config/               # 환경변수 및 API 설정
    │   ├── __init__.py
    │   └── settings.py
    ├── api/                  # 네이버 검색 및 데이터랩 API 클라이언트
    │   ├── __init__.py
    │   ├── naver_client.py
    │   └── datalab_client.py
    ├── services/             # 데이터 수집 및 EDA 서비스
    │   ├── __init__.py
    │   ├── collector.py
    │   └── eda_service.py
    ├── utils/                # 텍스트 전처리, 워드클라우드, 날짜 필터링 유틸
    │   ├── __init__.py
    │   ├── text_utils.py
    │   └── date_utils.py
    └── components/           # Streamlit UI 컴포넌트 및 Plotly 차트
        ├── __init__.py
        ├── charts.py
        └── views.py
```

---

## 🛠️ 시작하기 (uv 기반 실행)

### 1. 가상환경 및 패키지 설치
이 프로젝트는 초고속 패키지 관리자 `uv`를 사용합니다.
```bash
# 의존성 패키지 동기화 및 가상환경 설정
uv sync
```

### 2. 네이버 API 키 설정
`.env` 파일에 발급받은 네이버 오픈 API 키를 입력합니다:
```bash
# .env 파일 생성 또는 수정
NAVER_CLIENT_ID=your_client_id_here
NAVER_CLIENT_SECRET=your_client_secret_here
```
> ※ 키가 없어도 스트림릿 실행 후 사이드바에서 언제든지 직접 입력하여 테스트할 수 있습니다.

### 3. Streamlit 대시보드 실행
```bash
uv run streamlit run app.py
```
브라우저에서 `http://localhost:8501`로 접속합니다.
