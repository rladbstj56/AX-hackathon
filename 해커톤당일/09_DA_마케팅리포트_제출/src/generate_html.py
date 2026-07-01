"""HTML 대시보드 생성 — md와 같은 run_pipeline 결과를 카드·막대·표로 렌더링한다.

md 생성기(generate_report·reallocate)와 동일한 계산 결과 dict를 소비하므로 수치가 어긋나지 않는다.
이미지 차트(Matplotlib/Plotly)는 쓰지 않고 CSS 요소로만 시각화 → 과제 제약(이미지 차트 제외) 준수.
사용법: python3 src/generate_html.py [입력CSV]  → output/insight_report.html·budget_reallocation.html
"""
import sys
from html import escape

import pandas as pd

from detect_issues import BAND_SHORT
from generate_report import build_summary_points, build_playbook, _status
from reallocate import (run_pipeline, build_action_checklist, plan_lead_sentence,
                        PRIORITY_CRITERIA, PRIORITY_CAVEAT)

INSIGHT_OUT = 'output/insight_report.html'
REALLOC_OUT = 'output/budget_reallocation.html'

# 조치 레버 → 태그 색상 클래스. 예산=회수·이동 대상(강조), 데이터=예산 무관(중립), 운영=최적화.
_LEVER_CLASS = {'예산': 't-budget', '데이터·트래킹': 't-data',
                '운영·크리에이티브': 't-ops', '전략': 't-strat'}
# 벤치마크 등급 → 태그 색상. 우수>평균이상>개선여지>미흡.
_BAND_CLASS = {'상위25% 이상(우수)': 't-best', '평균 이상': 't-mid',
               '평균 이하(개선여지)': 't-low', '하위25% 이하(미흡)': 't-low', '측정불가': 't-na'}

CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans KR', sans-serif; background: #f4f5f7; color: #1a1a2e; line-height: 1.6; }
.container { max-width: 1080px; margin: 0 auto; padding: 40px 24px; }
.header { background: #fff; border-radius: 12px; padding: 32px 36px; margin-bottom: 24px; border-left: 5px solid #2d6a4f; box-shadow: 0 1px 4px rgba(0,0,0,.06); }
.header.rx { border-left-color: #7048e8; }
.badge { display: inline-block; background: #2d6a4f; color: #fff; font-size: 12px; font-weight: 600; padding: 4px 12px; border-radius: 20px; margin-bottom: 14px; letter-spacing: .5px; }
.badge.rx { background: #7048e8; }
.header h1 { font-size: 22px; font-weight: 700; margin-bottom: 10px; }
.header-meta { font-size: 13px; color: #6c757d; display: flex; flex-wrap: wrap; gap: 16px; }
.stats-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 24px; }
.stat { background: #fff; border-radius: 10px; padding: 20px; text-align: center; box-shadow: 0 1px 4px rgba(0,0,0,.06); border-top: 4px solid; }
.stat-n { font-size: 26px; font-weight: 800; }
.stat-label { font-size: 13px; color: #666; margin-top: 2px; }
.stat-sub { font-size: 12px; color: #999; margin-top: 4px; }
.c-red { border-color: #e63946; color: #e63946; } .c-blue { border-color: #4361ee; color: #4361ee; }
.c-green { border-color: #2d6a4f; color: #2d6a4f; } .c-purple { border-color: #7048e8; color: #7048e8; }
.section { background: #fff; border-radius: 12px; padding: 28px 32px; margin-bottom: 24px; box-shadow: 0 1px 4px rgba(0,0,0,.06); }
.section-title { font-size: 15px; font-weight: 700; padding-bottom: 14px; margin-bottom: 20px; border-bottom: 1px solid #eee; }
.note { font-size: 12px; color: #888; margin-bottom: 14px; }
.bar-row { margin-bottom: 12px; }
.bar-meta { display: flex; justify-content: space-between; font-size: 13px; margin-bottom: 5px; font-weight: 600; }
.bar-track { background: #f0f2f5; border-radius: 6px; height: 30px; overflow: hidden; }
.bar-fill { height: 100%; border-radius: 6px; display: flex; align-items: center; padding-left: 12px; color: #fff; font-size: 12px; font-weight: 700; }
.bar-na { height: 30px; background: repeating-linear-gradient(45deg,#eef0f3,#eef0f3 8px,#e3e6ea 8px,#e3e6ea 16px); border-radius: 6px; display: flex; align-items: center; padding-left: 12px; color: #888; font-size: 12px; font-weight: 700; }
.tbl-wrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
thead th { background: #f8f9fa; font-size: 12px; font-weight: 700; color: #6c757d; padding: 10px 12px; text-align: left; border-bottom: 2px solid #e9ecef; white-space: nowrap; }
tbody td { padding: 9px 12px; border-bottom: 1px solid #f0f2f5; vertical-align: middle; }
tbody tr:hover { background: #f8f9fb; }
td.num { text-align: right; font-variant-numeric: tabular-nums; }
td.lnum { text-align: left; font-variant-numeric: tabular-nums; }
.rank { font-weight: 800; color: #4361ee; }
.tag { display:inline-block; font-size:11px; font-weight:700; padding:2px 8px; border-radius:5px; }
.t-best { background:#d0ebe0; color:#1f5c3d; } .t-mid { background:#dde3ff; color:#3452cc; }
.t-low { background:#fff3cd; color:#856404; } .t-na { background:#e9ecef; color:#495057; }
.t-budget { background:#ffe0d6; color:#b5341a; } .t-data { background:#e9ecef; color:#495057; }
.t-ops { background:#dde3ff; color:#3452cc; } .t-strat { background:#e7dcff; color:#5b34b5; }
.chg-up { color:#2d6a4f; font-weight:700; } .chg-down { color:#e63946; font-weight:700; }
.issue { border:1px solid #eee; border-left:4px solid #e63946; border-radius:8px; padding:16px 18px; margin-bottom:14px; }
.issue.budget { border-left-color:#e8590c; } .issue.data { border-left-color:#868e96; }
.issue-h { font-size:14px; font-weight:700; margin-bottom:8px; display:flex; gap:8px; align-items:center; flex-wrap:wrap; }
.issue-row { font-size:13px; margin-top:4px; } .issue-row b { color:#555; }
.plan { border:1px solid #e7dcff; border-left:4px solid #7048e8; border-radius:8px; padding:18px 20px; margin-bottom:16px; }
.plan-h { font-size:14px; font-weight:700; margin-bottom:10px; }
.plan-h .pr { background:#7048e8; color:#fff; border-radius:6px; padding:2px 9px; font-size:12px; margin-right:8px; }
.callout { background:#f8f6ff; border-radius:8px; padding:14px 18px; font-size:13px; color:#4a3a7a; margin-top:6px; }
.summary { background:#fff; border-radius:12px; padding:24px 28px; margin-bottom:24px; border-left:5px solid #2d6a4f; box-shadow:0 1px 4px rgba(0,0,0,.06); }
.summary h2 { font-size:16px; margin-bottom:6px; } .summary .note { margin-bottom:12px; }
.summary ul { list-style:none; } .summary li { font-size:13px; padding:7px 0; border-bottom:1px solid #f0f2f5; }
.summary li:last-child { border-bottom:none; } .summary li b { color:#2d6a4f; }
.foot { font-size:12px; color:#999; text-align:center; padding:8px 0 4px; }
ol.crit { margin:6px 0 0 18px; } ol.crit li { font-size:13px; margin-bottom:8px; }
.guide { background:#f0f7f4; border-radius:12px; padding:20px 26px; margin-bottom:24px; border-left:5px solid #40916c; box-shadow:0 1px 4px rgba(0,0,0,.06); }
.guide.rx { background:#f6f2ff; border-left-color:#7048e8; }
.guide h3 { font-size:15px; margin-bottom:10px; } .guide .note { margin-bottom:10px; }
.guide ul { list-style:none; } .guide li { font-size:13px; padding:5px 0; }
.guide li b { color:#2d6a4f; } .guide.rx li b { color:#5b34b5; }
.checklist { background:#fff; border-radius:12px; padding:22px 28px; margin-bottom:24px; border-left:5px solid #e8590c; box-shadow:0 1px 4px rgba(0,0,0,.06); }
.checklist h3 { font-size:15px; margin-bottom:6px; } .checklist .note { margin-bottom:12px; }
.checklist ul { list-style:none; } .checklist li:last-child { border-bottom:none; }
.checklist li { font-size:14px; padding:10px 0 10px 30px; border-bottom:1px solid #f0f2f5; position:relative; }
.checklist li:before { content:'☐'; position:absolute; left:0; top:8px; font-size:17px; color:#e8590c; }
.playbook { border-left:5px solid #e8590c; }
.pb-rank { font-weight:800; color:#e8590c; text-align:center; }
.when-now { color:#e63946; font-weight:700; } .when-wk { color:#e8590c; font-weight:700; } .when-mo { color:#6c757d; font-weight:600; }
td.owner { color:#495057; white-space:nowrap; }
.plan-lead { background:#f8f6ff; border-radius:8px; padding:13px 16px; font-size:14px; line-height:1.7; margin:2px 0 14px; }
.plan-lead b { color:#5b34b5; }
.flow { display:flex; align-items:center; justify-content:center; gap:14px; flex-wrap:wrap; margin:6px 0 16px; }
.flow-node { border-radius:10px; padding:12px 18px; text-align:center; min-width:132px; }
.flow-node.from { border:2px solid #f1b0b7; background:#fff5f4; }
.flow-node.to { border:2px solid #9dc9b4; background:#f2f9f5; }
.flow-node .fn-name { font-weight:700; font-size:15px; }
.flow-node .fn-roas { font-size:11px; color:#777; margin-top:3px; }
.flow-node .fn-amt { font-size:14px; font-weight:800; margin-top:7px; }
.fn-amt.neg { color:#e63946; } .fn-amt.pos { color:#2d6a4f; }
.flow-arrow { text-align:center; color:#7048e8; line-height:1.35; }
.flow-arrow .fa-amt { font-size:13px; font-weight:700; } .flow-arrow .fa-line { font-size:24px; }
.ratio { display:inline-block; background:#7048e8; color:#fff; font-size:11px; font-weight:700; padding:2px 9px; border-radius:11px; margin-top:3px; }
.plan .subhead { font-size:12px; color:#999; margin:12px 0 6px; font-weight:700; }
"""


def _won(x):
    return f"{x:,.0f}원"


def _page(title, badge_cls, body):
    return (f"<!DOCTYPE html>\n<html lang=\"ko\">\n<head>\n<meta charset=\"UTF-8\">\n"
            f"<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n"
            f"<title>{escape(title)}</title>\n<style>{CSS}</style>\n</head>\n<body>\n"
            f"<div class=\"container\">\n{body}\n</div>\n</body>\n</html>\n")


def _stat(n, label, sub, color):
    sub_html = f'<div class="stat-sub">{escape(sub)}</div>' if sub else ''
    return f'<div class="stat {color}"><div class="stat-n">{escape(n)}</div><div class="stat-label">{escape(label)}</div>{sub_html}</div>'


def _roi_bars(summary, roi):
    """채널 ROI를 막대로. 최상위 ROI를 100% 폭 기준으로 정규화. 오가닉은 측정불가 빗금 막대."""
    colors = ['#2d6a4f', '#4361ee', '#4895ef', '#4cc9f0']
    top = roi['ROI'].max()
    bars = []
    for i, (ch, r) in enumerate(roi.iterrows()):
        w = max(6, r['ROI'] / top * 100)
        c = colors[i] if i < len(colors) else '#8390fa'
        bars.append(f'<div class="bar-row"><div class="bar-meta"><span>{i+1}. {escape(ch)}</span>'
                    f'<span>{r["ROI"]:.2f}% · ROAS {r["revenue"]/r["spend"]:.2f}</span></div>'
                    f'<div class="bar-track"><div class="bar-fill" style="width:{w:.1f}%;background:{c}">{r["ROI"]:.0f}%</div></div></div>')
    g = summary['by_channel']
    for ch in g.index:
        if g.loc[ch, 'spend'] == 0:
            bars.append(f'<div class="bar-row"><div class="bar-meta"><span>– {escape(ch)}</span>'
                        f'<span>측정 불가</span></div><div class="bar-na">광고비 0원 (오가닉)</div></div>')
    return "".join(bars)


def _channel_table(summary):
    g = summary['by_channel'].sort_values('revenue', ascending=False)
    rows = []
    for ch in g.index:
        r = g.loc[ch]
        roi = "측정불가" if pd.isna(r['ROI']) else f"{r['ROI']:.2f}%"
        roas = "–" if pd.isna(r['ROAS']) else f"{r['ROAS']:.2f}"
        cpa = "–" if pd.isna(r['CPA']) else f"{r['CPA']:,.0f}"
        rows.append(f"<tr><td>{escape(ch)}</td><td class='num'>{r['spend']:,.0f}</td>"
                    f"<td class='num'>{r['revenue']:,.0f}</td><td class='num'>{r['conversions']:,.0f}</td>"
                    f"<td class='num'>{roi}</td><td class='num'>{roas}</td><td class='num'>{cpa}</td>"
                    f"<td class='num'>{r['CTR']:.2f}%</td><td class='num'>{r['CVR']:.2f}%</td></tr>")
    return ("<p class='note'>CPA(전환당 비용) = 광고비 / 전환. 낮을수록 효율적. 오가닉은 광고비 0이라 측정 제외(–).</p>"
            "<div class='tbl-wrap'><table><thead><tr><th>채널</th><th>광고비</th><th>매출</th>"
            "<th>전환</th><th>ROI</th><th>ROAS</th><th>CPA</th><th>CTR</th><th>CVR</th></tr></thead><tbody>"
            + "".join(rows) + "</tbody></table></div>")


def _usage_guide_html(meta):
    """진단 리포트 상단 '사용법' 박스 html — md _usage_guide와 같은 내용, 렌더만 다름."""
    return ("<div class='guide'><h3>📖 이 리포트, 이렇게 쓰세요</h3><ul>"
            f"<li><b>무엇</b> · 지난 {meta['n_weeks']}주 마케팅 성과를 데이터에서 직접 계산·해석한 주간 점검 리포트</li>"
            "<li><b>누가·언제</b> · [경영진] 성과 브리핑 때 '한눈에 보기'만 / [마케터] 주간 예산·소재 결정 때 이슈·채널 평가 근거로</li>"
            "<li><b>읽는 순서</b> · ① 한눈에 보기 → ② 이번 주 실행 플레이북(할 일 전체) → ③ 이슈·채널 평가(근거) → ④ 전주 대비 변화율(급변 감시)</li>"
            "<li><b>액션 연결</b> · [예산] 태그→예산 재배분 기획안, [데이터·트래킹]→트래킹팀 정정, [운영]→채널 담당자 확인</li>"
            "</ul></div>")


def _rx_usage_html():
    """재배분 기획안 상단 '읽고 실행하는 법' 박스 html."""
    return ("<div class='guide rx'><h3>📖 이 기획안, 읽고 실행하는 법</h3>"
            "<p class='note'>이 문서가 답하는 질문: \"회수 가능한 예산을 어디로 옮겨야 매출이 늘까?\"</p><ul>"
            "<li><b>1단계</b> · §1 재원 요약에서 회수가능액(확실히 뺄 돈) 확인 — 임팩트는 우선순위 참고용 추정치</li>"
            "<li><b>2단계</b> · §2 재배분안을 1순위부터 — [어디→어디, 얼마] + [기대효과·한계] 확인</li>"
            "<li><b>3단계</b> · 1순위를 소액 테스트 집행 → 2주 후 ROAS 재측정 → 개선 시 확대, 아니면 다음 순위</li>"
            "<li><b>주의</b> · 여러 안이 같은 재원 공유 시 돈은 한 번만 — 동시 집행 금지</li>"
            "</ul></div>")


def _checklist_html(data):
    """데이터 파생 '지금 당장 할 일' 체크리스트 html — md와 동일한 build_action_checklist를 렌더."""
    items = "".join(f"<li>{escape(it)}</li>" for it in build_action_checklist(data))
    return ("<div class='checklist'><h3>✅ 지금 당장 할 일 (이번 데이터 기준)</h3>"
            "<p class='note'>아래 순서대로 실행하세요. 수치는 이번 성과 데이터에서 자동 산출된 값입니다.</p>"
            f"<ul>{items}</ul></div>")


_WHEN_CLASS = {'즉시': 'when-now', '이번 주': 'when-wk', '이번 달': 'when-mo'}


def _playbook_html(data):
    """'이번 주 실행 플레이북' 표 html — md와 동일한 build_playbook을 렌더만 다르게."""
    items = build_playbook(data)
    note = ("<p class='note'>리포트 전체에 흩어진 조치를 우선순위·담당·시점으로 취합 — 이 표만으로 이번 주 팀 업무 분배가 됩니다. "
            "(담당은 역할 예시로, 조직의 실제 담당자로 대체)</p>")
    if not items:
        return ('<div class="section playbook"><div class="section-title">🎯 이번 주 실행 플레이북</div>'
                f'{note}<p>이번 주 특별히 실행할 조치가 없습니다 — 현 운영을 유지하세요.</p></div>')
    rows = "".join(
        f"<tr><td class='pb-rank'>{it['rank']}</td><td>{escape(it['action'])}</td>"
        f"<td>{escape(it['basis'])}</td><td class='owner'>{escape(it['owner'])}</td>"
        f"<td class='{_WHEN_CLASS.get(it['when'], '')}'>{escape(it['when'])}</td></tr>" for it in items)
    return ('<div class="section playbook"><div class="section-title">🎯 이번 주 실행 플레이북</div>'
            f"{note}<div class='tbl-wrap'><table><thead><tr><th>순위</th><th>할 일</th>"
            "<th>근거</th><th>담당</th><th>시점</th></tr></thead><tbody>"
            f"{rows}</tbody></table></div></div>")


def _exec_summary_html(data):
    """리포트 최상단 요약 박스 html (갭1) — md와 동일한 build_summary_points를 렌더링만 다르게."""
    items = "".join(f"<li><b>{escape(label)}</b> · {escape(body)}</li>"
                    for label, body in build_summary_points(data))
    return ("<div class='summary'><h2>한눈에 보기 (Executive Summary)</h2>"
            "<p class='note'>이 박스만으로 '전체 성과 · 지금 할 일 · 위험'을 먼저 판단하도록 요약.</p>"
            f"<ul>{items}</ul></div>")


def _issue_card(r, i, kind, recency, threshold):
    """손실 이슈 카드 1개 — kind='실행'(예산·운영)이면 '기회손실', '정정'(데이터)이면 '왜곡·추정 금액'."""
    lever = r['lever']
    cls = 'budget' if kind == '실행' else 'data'
    label = '이슈' if kind == '실행' else '정정'
    amt_label = '기회손실' if kind == '실행' else '왜곡·추정 금액'
    tag = f"<span class='tag {_LEVER_CLASS.get(lever, 't-na')}'>{escape(lever)}</span>"
    rows = [f"<div class='issue-row'><b>현상·근거</b> {escape(str(r['note']))}</div>",
            f"<div class='issue-row'><b>발생</b> {escape(str(r['weeks']))} (빈도 {r['frequency']}주)</div>"]
    st = _status(r['type'], r['channel'], recency, threshold)
    if st:
        rows.append(f"<div class='issue-row'>{escape(st.lstrip('- '))}</div>")
    return (f"<div class='issue {cls}'>"
            f"<div class='issue-h'>{label} {i}: {escape(r['channel'])} — {escape(r['type'])} {tag}"
            f"<span style='margin-left:auto;color:#e63946'>{amt_label} {_won(r['impact_won'])}</span></div>"
            + "".join(rows) + "</div>")


def _note_card(r, i, label, recency, threshold, show_status):
    """운영관찰·긍정·품질 항목 카드 — 번호 헤더 + 현상·최근성(선택)으로 loss 카드와 형식 통일."""
    rows = [f"<div class='issue-row'><b>현상·근거</b> {escape(str(r['note']))}</div>"]
    if show_status:
        st = _status(r['type'], r['channel'], recency, threshold)
        if st:
            rows.append(f"<div class='issue-row'>{escape(st.lstrip('- '))}</div>")
    return (f"<div class='issue data'>"
            f"<div class='issue-h'>{label} {i}: {escape(r['channel'])} — {escape(r['type'])} "
            f"<span class='tag t-na'>{escape(str(r['week']))}</span></div>"
            + "".join(rows) + "</div>")


def _issue_cards(ranked, recency, threshold):
    loss = ranked.get('loss')
    actionable = loss[loss['lever'] != '데이터·트래킹'] if loss is not None and not loss.empty else None
    data_fix = loss[loss['lever'] == '데이터·트래킹'] if loss is not None and not loss.empty else None

    def _h4(text, mt='16px'):
        return f"<h4 style='font-size:13px;margin:{mt} 0 8px'>{text}</h4>"

    out = ["<p class='note'>손실을 <b>예산·운영으로 실행 가능한 손실</b>과 <b>데이터 정정 사안</b>으로 분리 — 성격이 달라 조치도 다름.</p>",
           _h4("실행 가능한 손실 (예산·운영 — 바로 조치)", '6px')]
    if actionable is None or actionable.empty:
        out.append("<p class='note'>예산·운영 레버로 실행할 손실 이슈 없음.</p>")
    else:
        out += [_issue_card(r, i, '실행', recency, threshold) for i, (_, r) in enumerate(actionable.iterrows(), 1)]

    out.append(_h4("데이터 정정 필요 (예산 조치 아님)"))
    out.append("<p class='note'>아래 금액은 잃은 돈이 아니라 <b>데이터가 왜곡·누락된 규모</b>다. 원본 재확인·수동 보정 대상(수치 신뢰도 이슈).</p>")
    if data_fix is None or data_fix.empty:
        out.append("<p class='note'>데이터 정정이 필요한 손실 사안 없음.</p>")
    else:
        out += [_issue_card(r, i, '정정', recency, threshold) for i, (_, r) in enumerate(data_fix.iterrows(), 1)]

    # 운영관찰·긍정·품질도 md와 동일하게 번호 카드로 렌더 (형식 통일).
    for cat, title, label, show_status in [
        ('operational', '운영 관찰 (손실은 아니나 확인 필요)', '관찰', True),
        ('positive', '주목할 긍정 신호', '긍정', True),
        ('quality', '데이터 수집 품질 이슈', '품질', False),
    ]:
        sub = ranked.get(cat)
        if sub is not None and not sub.empty:
            out.append(_h4(title))
            out += [_note_card(r, i, label, recency, threshold, show_status)
                    for i, (_, r) in enumerate(sub.iterrows(), 1)]
    return "".join(out)


def _wow_table(wow):
    prev, curr = wow.columns[0], wow.columns[1]
    label = {'spend': '지출', 'revenue': '매출', 'conversions': '전환수', 'CTR': 'CTR'}
    rows = []
    for m in ['spend', 'revenue', 'conversions', 'CTR']:
        r = wow.loc[m]
        chg = r['change_pct']
        cls = 'chg-up' if chg > 5 else 'chg-down' if chg < -5 else ''
        arrow = '▲' if chg > 5 else '▼' if chg < -5 else '→'
        v0 = f"{r[prev]:,.0f}" if m != 'CTR' else f"{r[prev]:.2f}%"
        v1 = f"{r[curr]:,.0f}" if m != 'CTR' else f"{r[curr]:.2f}%"
        rows.append(f"<tr><td>{label[m]}</td><td class='lnum'>{v0}</td><td class='lnum'>{v1}</td>"
                    f"<td class='lnum {cls}'>{arrow} {chg:+.2f}%</td></tr>")
    return (f"<div class='tbl-wrap'><table><thead><tr><th>지표</th><th>{prev}</th><th>{curr}</th>"
            "<th>변화율</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>")


def _benchmark_table(ranked):
    b = ranked['benchmark']
    rows = []
    for _, r in b.iterrows():
        roas = "측정불가" if pd.isna(r['ROAS']) else f"{r['ROAS']:.2f}"
        rb = f"<span class='tag {_BAND_CLASS.get(r['roas_band'], 't-na')}'>{BAND_SHORT[r['roas_band']]}</span>"
        rows.append(f"<tr><td>{escape(r['channel'])}</td>"
                    f"<td class='num'>{r['CTR']:.2f}% <span class='tag {_BAND_CLASS.get(r['ctr_band'],'t-na')}'>{BAND_SHORT[r['ctr_band']]}</span></td>"
                    f"<td class='num'>{r['CVR']:.2f}% <span class='tag {_BAND_CLASS.get(r['cvr_band'],'t-na')}'>{BAND_SHORT[r['cvr_band']]}</span></td>"
                    f"<td class='num'>{roas} {rb}</td><td>{escape(str(r['action']))}</td></tr>")
    return ("<p class='note'>등급은 우리 주차 비교가 아니라 <b>같은 채널 업계 분포(2026 한국 시장 벤치마크)</b> 대비 위치. "
            "종합 등급은 최종 성과 ROAS 기준.</p>"
            "<div class='tbl-wrap'><table><thead><tr><th>채널</th><th>CTR</th><th>CVR</th>"
            "<th>ROAS(종합)</th><th>제안 방향</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>")


def build_insight_html(data):
    t = data['summary']['total']
    m = data['meta']
    stats = "".join([
        _stat(_won(t['total_spend']), "총 지출 (유료 광고비)", "", "c-blue"),
        _stat(_won(t['total_revenue']), "총 매출 (오가닉 포함)",
              f"오가닉 {t['organic_revenue']/t['total_revenue']*100:.2f}%", "c-green"),
        _stat(f"{t['mer']:.2f}%", "전체 마케팅 효율 (MER)", f"유료 순효율 {t['paid_roi']:.2f}%", "c-purple"),
        _stat(f"{t['total_conversions']:,.0f}", "총 전환수", "건", "c-red"),
    ])
    body = [
        '<div class="header"><span class="badge">진단 리포트</span>'
        '<h1>마케팅 성과 인사이트 리포트</h1><div class="header-meta">'
        f'<span>📅 {escape(str(m["date_min"]))} – {escape(str(m["date_max"]))} ({m["n_weeks"]}주)</span>'
        f'<span>📊 원본 {m["n_raw"]}행 · 중복 {m["n_dup"]}·이상치 {m["n_outlier"]}·결측 {m["n_missing"]} 처리</span>'
        '<span>🐍 계산: Python pandas</span></div></div>',
        _usage_guide_html(m),
        _exec_summary_html(data),
        _playbook_html(data),
        f'<div class="stats-row">{stats}</div>',
        f'<div class="section"><div class="section-title">📊 채널별 ROI 순위</div>'
        f'<p class="note">ROI = 매출 / 광고비 × 100. 오가닉은 광고비 0이라 측정 불가.</p>'
        f'{_roi_bars(data["summary"], data["roi"])}{_channel_table(data["summary"])}</div>',
        f'<div class="section"><div class="section-title">💡 핵심 이슈 (비즈니스 임팩트 순)</div>'
        f'{_issue_cards(data["ranked"], data["recency"], data["threshold"])}</div>',
        f'<div class="section"><div class="section-title">📈 전주 대비 변화율 ({data["wow"].columns[0]} → {data["wow"].columns[1]})</div>{_wow_table(data["wow"])}</div>',
        f'<div class="section"><div class="section-title">🎯 채널 평가 (시장 벤치마크 대비)</div>{_benchmark_table(data["ranked"])}</div>',
    ]
    if 'opportunity' in data['ranked']:
        opp = data['ranked']['opportunity'].iloc[0]
        body.append(f'<div class="section"><div class="section-title">🌱 오가닉 성장 잠재력</div>'
                    f'<div class="callout">{escape(str(opp["note"]))}<br><br>'
                    '오가닉은 무료가 아니라 과거 유료광고 낙수효과·SEO 누적의 결과다. 광고비 배정이 아니라 '
                    'SEO·콘텐츠 투자로 키우는 채널이며, 예산 재배분 기획안의 전략 투자처로 연결된다.</div></div>')
    body.append('<div class="foot">계산: Python · 표현: HTML 대시보드 · md 리포트와 동일한 run_pipeline 결과</div>')
    return _page("마케팅 성과 인사이트 리포트", "", "\n".join(body))


def _plan_card(r):
    """재배분안 카드 — 돈의 흐름(source −금액 ➜ target +금액)을 시각화하고 '쉽게 말하면' 한 줄을 앞세운다.

    핵심 액션을 1초에 잡게 하고(플로우+효율 배수), 분석가 양식 4항목은 '자세한 근거'로 강등한다.
    """
    amt = _won(r['amount_won'])
    from_sub = f"ROAS {r['source_roas']:.2f}" if not pd.isna(r['source_roas']) else "저효율 지출"
    if r['kind'] == '광고 증액' and not pd.isna(r['target_roas']):
        to_sub = f"ROAS {r['target_roas']:.2f}"
        ratio_badge = ""
        if not pd.isna(r['source_roas']) and r['source_roas'] > 0:
            ratio_badge = f"<div class='ratio'>{r['target_roas']/r['source_roas']:.1f}배 효율 ↑</div>"
        move = f"{escape(r['source'])} → {escape(r['target'])}, {amt}(테스트 상한)으로 시작해 점진 증액 후 재측정"
        effect = (f"순증 매출 상한 약 <b>{_won(r['expected_won'])}</b> (선형확장 가정). "
                  "실제는 한계수익 체감으로 하회 가능 — 소액 테스트로 검증 후 확대하세요.")
    else:
        to_sub = "장기 자산 · 즉시 ROAS 없음"
        ratio_badge = ""
        move = f"{escape(r['source'])} → {escape(r['target'])}, {amt} 범위 내 SEO·콘텐츠 투자(광고비 직접 배정 아님)"
        effect = "오가닉은 ROAS 측정불가라 원 단위 추정 없이 정성 기대(중장기 유입 성장). 효과 발현에 시차 존재."
    flow = (f"<div class='flow'>"
            f"<div class='flow-node from'><div class='fn-name'>{escape(r['source'])}</div>"
            f"<div class='fn-roas'>{from_sub}</div><div class='fn-amt neg'>−{amt}</div></div>"
            f"<div class='flow-arrow'><div class='fa-amt'>{amt}</div><div class='fa-line'>➜</div>{ratio_badge}</div>"
            f"<div class='flow-node to'><div class='fn-name'>{escape(r['target'])}</div>"
            f"<div class='fn-roas'>{to_sub}</div><div class='fn-amt pos'>+{amt}</div></div></div>")
    lead = f"<div class='plan-lead'><b>핵심 실행</b> · {escape(plan_lead_sentence(r))}</div>"
    return (f"<div class='plan'><div class='plan-h'><span class='pr'>{r['rank']}순위</span>"
            f"예산 재배분<span style='color:#888;font-weight:400;font-size:12px;margin-left:8px'>"
            f"우선순위 점수 {r['priority_score']:,.0f} = 놓친 매출 {_won(r['impact_won'])} × 반복 {r['frequency']}주 (클수록 먼저)</span></div>"
            f"{flow}{lead}"
            "<div class='subhead'>자세한 근거</div>"
            f"<div class='issue-row'><b>무엇이 문제</b> · {escape(r['source'])} 과집행으로 회수 가능한 저효율 지출이 발생했습니다.</div>"
            f"<div class='issue-row'><b>근거 숫자</b> · 회수가능액 {amt} / {escape(r['source'])} 평소 ROAS {r['source_roas']:.2f} / 수혜 근거: {escape(str(r['basis']))}</div>"
            f"<div class='issue-row'><b>실행 방법</b> · {move}</div>"
            f"<div class='issue-row'><b>기대와 주의</b> · {effect}</div></div>")


def build_reallocation_html(data):
    funding, plans = data['funding'], data['plans']
    body = ['<div class="header rx"><span class="badge rx">예산 재배분 기획안</span>'
            '<h1>예산 재배분 기획안</h1><div class="header-meta">'
            '<span>진단(insight_report)의 처방 — 예산으로 무엇을 할지</span>'
            '<span>재원 원칙: 예산 레버(과집행)만 · 데이터 오류 제외</span></div></div>',
            _rx_usage_html(), _checklist_html(data)]

    if funding.empty:
        body.append('<div class="section"><div class="section-title">재원 요약</div>'
                    '<p>이번 기간에는 예산 레버 손실(광고비 과집행)이 없어 재배분 대상 재원이 없습니다. '
                    '현 배분을 유지합니다.</p></div>')
        body.append('<div class="foot">계산: Python · md 리포트와 동일한 run_pipeline 결과</div>')
        return _page("예산 재배분 기획안", "rx", "\n".join(body))

    frows = "".join(f"<tr><td>{escape(f['channel'])}</td><td class='lnum'>{_won(f['recoverable_won'])}</td>"
                    f"<td class='lnum'>{_won(f['impact_won'])}</td><td class='lnum'>{f['frequency']}주</td>"
                    f"<td>{escape(str(f['weeks']))}</td></tr>" for _, f in funding.iterrows())
    body.append('<div class="section"><div class="section-title">💰 재원 요약 (어디서 얼마를 회수하나)</div>'
                "<p class='note'>회수가능액(옮길 돈)은 실지출이라 확실하고, 기회손실(임팩트)은 '평소 효율이었다면' 가정이 섞인 추정치.</p>"
                "<div class='tbl-wrap'><table><thead><tr><th>재원 채널</th><th>회수가능액</th>"
                "<th>기회손실(임팩트)</th><th>빈도</th><th>발생</th></tr></thead><tbody>"
                + frows + "</tbody></table></div></div>")

    if plans.empty:
        body.append('<div class="section"><div class="section-title">재배분안</div>'
                    '<p>재원은 있으나 증액 여력이 검증된 수혜처(벤치마크 우수·오가닉)가 없어 재원을 유보합니다.</p></div>')
    else:
        cards = "".join(_plan_card(r) for _, r in plans.iterrows())
        shared = plans.groupby('source').size().gt(1).any()
        note = ("<div class='callout'><b>재원 공유 주의</b> — 위 안들은 같은 재원(과집행 회수분)을 공유한다. "
                "1순위를 우선 집행하고 성과 확인 후 다음 순위로 순차 배분한다.</div>" if shared else "")
        body.append(f'<div class="section"><div class="section-title">📑 재배분안 (우선순위 순)</div>{cards}{note}</div>')
        crit = "".join(f"<li><b>{escape(title)}</b><br>{escape(body)}</li>" for title, body in PRIORITY_CRITERIA)
        body.append(
            '<div class="section"><div class="section-title">⚖️ 우선순위, 이렇게 정했습니다 (판단 기준)</div>'
            "<p class='note'>아무렇게나가 아니라 데이터 규칙으로 줄을 세웁니다.</p>"
            f'<ol class="crit">{crit}</ol>'
            f"<div class='callout'><b>정직한 고지</b> · {escape(PRIORITY_CAVEAT)}</div></div>")
    body.append('<div class="foot">계산: Python · 표현: HTML 대시보드 · md 리포트와 동일한 run_pipeline 결과</div>')
    return _page("예산 재배분 기획안", "rx", "\n".join(body))


if __name__ == '__main__':
    data_path = sys.argv[1] if len(sys.argv) > 1 else 'data/marketing_performance.csv'
    d = run_pipeline(data_path)   # 한 번 실행해 두 HTML이 같은 결과를 공유
    for out, builder in [(INSIGHT_OUT, build_insight_html), (REALLOC_OUT, build_reallocation_html)]:
        html = builder(d)
        with open(out, 'w') as f:
            f.write(html)
        print(f"생성 완료: {out} ({len(html):,}자)")
