import streamlit as st
import pandas as pd
from supabase import create_client

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

@st.cache_resource
def get_client():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def load_df() -> pd.DataFrame:
    client = get_client()
    res = client.table("feedback").select("*").order("id").execute()
    return pd.DataFrame(res.data)

def mark_resolved(feedback_id: int, value: bool):
    client = get_client()
    client.table("feedback").update({"처리됨": value}).eq("id", feedback_id).execute()

st.set_page_config(page_title="고객 피드백 대시보드", layout="wide")
st.title("☕ 카페 고객 피드백 — 지금 가장 급한 불만은?")

df = load_df()

# ── 상단: 유형별 개수 카드 ────────────────────────────────────────────────────
counts = df["유형"].value_counts()

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("전체 피드백", f"{len(df)}건")
col2.metric("🔴 불만", f"{counts.get('불만', 0)}건")
col3.metric("🟡 요청", f"{counts.get('요청', 0)}건")
col4.metric("🔵 문의", f"{counts.get('문의', 0)}건")
col5.metric("🟢 칭찬", f"{counts.get('칭찬', 0)}건")

st.divider()

# ── 하단: 가장 급한 불만 TOP 3 ───────────────────────────────────────────────
st.subheader("🚨 가장 급한 불만 TOP 3")
st.markdown(
    """
**선정 기준**
- 유형 기본점수: 불만 +3 · 요청 +2 · 문의 +1 · 칭찬 0
- 공통 추가 (불만·요청·문의): 별점 1점 +2 · 별점 2점 +1
- 불만 전용: 금전 피해(환불·결제·포인트) +3 · 반복 표현(자꾸·두 번·계속) +1 · 서비스 불가(오류·끊겨·안 울려) +1
- 요청 전용: 긴급·안전 키워드(빨리·꼭·알레르기 등) +1
- 문의 전용: 즉시 답변 필요 키워드(예약·단체·알레르기 등) +1
"""
)
_, hint_col = st.columns([5, 2])
hint_col.caption("처리 완료되면 버튼을 눌러주세요.")

top3 = (
    df[(df["유형"] == "불만") & (df["처리됨"] == False)]
    .sort_values("긴급도", ascending=False)
    .head(3)
    .reset_index(drop=True)
)

medals = ["🥇", "🥈", "🥉"]
유형_색 = {"불만": "🔴", "요청": "🟡", "문의": "🔵", "칭찬": "🟢"}
감정_색 = {"부정": "😠", "중립": "😐", "긍정": "😊"}

if top3.empty:
    st.success("✅ 처리되지 않은 불만이 없습니다!")
else:
    for i, row in top3.iterrows():
        with st.container(border=True):
            c1, c2, c3 = st.columns([1, 4, 2])
            with c1:
                st.markdown(f"### {medals[i]}")
                st.caption(f"ID #{int(row['id'])} · {row['경로']}")
                st.caption(f"별점 {'★' * int(row['별점']) if pd.notna(row['별점']) else 'N/A'}")
                st.caption(f"긴급도 **{int(row['긴급도'])}점**")
                st.caption(f"{유형_색.get(row['유형'], '')} {row['유형']}  {감정_색.get(row['감정'], '')} {row['감정']}")
            with c2:
                st.markdown(f"**{row['내용']}**")
                score_detail = []
                text = str(row["내용"])
                if any(kw in text for kw in ["환불", "결제", "포인트", "금액", "돈"]):
                    score_detail.append("💸 금전 피해")
                if any(kw in text for kw in ["자꾸", "두 번", "계속", "또", "반복"]):
                    score_detail.append("🔁 반복 발생")
                if any(kw in text for kw in ["오류", "안 울려", "끊겨", "식었"]):
                    score_detail.append("🚫 서비스 불가")
                if pd.notna(row["별점"]) and row["별점"] <= 2:
                    score_detail.append(f"⭐ 별점 {int(row['별점'])}점")
                st.info("긴급 사유: " + " · ".join(score_detail) if score_detail else "유형 기본점수")
            with c3:
                if st.button("✅ 처리 완료", key=f"resolve_{int(row['id'])}"):
                    mark_resolved(int(row["id"]), True)
                    st.cache_resource.clear()
                    st.rerun()

# ── 처리 완료 목록 ────────────────────────────────────────────────────────────
resolved = df[(df["유형"] == "불만") & (df["처리됨"] == True)]
if not resolved.empty:
    with st.expander(f"✅ 처리 완료 항목 ({len(resolved)}건)"):
        for _, row in resolved.iterrows():
            c1, c2 = st.columns([5, 1])
            with c1:
                st.markdown(f"~~ID #{int(row['id'])} · {row['내용']}~~")
            with c2:
                if st.button("↩ 되돌리기", key=f"undo_{int(row['id'])}"):
                    mark_resolved(int(row["id"]), False)
                    st.cache_resource.clear()
                    st.rerun()
