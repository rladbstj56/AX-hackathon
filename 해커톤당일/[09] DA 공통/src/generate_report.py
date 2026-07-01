"""insight_report.md 자동 생성 — 수치·표는 계산 엔진에서, 해석은 규칙 기반 템플릿으로.

calculate.py(집계)·detect_issues.py(이슈)를 불러 새 CSV에도 동일 품질의 리포트를 재현한다.
권장 조치는 임의 서술이 아니라 industry-news.md 4장 '성과 이슈 패턴(유형 A~D)'에 매핑한다.
"""
import sys

import pandas as pd

from detect_issues import BAND_SHORT
from reallocate import run_pipeline

DATA = 'data/marketing_performance.csv'
OUT = 'output/insight_report.md'

# 이슈 유형 → 권장 조치 (industry-news.md 4장 유형 A~D 대응)
REC = {
    '광고비급등(과집행)': "예산 한도 설정, 타겟 세분화, 소재 교체 (유형 A: 광고비 급증 후 ROAS 하락)",
    '매출이상치': "원본 데이터 재확인, 중복·테스트 주문 제거 후 재집계 (유형 D: 비현실적 급등)",
    'revenue결측': "즉시 담당자 확인, 수동 보정 또는 '데이터 없음' 명시 (유형 C: 데이터 결측)",
    'impressions결측': "트래킹 코드·플랫폼 API 점검 (유형 C: 데이터 결측)",
    'clicks결측': "트래킹 코드·플랫폼 API 점검 (유형 C: 데이터 결측)",
    '광고비급락(집행축소)': "의도적 감축인지 집행 중단 사고인지 담당자 확인",
    '성과급락': "랜딩페이지 A/B 테스트, UX·경쟁·소재 소진 점검 (유형 B)",
    '성과호재': "성공 요인 분석 후 예산 확대 검토",
}


def won(x):
    return f"{x:,.0f}원"


def _usage_guide(meta):
    """리포트 최상단 '사용법' 박스 (고객 중심 갭 보완) — 처음 보는 독자가 무엇을·어떻게 볼지 안내.

    독자별(경영진/마케터) 읽는 지점과 순서, 이슈 태그를 실제 액션으로 잇는 경로를 명시한다.
    n_weeks만 데이터에서 채우고 나머지는 고정 안내라 새 CSV에도 그대로 재현된다.
    """
    return ("> 이 리포트가 무엇이고 누가 어떻게 쓰는지 먼저 안내합니다. 처음 보는 분은 여기부터 읽으세요.\n\n"
            f"- **무엇**: 지난 {meta['n_weeks']}주 마케팅 성과를 데이터에서 직접 계산·해석한 주간 점검 리포트입니다.\n"
            "- **누가·언제**: [경영진] 성과 브리핑 때 '한눈에 보기'만 봐도 전체·위험을 판단 / [마케터] 주간 예산·소재 결정 때 이슈·채널 평가를 근거로 사용.\n"
            "- **읽는 순서**: ① 한눈에 보기(전체 성과·위험) → ② 이번 주 실행 플레이북(지금 할 일 전체) → ③ 이슈·채널 평가(플레이북의 근거) → ④ 전주 대비 변화율(급변 감시).\n"
            "- **액션으로 잇기**: 이슈의 `[예산]` 태그는 예산 재배분 기획안(budget_reallocation)으로 실행, `[데이터·트래킹]`은 트래킹팀에 정정 요청, `[운영]`은 담당 채널자 확인.\n")


def _overview(meta):
    return (f"- 분석 대상: {meta['path']} (원본 {meta['n_raw']}행, 채널 {meta['n_channels']}개)\n"
            f"- 분석 기간: {meta['date_min']} – {meta['date_max']} ({meta['n_weeks']}주: {meta['weeks']})\n"
            "- 데이터 정제:\n"
            f"  - 완전 중복 {meta['n_dup']}행 제거 ({meta['n_raw']}→{meta['n_raw']-meta['n_dup']}행)\n"
            f"  - 결측 {meta['n_missing']}건 NaN 유지 — 0으로 채우지 않고 집계에서 자동 제외\n"
            f"  - 매출 이상치 {meta['n_outlier']}건 revenue만 제외(AOV modified z-score>3.5 자동 탐지) — 정상 지출·전환은 보존\n"
            "  - 오가닉(광고비 0) ROI 측정 불가로 순위 제외\n")


def _summary(s):
    t = s['total']
    rows = ["| 지표 | 값 |", "|------|-----|",
            f"| 총 지출 (유료 광고비) | {won(t['total_spend'])} |",
            f"| 총 매출 (전 채널, 오가닉 포함) | {won(t['total_revenue'])} |",
            f"| ├ 오가닉(비유료) 매출 | {won(t['organic_revenue'])} ({t['organic_revenue']/t['total_revenue']*100:.2f}%) |",
            f"| └ 유료채널 매출 | {won(t['paid_revenue'])} |",
            f"| 전체 마케팅 효율 MER (오가닉 포함) | {t['mer']:.2f}% |",
            f"| 유료 광고 순효율 (오가닉 제외) | {t['paid_roi']:.2f}% |",
            f"| 총 전환수 | {t['total_conversions']:,.0f}건 |\n",
            "> **오가닉(organic)** = 광고비를 직접 쓰지 않고 들어온 매출(검색 결과·직접 방문·SEO·콘텐츠 등 자연 유입). "
            "이번 기간 광고 원장에 잡히는 지출이 0이라 ROI 계산 대상에선 빠지지만 매출 기여는 크므로 별도 표기한다"
            "(규모가 유의미하면 아래 '오가닉 성장 잠재력' 섹션에서 상세 분석).\n",
            "> MER은 경영진용(마케팅 조직 전체 성과), 유료 순효율은 마케팅팀용(광고 운영 효율).\n",
            "### 채널별 합계·파생지표\n",
            "| 채널 | 광고비(원) | 매출(원) | 전환 | ROI(%) | ROAS | CPA(원) | CTR(%) | CVR(%) |",
            "|------|-----------|---------|------|--------|------|---------|--------|--------|"]
    g = s['by_channel']
    for ch in g.sort_values('revenue', ascending=False).index:   # 채널 목록을 데이터에서 동적으로
        r = g.loc[ch]
        roi = "측정불가" if pd.isna(r['ROI']) else f"{r['ROI']:.2f}"
        roas = "-" if pd.isna(r['ROAS']) else f"{r['ROAS']:.2f}"
        cpa = "-" if pd.isna(r['CPA']) else f"{r['CPA']:,.0f}"
        rows.append(f"| {ch} | {r['spend']:,.0f} | {r['revenue']:,.0f} | {r['conversions']:,.0f} | "
                    f"{roi} | {roas} | {cpa} | {r['CTR']:.2f} | {r['CVR']:.2f} |")
    rows.append("\n> **CPA(전환당 비용)** = 광고비 / 전환. 낮을수록 효율적(입찰·예산 조정의 직접 지표). "
                "오가닉은 광고비 0이라 측정 제외(-).")
    return "\n".join(rows) + "\n"


def _roi_rank(roi_df):
    rows = ["> ROI = 매출 / 광고비 × 100. 오가닉은 광고비 0이라 측정 불가로 제외.\n",
            "> **활용**: 효율 높은 채널을 키울 후보로 보되, 절대 ROI만으로 정하지 말고 아래 6번 시장 벤치마크 등급과 함께 판단하세요 — 절대 1위여도 자기 시장 대비 미달일 수 있습니다.\n",
            "| 순위 | 채널 | ROI(%) |", "|------|------|--------|"]
    for i, (ch, r) in enumerate(roi_df.iterrows(), 1):
        rows.append(f"| {i} | {ch} | {r['ROI']:.2f} |")
    rows.append("| - | 오가닉 | 측정 불가 (광고비 0) |")
    top = roi_df.index[0]
    rows.append(f"\n**해석**: 가장 효율적인 유료 채널은 {top}(ROI {roi_df.iloc[0]['ROI']:.2f}%). "
                "단 절대 효율(ROI)이 높다고 채널 벤치마크 대비 잘하는 것은 아니므로 6번 채널 평가와 함께 볼 것.\n")
    return "\n".join(rows)


def _status(itype, channel, recency, threshold):
    """이슈가 최근 주차에도 지속되는지 한 줄로 반환 (갭3: 진행 중 vs 해소 구분).

    급등/급락 이슈는 해당 지표의 최근 주차 LOO 편차를 임계값과 비교해 지속/해소를 판정한다.
    이상치·결측은 특정 일자 데이터 사안이라 '재발' 개념이 아니므로 그 성격만 명시한다.
    독자가 '지금 불이 났나(지속) 이미 끝난 일인가(해소)'를 알아 긴급도를 가르게 한다.
    """
    r = recency.get(channel)
    if r is None:
        return ""
    wk, thr = r['week'], threshold * 100
    if '과집행' in itype:
        v, hit = r['spend'], (not pd.isna(r['spend']) and r['spend'] >= thr)
    elif '집행축소' in itype:
        v, hit = r['spend'], (not pd.isna(r['spend']) and r['spend'] <= -thr)
    elif '성과급락' in itype:
        v = r['revenue']
        hit = any(not pd.isna(r[m]) and r[m] <= -thr for m in ('revenue', 'conversions'))
    elif '호재' in itype:
        v = r['revenue']
        hit = any(not pd.isna(r[m]) and r[m] >= thr for m in ('revenue', 'conversions'))
    else:
        return "- 최근성: 특정 일자 데이터 사안(재발 개념 아님) — 정정 후 재탐지로 확인"
    if pd.isna(v):
        return ""
    tag = "지속(최근 주차도 임계값 초과 — 긴급)" if hit else "해소(최근 주차 정상 범위 — 사후 점검)"
    return f"- 최근 {wk} 상태: {tag}, 해당 지표 편차 {v:+.1f}%"


def _issues(ranked, recency, threshold):
    rows = ["> 손실 이슈는 원(₩) 매출 영향으로 통일해 정렬하되, **예산·운영으로 실행 가능한 손실**과 "
            "**데이터 정정 사안**을 분리한다 — 성격이 달라 조치도 다르기 때문. 규칙 기반 자동 탐지 결과.\n",
            "> **활용**: 각 이슈의 대괄호 태그가 곧 담당·조치처입니다 — `[예산]`은 예산 재배분 기획안으로, "
            "`[데이터·트래킹]`은 트래킹팀 정정 요청, `[운영]`은 채널 담당자 확인으로 넘기세요.\n"]
    loss = ranked.get('loss')
    if loss is None or loss.empty:
        actionable = data_fix = loss  # 둘 다 None/empty → 아래에서 '없음' 처리
    else:
        actionable = loss[loss['lever'] != '데이터·트래킹']
        data_fix = loss[loss['lever'] == '데이터·트래킹']

    rows.append("### 실행 가능한 손실 (예산·운영 — 바로 조치)\n")
    if actionable is None or actionable.empty:
        rows.append("이번 기간 예산·운영 레버로 실행할 손실 이슈는 탐지되지 않았습니다.\n")
    else:
        for i, (_, r) in enumerate(actionable.iterrows(), 1):
            rows += [f"**이슈 {i}: {r['channel']} — {r['type']} (기회손실 {won(r['impact_won'])}) `[{r['lever']}]`**",
                     f"- 현상·근거: {r['note']}",
                     f"- 발생: {r['weeks']} (빈도 {r['frequency']}주)"]
            st = _status(r['type'], r['channel'], recency, threshold)
            if st:
                rows.append(st)
            rows.append(f"- 권장 조치: {REC.get(r['type'], '원인 분석 후 대응')}\n")
        rows.append("> 예산 레버 손실의 회수분은 재배분 재원이 된다 — 상세 기획은 budget_reallocation.md 참조.\n")

    rows.append("### 데이터 정정 필요 (예산 조치 아님 — 원본·트래킹 확인)\n")
    rows.append("> 아래 '금액'은 잃은 돈이 아니라 **데이터가 왜곡·누락된 규모**다. 예산 재배분 대상이 아니며 "
                "원본 재확인·수동 보정으로 해결하는 수치 신뢰도 이슈다.\n")
    if data_fix is None or data_fix.empty:
        rows.append("데이터 정정이 필요한 손실 사안은 없습니다.\n")
    else:
        for i, (_, r) in enumerate(data_fix.iterrows(), 1):
            rows += [f"**정정 {i}: {r['channel']} — {r['type']} (왜곡·추정 금액 {won(r['impact_won'])}) `[{r['lever']}]`**",
                     f"- 현상·근거: {r['note']}",
                     f"- 발생: {r['weeks']} (빈도 {r['frequency']}주)",
                     f"- 권장 조치: {REC.get(r['type'], '원본 확인')}\n"]

    if 'operational' in ranked:
        rows.append("### 운영 관찰 (손실은 아니나 확인 필요)\n")
        for i, (_, r) in enumerate(ranked['operational'].iterrows(), 1):
            rows += [f"**관찰 {i}: {r['channel']} — {r['type']} ({r['week']})**",
                     f"- 현상·근거: {r['note']}"]
            st = _status(r['type'], r['channel'], recency, threshold)
            if st:
                rows.append(st)
            rows.append(f"- 권장 조치: {REC.get(r['type'], '담당자 확인')}\n")

    if 'quality' in ranked:
        rows.append("### 데이터 수집 품질 이슈\n")
        for i, (_, r) in enumerate(ranked['quality'].iterrows(), 1):
            rows += [f"**품질 {i}: {r['channel']} — {r['type']} ({r['week']})**",
                     f"- 현상·근거: {r['note']}",
                     f"- 권장 조치: {REC.get(r['type'], '트래킹 점검')}\n"]

    if 'positive' in ranked:
        rows.append("### 주목할 긍정 신호\n")
        for i, (_, r) in enumerate(ranked['positive'].iterrows(), 1):
            rows += [f"**긍정 {i}: {r['channel']} — {r['type']} ({r['week']})**",
                     f"- 현상·근거: {r['note']}"]
            st = _status(r['type'], r['channel'], recency, threshold)
            if st:
                rows.append(st)
            rows.append(f"- 권장 조치: {REC.get(r['type'], '성공 요인 분석 후 확대 검토')}\n")
    return "\n".join(rows)


def _wow(wow_df):
    prev, curr = wow_df.columns[0], wow_df.columns[1]   # 실제 마지막 두 주차 (하드코딩 제거)
    rows = [f"| 지표 | {prev} | {curr} | 변화율(%) | 상태 |", "|------|----|----|----------|------|"]
    label = {'spend': '지출', 'revenue': '매출', 'conversions': '전환수', 'CTR': 'CTR'}
    max_abs = 0
    for m in ['spend', 'revenue', 'conversions', 'CTR']:
        r = wow_df.loc[m]
        chg = r['change_pct']
        max_abs = max(max_abs, abs(chg))
        state = "↑↑" if chg >= 50 else "↑" if chg > 5 else "→" if chg >= -5 else "↓↓" if chg <= -50 else "↓"
        v0 = f"{r[prev]:,.0f}" if m != 'CTR' else f"{r[prev]:.2f}%"
        v1 = f"{r[curr]:,.0f}" if m != 'CTR' else f"{r[curr]:.2f}%"
        rows.append(f"| {label[m]} | {v0} | {v1} | {chg:+.2f} | {state} |")
    verdict = (f"모든 지표가 ±50% 이내(최대 변동 {max_abs:.2f}%)로 {prev}→{curr}는 안정적. 급변 없음."
               if max_abs < 50 else f"일부 지표가 ±50%를 초과({prev}→{curr} 최대 {max_abs:.2f}%) — 급변 발생, 원인 확인 필요.")
    rows.append(f"\n> {verdict}\n")
    return "\n".join(rows)


_DIR_ORDER = ['증액 후보', '유지', '개선 우선', '측정불가']
_DIR_LABEL = {'증액 후보': '증액 후보', '유지': '유지', '개선 우선': '개선 우선',
              '측정불가': '측정불가(별도 판단)'}


def _benchmark(ranked):
    b = ranked['benchmark']
    rows = [
        "> **여기서 '등급'은 우리 회사 주차 비교가 아니라, 같은 채널을 운영하는 업계 분포(2026 한국 시장 벤치마크, "
        "industry-news.md) 대비 위치다.** 출처가 업계 통용 추정치라 정성 판단용으로만 쓰고 원(₩) 랭킹엔 넣지 않는다.\n",
        "> 등급의 뜻과 그에 따른 조치:",
        "> - **우수(상위25%↑)**: 그 채널을 쓰는 회사들 상위 25%보다 잘함 → 검증된 효율, 증액해도 효율 유지 기대(증액 후보)",
        "> - **평균이상**: 시장 중간보다 나음 → 현상 유지·소폭 최적화",
        "> - **개선여지(평균 이하)**: 시장 중간에 못 미침 → 증액 보류, 원인부터 개선",
        "> - 종합 등급은 최종 성과인 **ROAS** 기준. CTR·CVR은 퍼널 어디가 약한지 진단용(CTR 약함=소재·타겟, CVR 약함=랜딩·오퍼).\n",
        "> **활용**: 맨 오른쪽 '제안 방향' 열이 곧 예산 액션입니다 — 증액 후보부터 늘리고, 개선 우선 채널은 원인 교정 후 재검토, 유지 채널은 현상 유지하세요.\n",
        "| 채널 | CTR | CVR | ROAS(종합) | 제안 방향 |",
        "|------|-----|-----|-----------|-----------|",
    ]
    for _, r in b.iterrows():
        roas_cell = "측정불가" if pd.isna(r['ROAS']) else f"{r['ROAS']:.2f}({BAND_SHORT[r['roas_band']]})"
        rows.append(f"| {r['channel']} | {r['CTR']:.2f}%({BAND_SHORT[r['ctr_band']]}) | "
                    f"{r['CVR']:.2f}%({BAND_SHORT[r['cvr_band']]}) | {roas_cell} | {r['action']} |")

    groups = {}
    for _, r in b.iterrows():
        groups.setdefault(r['direction'], []).append(r['channel'])
    parts = [f"{_DIR_LABEL[d]} = {', '.join(groups[d])}" for d in _DIR_ORDER if d in groups]
    rows.append(f"\n**핵심 인사이트 (예산 방향)**: {' / '.join(parts)}. "
                "종합 등급은 ROAS(시장 대비 매출효율) 기준이라, 절대 ROI 순위가 높아도 자기 채널 시장 벤치마크로는 "
                "미달일 수 있다(예: 이메일 — 절대 ROI 1위지만 CRM 벤치마크 대비 개선여지). "
                "증액은 '증액 후보'부터, '개선 우선' 채널은 원인 교정 후 재검토한다.\n")
    return "\n".join(rows)


def _opportunity(ranked):
    rows = []
    for _, r in ranked['opportunity'].iterrows():
        rows.append(f"- **{r['channel']}**: {r['note']}")
    rows.append("\n> **오가닉은 '무료'가 아니다.** 과거 유료 광고의 낙수효과(브랜딩→검색·직접 유입)와 "
                "SEO·콘텐츠 투자가 누적된 결과이며, 단지 현재 기간 광고비 원장에 직접 귀속되는 클릭당 비용이 0일 뿐이다. "
                "광고비를 직접 배정하는 채널이 아니므로 'SEO·콘텐츠 투자 확대' 또는 '브랜딩 광고의 낙수효과 활용'으로 키운다 "
                "(industry-news 채널 믹스 전략).\n>\n"
                "> ⚠️ 오가닉 매출의 일부는 유료 채널(특히 브랜딩)의 기여이므로, 채널 ROI를 독립적으로 비교하면 "
                "이 교차 기여를 놓친다. 정밀 예산 배분은 MTA/MMM 등 교차 채널 기여 분석이 필요하다(industry-news 트렌드 2).\n")
    return "\n".join(rows)


def build_summary_points(d):
    """요약 박스 항목 (라벨, 내용) 리스트 — md·html이 공유(표현만 다르고 수치·판단은 동일).

    한 곳에서만 요약 로직을 만들어 md↔html 불일치를 원천 차단한다(decisions Step 21 원칙).
    ① 전체 성과 ② 바로 실행할 예산 액션 ③ 최우선 실행 이슈 + 데이터 정정 규모(분리) ④ 최근 안정성.
    재원 없음·이슈 없음 등 조건부에도 문장이 성립하도록 분기한다.
    """
    s, ranked, plans, wow = d['summary'], d['ranked'], d['plans'], d['wow']
    t = s['total']
    pts = [("이번 기간 성과",
            f"총매출 {won(t['total_revenue'])} · 유료 광고비 {won(t['total_spend'])} "
            f"(MER {t['mer']:.0f}%, 유료 순효율 {t['paid_roi']:.0f}%, 전환 {t['total_conversions']:,.0f}건)")]

    if not plans.empty:
        p = plans.iloc[0]
        exp = f", 순증 매출 상한 약 {won(p['expected_won'])}" if not pd.isna(p['expected_won']) else ""
        pts.append(("바로 실행할 예산 액션",
                    f"{p['source']} → {p['target']} {won(p['amount_won'])} 재배분{exp} "
                    f"(우선순위 1순위, 상세: budget_reallocation.md)"))
    else:
        pts.append(("예산 액션", "과집행 등 재배분 재원이 없어 현 배분 유지 권장"))

    loss = ranked.get('loss')
    if loss is not None and not loss.empty:
        act = loss[loss['lever'] == '예산']
        if not act.empty:
            top = act.iloc[0]
            pts.append(("최우선 실행 이슈",
                        f"{top['channel']} {top['type']} — 기회손실 {won(top['impact_won'])} "
                        f"({top['weeks']}), 예산 재배분으로 대응"))
        data_loss = loss[loss['lever'] == '데이터·트래킹']
        if not data_loss.empty:
            pts.append(("데이터 정정 필요(예산 조치 아님)",
                        f"{len(data_loss)}건, 왜곡·추정 금액 합 {won(data_loss['impact_won'].sum())} "
                        f"— 원본 재확인·트래킹 점검 대상(손실 아님)"))

    prev, curr = wow.columns[0], wow.columns[1]
    max_abs = wow['change_pct'].abs().max()
    stat = "안정적, 급변 없음" if max_abs < 50 else "급변 발생 — 원인 확인 필요"
    pts.append((f"최근 추세({prev}→{curr})", f"{stat} (최대 변동 {max_abs:.1f}%)"))
    return pts


def build_playbook(d):
    """리포트 곳곳에 흩어진 조치를 '이번 주 실행 플레이북' 한 리스트로 취합 — md·html 공유.

    입력: run_pipeline 결과(ranked·plans). 출력: dict 리스트 [{rank, action, basis, owner, when}].
    이미 계산된 판단(재배분·손실·벤치마크·관찰·긍정)을 실무 액션으로 '번역'만 한다 — 새 계산 없음.
    담당·시점을 붙여 리포트를 '읽을거리'에서 '업무 분배 도구'로 바꾼다. tier(1급함~3)로 정렬.
    """
    ranked, plans = d['ranked'], d['plans']
    items = []   # 각 항목에 trank(유형 우선), amt(동유형 내 금액 정렬용) 부여. 최종 정렬은 시점→유형→금액.

    if not plans.empty:   # 예산 재배분 — 실제 회수 가능한 손실·즉시. 시점 최상단.
        p = plans.iloc[0]
        exp = f", 순증 상한 {won(p['expected_won'])}" if not pd.isna(p['expected_won']) else ""
        items.append({'trank': 0, 'amt': p['priority_score'],
                      'action': f"{p['source']} 과집행 차단 후 회수분을 {p['target']}에 재배분",
                      'basis': f"초과지출 {won(p['amount_won'])}{exp} · 상세: 예산 재배분 기획안",
                      'owner': '마케팅 리드', 'when': '즉시'})

    loss = ranked.get('loss')
    if loss is not None and not loss.empty:   # 데이터 정정 — 수치 신뢰도, 왜곡 금액 큰 순
        for _, r in loss[loss['lever'] == '데이터·트래킹'].iterrows():
            items.append({'trank': 1, 'amt': r['impact_won'],
                          'action': f"{r['channel']} {r['type']} 원본 재확인·보정",
                          'basis': f"왜곡·추정 {won(r['impact_won'])} (예산 손실 아님)",
                          'owner': '트래킹팀', 'when': '이번 주'})

    b = ranked.get('benchmark')
    covered = set(plans['target']) if not plans.empty else set()
    if b is not None and not b.empty:   # 벤치마크 방향 — 증액 후보(미커버)·개선 우선만 (유지는 제외)
        for _, r in b.iterrows():
            if r['direction'] == '증액 후보' and r['channel'] not in covered:
                items.append({'trank': 2, 'amt': 0,
                              'action': f"{r['channel']} 증액 검토",
                              'basis': str(r['action']), 'owner': '마케팅 리드', 'when': '이번 주'})
            elif r['direction'] == '개선 우선':
                items.append({'trank': 4, 'amt': 0,
                              'action': f"{r['channel']} 효율 개선 (증액 보류)",
                              'basis': str(r['action']), 'owner': '채널 담당', 'when': '이번 달'})

    op = ranked.get('operational')
    if op is not None and not op.empty:   # 운영 관찰 — 의도 여부 확인
        for _, r in op.iterrows():
            items.append({'trank': 3, 'amt': 0,
                          'action': f"{r['channel']} {r['type']} 의도 여부 담당자 확인",
                          'basis': f"{r['week']} 발생 · 의도적 조정인지 불명",
                          'owner': '채널 담당', 'when': '이번 주'})

    pos = ranked.get('positive')
    if pos is not None and not pos.empty:   # 긍정 신호 — 성공요인 분석·확대
        for _, r in pos.iterrows():
            items.append({'trank': 5, 'amt': 0,
                          'action': f"{r['channel']} 성공요인 분석 후 확대 검토",
                          'basis': f"{r['week']} 성과 호재", 'owner': '마케팅 리드', 'when': '이번 달'})

    when_rank = {'즉시': 0, '이번 주': 1, '이번 달': 2}
    items.sort(key=lambda x: (when_rank[x['when']], x['trank'], -x['amt']))
    for i, it in enumerate(items, 1):
        it['rank'] = i
    return items


def _playbook_md(d):
    items = build_playbook(d)
    head = ["> 리포트 전체에 흩어진 조치를 **우선순위·담당·시점**으로 취합했습니다. 이 표만으로 이번 주 팀 업무 분배가 됩니다. "
            "(담당은 역할 예시 — 조직의 실제 담당자로 대체)\n"]
    if not items:
        return "\n".join(head) + "\n이번 주 특별히 실행할 조치가 탐지되지 않았습니다 — 현 운영을 유지하세요.\n"
    rows = ["| 순위 | 할 일 | 근거 | 담당 | 시점 |", "|------|------|------|------|------|"]
    for it in items:
        rows.append(f"| {it['rank']} | {it['action']} | {it['basis']} | {it['owner']} | {it['when']} |")
    return "\n".join(head + rows) + "\n"


def _executive_summary(d):
    """리포트 최상단 요약 박스 md (갭1) — 경영진이 받자마자 성과·액션·위험을 얻도록."""
    lines = ["## 한눈에 보기 (Executive Summary)\n",
             "> 상세는 아래 섹션. 이 박스만으로 '전체 성과 · 지금 할 일 · 위험'을 먼저 판단할 수 있게 요약.\n"]
    for label, body in build_summary_points(d):
        lines.append(f"- **{label}**: {body}")
    lines.append("")
    return "\n".join(lines)


def _decisions(threshold):
    # 방법론(데이터와 무관하게 고정)만 기술 — 특정 수치·날짜는 데이터마다 달라지므로 넣지 않음.
    # 임계값은 데이터 적응형이라 이번 기간 산출값을 표기(고정 상수 아님).
    return ("상세 근거·이력은 decisions.md 참조. 적용한 방법론:\n"
            "- 결측: NaN 유지(0으로 채우지 않음), 집계 자동 제외\n"
            "- 매출 이상치: 채널별 AOV modified z-score>3.5로 동적 탐지 → revenue만 제외(정상 지출·전환 보존)\n"
            "- 완전 중복 행: drop_duplicates로 제거(집계 부풀림 방지)\n"
            "- 전체 ROI: MER(오가닉 포함)·유료 순효율·오가닉 매출 3종 분리 표기\n"
            f"- 이슈 탐지: LOO 중앙값 기준선 + 데이터 적응형 임계값(Tukey IQR 펜스, 하한 25%) "
            f"— 이번 기간 {threshold*100:.0f}% + 원(₩) 임팩트 정렬. 과집행은 'ROAS 하락' 조건\n"
            "- 채널 평가: 내부 순위가 아닌 industry-news 벤치마크 대비 정성 판정\n")


def build_report(data_path=DATA, data=None):
    """insight_report.md를 생성한다. data(run_pipeline 결과)를 받으면 재사용, 없으면 직접 실행.

    html 생성기와 같은 결과를 공유하도록 data 주입을 허용 — 수치가 md·html 간 어긋나지 않게.
    """
    d = data or run_pipeline(data_path)
    s, ranked, wow = d['summary'], d['ranked'], d['wow']
    prev, curr = wow.columns[0], wow.columns[1]
    # 섹션은 (제목, 본문) 리스트로 모아 번호를 동적으로 매긴다.
    # 기회 섹션은 조건(유의미한 오가닉 매출)을 만족할 때만 존재하므로, 빠져도 번호에 구멍이 안 생긴다.
    sections = [
        ("데이터 개요", _overview(d['meta'])),
        ("핵심 수치 요약", _summary(s)),
        ("채널별 ROI 순위", _roi_rank(d['roi'])),
        ("이슈 (비즈니스 임팩트 순)", _issues(ranked, d['recency'], d['threshold'])),
        (f"전주 대비 변화율 ({prev} → {curr})", _wow(wow)),
        ("채널 평가 (시장 벤치마크 대비)", _benchmark(ranked)),
    ]
    if 'opportunity' in ranked:   # 유의미한 오가닉이 있을 때만 포함 (없으면 생략, KeyError 방지)
        sections.append(("오가닉 성장 잠재력", _opportunity(ranked)))
    sections.append(("의사결정 로그 요약", _decisions(d['threshold'])))

    parts = ["# 마케팅 성과 인사이트 리포트\n",
             "> 계산: Python (calculate.py) · 이슈 탐지: detect_issues.py · 해석: 규칙 기반 + Claude\n",
             "## 이 리포트 사용법\n\n" + _usage_guide(d['meta']),
             _executive_summary(d),
             "## 🎯 이번 주 실행 플레이북\n\n" + _playbook_md(d)]
    for i, (title, body) in enumerate(sections, 1):
        parts.append(f"## {i}. {title}\n\n{body}")
    report = "\n---\n\n".join(parts)
    # 물결표(~)는 마크다운에서 쌍으로 만나면 취소선(~~)이 되어 글자가 지워져 보인다.
    # 본 리포트의 ~는 모두 범위 표기(W1~W8, 날짜)이므로 엔대시로 치환해 취소선 오작동을 원천 차단.
    return report.replace('~', '–')


if __name__ == '__main__':
    # 사용법: python3 src/generate_report.py [입력CSV] [출력MD]  (인자 생략 시 기본 샘플·경로)
    data_path = sys.argv[1] if len(sys.argv) > 1 else DATA
    out_path = sys.argv[2] if len(sys.argv) > 2 else OUT
    report = build_report(data_path)
    with open(out_path, 'w') as f:
        f.write(report)
    print(f"생성 완료: {out_path} ({len(report):,}자) ← 입력: {data_path}")
