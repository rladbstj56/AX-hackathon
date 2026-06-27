import pandas as pd
import re
from pathlib import Path

BASE_DIR = Path(__file__).parent
INPUT_CSV = BASE_DIR / "Day3_과제_feedback.csv"
OUTPUT_CSV = BASE_DIR / "Day3_과제_feedback_classified.csv"

# ── 1. 날짜 정규화 ────────────────────────────────────────────────────────────

def parse_date(raw: str) -> str:
    """4가지 날짜 형식을 YYYY-MM-DD로 통일."""
    s = str(raw).strip()

    # 26.5.6 → 연도 두 자리 점 구분
    m = re.fullmatch(r"(\d{2})\.(\d{1,2})\.(\d{1,2})", s)
    if m:
        y, mo, d = m.groups()
        return f"20{y}-{int(mo):02d}-{int(d):02d}"

    # 5월 4일 → 한글 (연도 없으면 2026 기본)
    m = re.fullmatch(r"(\d{1,2})월\s*(\d{1,2})일", s)
    if m:
        mo, d = m.groups()
        return f"2026-{int(mo):02d}-{int(d):02d}"

    # 2026/05/03 or 2026-05-02
    try:
        return pd.to_datetime(s).strftime("%Y-%m-%d")
    except Exception:
        return s  # 파싱 실패 시 원본 유지


# ── 2. 유형 분류 (키워드 규칙) ──────────────────────────────────────────────

COMPLAINT_KW = ["오류", "안 울려", "끊겨", "불만", "잘못", "안 쌓", "환불", "오래", "좁아", "달아", "올랐", "식었", "불편"]
REQUEST_KW   = ["있으면 좋겠", "해주셨으면", "나왔으면", "있으면", "표시가 있으면"]
PRAISE_KW    = ["좋아요", "친절", "맛있어요", "단골", "감사해요", "추천", "예뻐서", "퀄리티"]
INQUIRY_KW   = ["있나요", "가능한가요", "되나요", "어떻게 되나요", "여나요", "될까요"]

def classify(text: str) -> str:
    for kw in COMPLAINT_KW:
        if kw in text:
            return "불만"
    for kw in REQUEST_KW:
        if kw in text:
            return "요청"
    for kw in INQUIRY_KW:
        if kw in text:
            return "문의"
    for kw in PRAISE_KW:
        if kw in text:
            return "칭찬"
    return "기타"


# ── 3. 긴급도 점수 (유형별 기본점수 + 추가점수) ──────────────────────────────

MONEY_KW   = ["환불", "결제", "포인트", "금액", "돈"]
REPEAT_KW  = ["또", "계속", "자꾸", "두 번", "반복"]
NO_USE_KW  = ["오류", "안 울려", "끊겨", "식었"]
REQUEST_URGENT_KW = ["빨리", "급해요", "당장", "꼭", "알레르기", "안전", "위험", "항상", "매번"]
INQUIRY_URGENT_KW = ["예약", "단체", "명", "알레르기", "오늘", "지금", "바로"]

TYPE_BASE = {"불만": 3, "요청": 2, "문의": 1, "칭찬": 0}

def urgency_score(row: pd.Series) -> int:
    유형 = row["유형"]
    score = TYPE_BASE.get(유형, 0)
    text = str(row["내용"])
    rating = row["별점"]

    # 불만 전용 추가점수
    if 유형 == "불만":
        if any(kw in text for kw in MONEY_KW):
            score += 3
        if any(kw in text for kw in REPEAT_KW):
            score += 1
        if any(kw in text for kw in NO_USE_KW):
            score += 1

    # 요청 전용 추가점수
    if 유형 == "요청":
        if any(kw in text for kw in REQUEST_URGENT_KW):
            score += 1

    # 문의 전용 추가점수
    if 유형 == "문의":
        if any(kw in text for kw in INQUIRY_URGENT_KW):
            score += 1

    # 별점 1~2점 추가점수 (불만·요청·문의 공통)
    if 유형 in ("불만", "요청", "문의"):
        if pd.notna(rating) and rating == 1:
            score += 2
        elif pd.notna(rating) and rating == 2:
            score += 1

    return score


# ── 4. 감정 추정 ──────────────────────────────────────────────────────────────

POS_KW = ["좋아요", "맛있어요", "친절", "감사", "추천", "예뻐", "퀄리티", "단골", "완벽"]
NEG_KW = ["오류", "불만", "달아", "오래", "좁아", "끊겨", "식었", "잘못", "올랐", "안 쌓", "환불", "불편", "안 울려"]

def estimate_sentiment(row: pd.Series) -> str:
    rating = row["별점"]
    if pd.notna(rating):
        if rating <= 2:
            return "부정"
        elif rating == 3:
            return "중립"
        else:
            return "긍정"
    # 별점 없으면 내용 키워드로 추정
    text = str(row["내용"])
    if any(kw in text for kw in NEG_KW):
        return "부정"
    if any(kw in text for kw in POS_KW):
        return "긍정"
    return "중립"


# ── 메인 ─────────────────────────────────────────────────────────────────────

def main():
    df = pd.read_csv(INPUT_CSV)

    print(f"[로드] {len(df)}행, {df.shape[1]}열")
    print(f"[결측] 별점 결측: {df['별점'].isna().sum()}건")

    # 1. 날짜 정규화
    df["받은날짜"] = df["받은날짜"].apply(parse_date)

    # 2. 유형 분류
    df["유형"] = df["내용"].apply(classify)

    # 3. 감정 추정 — 원본 별점 기준으로 먼저 실행 (결측이면 키워드로 추정)
    df["감정"] = df.apply(estimate_sentiment, axis=1)

    # 4. 별점 결측 — 유형별 평균으로 채우기 (없으면 NaN 유지)
    mean_by_type = df.groupby("유형")["별점"].mean()
    def fill_rating(row):
        if pd.isna(row["별점"]):
            return round(mean_by_type.get(row["유형"], float("nan")), 1)
        return row["별점"]
    df["별점"] = df.apply(fill_rating, axis=1)

    # 5. 긴급도 점수
    df["긴급도"] = df.apply(urgency_score, axis=1)

    # 6. 저장
    df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    print(f"\n[완료] → {OUTPUT_CSV.name}")

    # 정합성 체크
    print(f"\n[유형 분포]\n{df['유형'].value_counts().to_string()}")
    print(f"\n[급한 불만 Top3]")
    top3 = df[df["유형"] == "불만"].sort_values("긴급도", ascending=False).head(3)
    for _, r in top3.iterrows():
        print(f"  ID {r['id']} (긴급도 {r['긴급도']}점) | 별점 {r['별점']} | {r['내용'][:30]}...")


if __name__ == "__main__":
    main()
