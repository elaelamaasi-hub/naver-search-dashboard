import re
import html
import os
from urllib.parse import urlparse
from collections import Counter
from typing import List, Tuple, Optional, Dict, Any
from wordcloud import WordCloud

# 한글 불용어(Stopwords) 기본 목록
DEFAULT_STOPWORDS = {
    "이", "그", "저", "것", "수", "등", "및", "를", "을", "에", "의", "가", "은", "는",
    "와", "과", "로", "으로", "에서", "까지", "부터", "대한", "위한", "통해", "관련",
    "더", "잘", "못", "안", "또", "다시", "매우", "너무", "정말", "모두", "함께",
    "있다", "없다", "하다", "되다", "이다", "같다", "대해", "따라", "있는", "하는",
    "되는", "위해", "하며", "되고", "하고", "경우", "때문", "관련된", "통한", "제공",
    "네이버", "검색", "결과", "조회", "정보", "보기", "바로가기", "더보기"
}

# 기초 감성(어조) 분석용 긍정/부정 어휘 사전
POSITIVE_WORDS = {
    "성장", "혁신", "상승", "최고", "기대", "인기", "추천", "혜택", "만족", "성공",
    "돌파", "우수", "호조", "개선", "확대", "긍정", "대박", "신기록", "호평", "발전",
    "선도", "강세", "활성화", "주목", "매력", "호재", "안정", "회복", "유망", "급증"
}

NEGATIVE_WORDS = {
    "하락", "우려", "감소", "악화", "논란", "위험", "위기", "실패", "불만", "비판",
    "적자", "충격", "제재", "피해", "급락", "부진", "침체", "부정", "결함", "폭락",
    "소송", "약세", "경고", "불안", "의혹", "갈등", "타격", "급감", "리스크", "폐지"
}

def clean_html(raw_text: Optional[str]) -> str:
    """HTML 태그 및 HTML 엔티티를 제거하고 일반 텍스트로 변환합니다."""
    if not raw_text:
        return ""
    # HTML 엔티티 언이스케이프 (예: &quot; -> ", &lt; -> <)
    text = html.unescape(raw_text)
    # 태그 제거 (<b>, </b> 등)
    text = re.sub(r"<[^>]+>", "", text)
    # 불필요한 연속 공백 정규화
    text = re.sub(r"\s+", " ", text).strip()
    return text

def extract_domain(url: Optional[str]) -> str:
    """URL에서 도메인(호스트명)을 추출합니다."""
    if not url:
        return "기타/알수없음"
    try:
        parsed = urlparse(url)
        netloc = parsed.netloc.lower()
        # www. 제거
        if netloc.startswith("www."):
            netloc = netloc[4:]
        return netloc if netloc else "기타/알수없음"
    except Exception:
        return "기타/알수없음"

def analyze_sentiment(text: str) -> Dict[str, Any]:
    """
    텍스트 내 긍정/부정 어휘 매칭을 통한 기초 감성 지수(-1.0 ~ +1.0) 및 라벨 산출
    """
    cleaned = clean_html(text).lower()
    tokens = re.findall(r"[가-힣]{2,}", cleaned)
    
    pos_count = sum(1 for t in tokens if t in POSITIVE_WORDS)
    neg_count = sum(1 for t in tokens if t in NEGATIVE_WORDS)
    total_sentiment_words = pos_count + neg_count

    if total_sentiment_words == 0:
        score = 0.0
        label = "중립"
    else:
        score = (pos_count - neg_count) / total_sentiment_words
        if score > 0.15:
            label = "긍정"
        elif score < -0.15:
            label = "부정"
        else:
            label = "중립"

    return {
        "pos_count": pos_count,
        "neg_count": neg_count,
        "sentiment_score": round(score, 3),
        "sentiment_label": label
    }

def extract_text_features(title: str, desc: str) -> Dict[str, Any]:
    """제목 및 요약문에서 텍스트 통계 지표 산출"""
    t_clean = clean_html(title)
    d_clean = clean_html(desc)
    combined = f"{t_clean} {d_clean}".strip()
    
    words = re.findall(r"[가-힣a-zA-Z0-9]+", combined)
    unique_words = set(w.lower() for w in words)
    lexical_diversity = round(len(unique_words) / len(words), 3) if words else 0.0

    sentiment = analyze_sentiment(combined)

    return {
        "title_clean": t_clean,
        "desc_clean": d_clean,
        "title_len": len(t_clean),
        "desc_len": len(d_clean),
        "total_len": len(t_clean) + len(d_clean),
        "word_count": len(words),
        "unique_word_count": len(unique_words),
        "lexical_diversity": lexical_diversity,
        "sentiment_score": sentiment["sentiment_score"],
        "sentiment_label": sentiment["sentiment_label"]
    }

def extract_keywords(
    texts: List[str],
    top_n: int = 30,
    min_word_len: int = 2,
    custom_stopwords: Optional[set] = None
) -> List[Tuple[str, int]]:
    """
    텍스트 목록에서 의미 있는 한글 및 영문 키워드 빈도를 추출합니다.
    """
    stopwords = DEFAULT_STOPWORDS.copy()
    if custom_stopwords:
        stopwords.update(custom_stopwords)
    
    words = []
    for text in texts:
        cleaned = clean_html(text)
        tokens = re.findall(r"[가-힣a-zA-Z0-9]{2,}", cleaned)
        for token in tokens:
            token_lower = token.lower()
            if token_lower.isdigit():
                continue
            if token_lower not in stopwords and len(token_lower) >= min_word_len:
                words.append(token_lower)
                
    counter = Counter(words)
    return counter.most_common(top_n)

def get_korean_font_path() -> Optional[str]:
    """Windows/macOS/Linux 시스템의 한글 폰트 경로를 탐색합니다."""
    candidate_paths = [
        r"C:\Windows\Fonts\malgun.ttf",       # 맑은 고딕
        r"C:\Windows\Fonts\malgunbd.ttf",     # 맑은 고딕 볼드
        r"C:\Windows\Fonts\gulim.ttc",        # 굴림
        "/System/Library/Fonts/AppleSDGothicNeo.ttc", # macOS
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf", # Linux
    ]
    for p in candidate_paths:
        if os.path.exists(p):
            return p
    return None

def generate_wordcloud_image(
    word_freq_dict: dict,
    width: int = 800,
    height: int = 400,
    background_color: str = "white"
) -> Optional[WordCloud]:
    """단어 빈도 딕셔너리를 기반으로 WordCloud 객체를 생성합니다."""
    if not word_freq_dict:
        return None
        
    font_path = get_korean_font_path()
    try:
        wc = WordCloud(
            font_path=font_path,
            width=width,
            height=height,
            background_color=background_color,
            colormap="viridis",
            max_words=100,
            prefer_horizontal=0.9
        ).generate_from_frequencies(word_freq_dict)
        return wc
    except Exception as e:
        print(f"WordCloud 생성 실패: {e}")
        return None
