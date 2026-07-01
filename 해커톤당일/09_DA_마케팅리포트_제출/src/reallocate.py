"""예산 재배분 기획안 엔진 — 손실 이슈·채널 효율에서 재배분안을 산출한다.

진단(insight_report)이 '무슨 일이 있었나'라면, 여기는 '예산으로 무엇을 할까'(처방)다.
재원은 lever=='예산'인 손실(과집행 초과지출)만 사용 — 데이터 오류(이상치·결측)는 제외.
옮기는 금액은 recoverable_won(실지출 회수액), 우선순위 크기는 impact_won(놓친 매출·추정치)로 구분한다.
"""
import sys

import pandas as pd

from calculate import (load_and_clean, compute_summary, compute_channel_roi,
                       compute_wow_change, find_revenue_outliers)
from detect_issues import (BENCHMARKS, _band, compute_adaptive_threshold, compute_recency,
                           detect_spike_drop, detect_outliers, detect_missing, evaluate_channels,
                           detect_opportunity, score_and_rank)

DATA = 'data/marketing_performance.csv'
OUT = 'output/budget_reallocation.md'


def _won(x):
    return f"{x:,.0f}원"


def _meta(data_path):
    """리포트 개요용 데이터 메타정보(행수·중복·결측·이상치·기간·주차)를 원본에서 산출."""
    raw_all = pd.read_csv(data_path)
    n_dup = len(raw_all) - len(raw_all.drop_duplicates())
    raw = load_and_clean(data_path, mask_outlier=False)
    n_missing = int(raw[['impressions', 'clicks', 'revenue']].isna().sum().sum())
    weeks = sorted(raw['week'].dropna().unique(), key=lambda w: (len(str(w)), str(w)))
    return {
        'path': data_path, 'n_raw': len(raw_all), 'n_dup': n_dup,
        'n_channels': raw['channel'].nunique(), 'n_missing': n_missing,
        'n_outlier': len(find_revenue_outliers(raw)),
        'date_min': raw['date'].min(), 'date_max': raw['date'].max(),
        'n_weeks': len(weeks), 'weeks': f"{weeks[0]}–{weeks[-1]}",
    }


def run_pipeline(data_path=DATA):
    """정제→집계→이슈→랭킹→재원→수혜→재배분을 한 번 실행해 모든 결과를 dict로 반환한다.

    md 생성기(build_report·build_reallocation)와 html 생성기가 이 하나의 결과를 공유 →
    표현이 달라도 수치는 절대 어긋나지 않는다('데이터 하나, 표현 둘'). 계산 로직은 전부 재사용.
    """
    df = load_and_clean(data_path)
    raw = load_and_clean(data_path, mask_outlier=False)
    s = compute_summary(df)
    ranked = score_and_rank(
        detect_spike_drop(df) + detect_outliers(raw) + detect_missing(raw)
        + evaluate_channels(s['by_channel'])
        + detect_opportunity(s['by_channel'], s['total']['total_revenue']))
    funding = compute_funding(ranked)
    targets = select_targets(s, ranked, exclude=list(funding['channel']))
    plans = build_plans(funding, targets, s)
    return {
        'meta': _meta(data_path), 'summary': s, 'roi': compute_channel_roi(df),
        'wow': compute_wow_change(df), 'ranked': ranked, 'threshold': compute_adaptive_threshold(df),
        'recency': compute_recency(df),
        'funding': funding, 'targets': targets, 'plans': plans,
    }


def compute_funding(ranked):
    """재배분 재원(어디서 얼마를 뺄 수 있나)을 채널별로 집계한다.

    입력: score_and_rank 결과 dict (ranked['loss'] = 손실 이슈 DataFrame).
    처리: 손실 중 lever=='예산' 행만 필터 → 과집행 초과지출만 재원으로 인정.
          이상치·결측(데이터·트래킹 레버)은 여기서 자동 배제된다.
    출력: DataFrame [channel, recoverable_won, impact_won, frequency, weeks], 회수액 내림차순.
          재원이 없으면 빈 DataFrame(같은 컬럼) 반환 — 새 CSV에서 과집행이 없어도 안전.
    """
    cols = ['channel', 'recoverable_won', 'impact_won', 'frequency', 'weeks']
    loss = ranked.get('loss')
    if loss is None or loss.empty:
        return pd.DataFrame(columns=cols)
    src = loss[(loss['lever'] == '예산') & (loss['recoverable_won'] > 0)]
    if src.empty:
        return pd.DataFrame(columns=cols)
    funding = src.groupby('channel').agg(
        recoverable_won=('recoverable_won', 'sum'),
        impact_won=('impact_won', 'sum'),
        frequency=('frequency', 'sum'),
        weeks=('weeks', lambda s: ','.join(s)),
    ).reset_index().sort_values('recoverable_won', ascending=False)
    return funding[cols]


def select_targets(summary, ranked, exclude=()):
    """재원을 넣을 수혜처 후보를 선정한다 (어디에 넣나).

    입력: compute_summary 결과(채널별 ROAS), score_and_rank 결과(오가닉 기회), 제외 채널(재원 채널).
    두 유형의 후보를 낸다:
      1) 광고 증액 — 벤치마크 ROAS 등급이 '우수'(시장 상위25% 이상)인 유료 채널. 절대 ROI가 아니라
         자기 시장 대비 우수 = '아직 더 태울 여지 검증'. 재원 채널 자신은 제외(과집행처에 재투입 모순).
      2) 전략 투자 — 오가닉(detect_opportunity). 광고비 배정이 아니라 SEO·콘텐츠 투자처로 제시.
    출력: DataFrame [channel, kind, roas, grade, evidence]. 후보 없으면 빈 DataFrame(같은 컬럼).
    """
    cols = ['channel', 'kind', 'roas', 'grade', 'evidence']
    g = summary['by_channel']
    rows = []
    for ch in g.index:
        if ch in exclude:
            continue
        bench = BENCHMARKS.get(ch, {})
        roas = g.loc[ch, 'ROAS']
        if pd.isna(roas) or not bench.get('ROAS'):
            continue  # 오가닉·벤치마크 없는 채널은 광고 증액 후보에서 제외
        band = _band(roas, bench['ROAS'])
        if '우수' in band:
            rows.append({'channel': ch, 'kind': '광고 증액', 'roas': roas, 'grade': band,
                         'evidence': f'ROAS {roas:.2f} — 시장 벤치마크 상위25% 이상(증액 여력 검증)'})
    opp = ranked.get('opportunity')
    if opp is not None and not opp.empty:
        for _, o in opp.iterrows():
            if o['channel'] in exclude:
                continue
            rows.append({'channel': o['channel'], 'kind': '전략 투자(SEO·콘텐츠)', 'roas': float('nan'),
                         'grade': '측정불가(오가닉)', 'evidence': o['note']})
    return pd.DataFrame(rows, columns=cols)


# 수혜처 유형별 즉효성 순위 (우선순위 2차 정렬용). 낮을수록 우선 — 광고 증액은 즉시 ROAS 실현, 전략 투자는 지연.
_KIND_RANK = {'광고 증액': 0, '전략 투자(SEO·콘텐츠)': 1}


def build_plans(funding, targets, summary):
    """재원 × 수혜처를 매칭해 우선순위가 매겨진 재배분안 목록을 만든다.

    입력: compute_funding·select_targets 결과, compute_summary(재원 채널의 평소 ROAS 조회용).
    처리:
      - 각 재원(과집행 채널)의 회수액을 각 수혜처로 보내는 안을 생성. 옮기는 금액 = recoverable(회수 실지출·테스트 상한).
      - 광고 증액: 기대효과를 원(₩)으로 추정 — 순증분 = 회수액 × (수혜 ROAS − 재원채널 평소 ROAS)(선형확장 상한).
      - 전략 투자(오가닉): ROAS 측정불가라 원 추정 없이 정성 기대효과.
      - 우선순위: 1차 impact_won×frequency(재원의 심각도·반복성) 내림차순, 동점은 수혜처 즉효성(_KIND_RANK) 오름차순.
    출력: DataFrame(우선순위 rank 부여). 재원·수혜처 중 하나라도 없으면 빈 DataFrame(같은 컬럼).
    복수 안이 같은 재원을 공유하므로(돈은 한 번만 씀) rank 1을 우선 집행, 성과 확인 후 후속 안으로 순차 배분한다.
    """
    cols = ['rank', 'source', 'target', 'kind', 'amount_won', 'source_roas', 'target_roas',
            'expected_won', 'expected_note', 'priority_score', 'impact_won', 'frequency', 'basis']
    g = summary['by_channel']
    if funding.empty or targets.empty:
        return pd.DataFrame(columns=cols)

    rows = []
    for _, f in funding.iterrows():
        src = f['channel']
        src_roas = g.loc[src, 'ROAS'] if src in g.index else float('nan')
        amount = f['recoverable_won']
        score = f['impact_won'] * f['frequency']
        for _, t in targets.iterrows():
            tgt_roas = t['roas']
            if t['kind'] == '광고 증액' and not pd.isna(tgt_roas) and not pd.isna(src_roas):
                expected = amount * (tgt_roas - src_roas)   # 재원채널 대신 수혜채널에 썼을 때 순증 매출(상한)
                note = (f"회수액을 평소 ROAS {src_roas:.2f}인 {src} 대신 {tgt_roas:.2f}인 {t['channel']}에 재투입 시 "
                        f"매출 순증 상한 (선형확장 가정)")
            else:
                expected = float('nan')                     # 오가닉은 원 추정 안 함(정성)
                note = f"{t['channel']} {t['evidence']} — SEO·콘텐츠 투자로 중장기 유입 성장(즉시 ROAS 미정)"
            rows.append({'source': src, 'target': t['channel'], 'kind': t['kind'], 'amount_won': amount,
                         'source_roas': src_roas, 'target_roas': tgt_roas, 'expected_won': expected,
                         'expected_note': note, 'priority_score': score,
                         'impact_won': f['impact_won'], 'frequency': f['frequency'], 'basis': t['evidence']})

    out = pd.DataFrame(rows)
    out['_kind_rank'] = out['kind'].map(_KIND_RANK).fillna(9)
    out = out.sort_values(['priority_score', '_kind_rank'], ascending=[False, True]).reset_index(drop=True)
    out['rank'] = out.index + 1
    return out[cols]


def plan_lead_sentence(r):
    """재배분안 1건을 '쉽게 말하면' 한 문장으로 — md·html 공유. 분석가 양식 대신 실무자 언어.

    ROAS를 '광고비 1원당 X원 회수'로 풀고, 효율 배수·기대 매출을 넣어 '무엇을·왜' 즉시 이해되게 한다.
    광고 증액이면 효율 비교 문장, 전략 투자(오가닉)면 '오래 남는 자산' 문장으로 분기한다.
    """
    if r['kind'] == '광고 증액' and not pd.isna(r['source_roas']) and r['source_roas'] > 0 and not pd.isna(r['target_roas']):
        ratio = r['target_roas'] / r['source_roas']
        exp = f" 같은 예산으로 매출 최대 {_won(r['expected_won'])}을 추가로 기대할 수 있습니다." if not pd.isna(r['expected_won']) else ""
        return (f"저효율 채널 {r['source']}(ROAS {r['source_roas']:.1f})에서 회수한 {_won(r['amount_won'])}을, "
                f"효율이 {ratio:.1f}배 높은 {r['target']}(ROAS {r['target_roas']:.1f})로 이동합니다.{exp}")
    return (f"{r['source']}에서 회수한 {_won(r['amount_won'])}을 {r['target']} SEO·콘텐츠에 투자합니다. "
            f"즉시 매출로는 잡히지 않지만, 광고 중단 시 사라지는 유료 유입과 달리 지속적으로 남는 자산이 됩니다.")


def _plan_block(r):
    """재배분안 1건을 '쉽게 말하면' 요약 + 4항목 근거(문제·근거·실행·기대) 양식으로 서술한다."""
    if r['kind'] == '광고 증액':
        move = f"**{r['source']} → {r['target']}**, {_won(r['amount_won'])}(테스트 상한), 점진 증액 후 재측정"
        effect = (f"순증 매출 상한 약 {_won(r['expected_won'])} — {r['expected_note']}.\n"
                  f"  - 한계: 선형확장 가정 상한이라 한계수익 체감으로 실제는 하회 가능. 소액 테스트로 검증 후 확대.")
    else:
        move = f"**{r['source']} → {r['target']}**, {_won(r['amount_won'])} 범위 내 SEO·콘텐츠 투자(광고비 직접 배정 아님)"
        effect = (f"{r['expected_note']}.\n"
                  f"  - 한계: 오가닉은 ROAS 측정불가라 원 단위 기대효과를 추정하지 않음(정성). 효과 발현에 시차 존재.")
    return "\n".join([
        f"### [재배분안 #{r['rank']}] 우선순위 {r['rank']}순위  "
        f"(임팩트 {_won(r['impact_won'])} × 빈도 {r['frequency']}주 = 점수 {r['priority_score']:,.0f})\n",
        f"> **핵심 실행**: {plan_lead_sentence(r)}\n",
        f"1. **문제 정의** — {r['source']} 과집행: 회수 가능한 저효율 지출 발생(insight_report 손실 이슈 참조).",
        f"2. **근거 데이터** — 회수가능액 {_won(r['amount_won'])} / 재원채널 평소 ROAS "
        f"{r['source_roas']:.2f} / 수혜채널 근거: {r['basis']}",
        f"3. **재배분안** — {move}",
        f"4. **기대효과·한계** — {effect}\n",
    ])


# 우선순위 판단 기준 — 마케팅 실무자 눈높이의 (제목, 설명) 쌍. md·html이 공유해 문구가 어긋나지 않는다.
PRIORITY_CRITERIA = [
    ("손실 규모 × 발생 빈도로 우선순위를 매깁니다",
     "놓친 매출(손실 규모)만으로 줄을 세우면 일회성 대형 이슈와 매주 반복되는 소액 누수가 뒤섞입니다. "
     "발생 빈도를 곱해, 구조적으로 반복되는 예산 누수를 상위로 끌어올립니다 — 재배분으로 가장 크게 회수할 수 있는 지점입니다."),
    ("점수가 같으면 전환이 즉시 발생하는 채널을 우선합니다",
     "같은 재원을 나눠 쓰는 안들은 손실 규모·빈도가 같아 우선순위 점수가 동일해집니다. "
     "이때는 집행 즉시 전환·매출로 이어지는 광고 증액을, 효과가 수개월 뒤 나타나는 SEO·콘텐츠 투자보다 먼저 집행합니다."),
    ("재배분액은 추정 손실이 아니라 실제 회수 가능한 예산으로 산정합니다",
     "'놓친 매출'은 추정치이고, '과집행된 광고비'는 실제로 회수 가능한 확정 금액입니다. "
     "추정치를 재배분액으로 잡으면 실제로 집행할 수 없는 규모의 계획이 되므로, 옮기는 금액은 회수 가능액만 사용합니다."),
    ("증액처는 절대 ROI 1위가 아니라 시장 대비 증액 여력이 검증된 채널로 선정합니다",
     "절대 ROI가 가장 높은 채널은 이미 예산이 포화 상태일 수 있어, 추가 투입 시 한계 효율이 빠르게 떨어질 수 있습니다. "
     "그래서 동종 업계 벤치마크 상위권(우수 등급)이면서 아직 증액 여력이 남은 채널을 우선 증액 대상으로 삼습니다."),
]

PRIORITY_CAVEAT = ("위 기대 매출은 현재 효율이 선형으로 유지된다는 가정 하의 상한값으로, 실제 성과는 이보다 낮을 수 있습니다. "
                   "오가닉 기여는 ROAS 측정이 불가해 정성적 방향으로만 제시합니다. "
                   "모든 안은 소액 테스트 → 성과 재측정 → 확대의 단계적 검증을 전제로 합니다.")


_RX_USAGE = (
    "## 이 기획안, 읽고 실행하는 법\n\n"
    "> 이 문서가 답하는 질문: **\"회수 가능한 예산을 어디로 옮겨야 매출이 늘까?\"** 처음 보는 분은 여기부터 읽으세요.\n\n"
    "- **1단계** — §1 재원 요약에서 **회수가능액**(확실히 뺄 수 있는 돈)을 확인합니다. '임팩트'는 우선순위 참고용 추정치입니다.\n"
    "- **2단계** — §2 재배분안을 **1순위부터** 봅니다. 각 안의 [어디→어디, 얼마]와 [기대효과·한계]를 확인합니다.\n"
    "- **3단계** — 1순위를 **소액 테스트로 집행** → 2주 후 ROAS 재측정 → 개선되면 확대, 아니면 다음 순위로 전환합니다.\n"
    "- **주의** — 여러 안이 같은 재원을 공유하면 **돈은 한 번만** 씁니다. 동시 집행하지 마세요.\n"
)


def build_action_checklist(d):
    """'지금 당장 할 일' 체크리스트 항목(문자열 리스트)을 데이터에서 생성 — md·html이 공유.

    입력: run_pipeline 결과 dict(funding·plans 사용). 출력: 실행 단계 문자열 리스트.
    1순위 재배분안에서 [과집행 차단 → 수혜처 테스트 증액 → 재측정] 3단계를 뽑는다.
    재원이 없거나 수혜처가 없으면 그에 맞는 유지/유보 메시지로 분기해 항상 문장이 성립한다.
    """
    funding, plans = d['funding'], d['plans']
    if funding.empty:
        return ["과집행 등 회수 가능한 재원이 없습니다 — 예산 이동 없이 현 배분을 유지하고 채널 효율 개선을 우선하세요."]
    if plans.empty:
        f = funding.iloc[0]
        return [f"{f['channel']} 예산 한도를 설정해 과집행을 차단하세요 (회수 가능 {_won(f['recoverable_won'])}).",
                "증액 여력이 검증된 수혜처가 없어 회수분은 유보하고, 채널 효율 개선 후 재검토하세요."]
    p = plans.iloc[0]
    steps = [f"{p['source']} 예산 한도를 설정해 과집행을 차단하세요 (회수 가능 {_won(p['amount_won'])})."]
    if p['kind'] == '광고 증액':
        exp = f", 순증 매출 상한 약 {_won(p['expected_won'])}" if not pd.isna(p['expected_won']) else ""
        steps.append(f"회수액을 {p['target']}에 소액 테스트로 증액하세요 (근거: 시장 벤치마크 우수 등급{exp}).")
        steps.append(f"2주 후 {p['target']} ROAS를 재측정하세요 — 개선되면 확대, 아니면 다음 순위 안으로 전환.")
    else:
        steps.append(f"회수액 범위 내에서 {p['target']} SEO·콘텐츠에 투자하세요 (즉시 ROAS가 아닌 중장기 유입 목적).")
        steps.append(f"{p['target']} 유입·전환 추이를 월 단위로 관찰하세요 — 효과 발현에 시차가 있어 조급한 판단은 금물.")
    return steps


def _checklist_md(d):
    lines = ["## ✅ 지금 당장 할 일 (이번 데이터 기준)\n",
             "> 아래 순서대로 실행하면 됩니다. 수치는 이번 성과 데이터에서 자동 산출된 값이라 새 데이터를 넣으면 자동 갱신됩니다.\n"]
    for it in build_action_checklist(d):
        lines.append(f"- [ ] {it}")
    return "\n".join(lines) + "\n"


def build_reallocation(data_path=DATA, data=None):
    """예산 재배분 기획안 md를 생성한다 (진단 리포트의 '처방' 짝).

    data(run_pipeline 결과)를 받으면 재사용하고, 없으면 직접 실행한다. md·html 생성기가
    같은 결과를 공유하도록 하기 위함. 재원(과집행)이 없으면 그 사실을 명시하고 안전하게 종료한다.
    """
    d = data or run_pipeline(data_path)
    s, funding, targets, plans = d['summary'], d['funding'], d['targets'], d['plans']

    out = ["# 예산 재배분 기획안\n",
           _RX_USAGE,
           _checklist_md(d),
           "## 0. 개요\n",
           "- 목적: insight_report(진단, '무슨 일이 있었나')의 **처방** — 예산으로 무엇을 할지 제안.",
           "- **재원 원칙**: 조치 레버가 '예산'인 손실(광고비 과집행의 초과지출)만 재원으로 삼는다. "
           "이상치·결측(데이터·트래킹 레버)은 데이터 수집·기록 오류라 예산 재배분으로 해결되지 않으므로 제외.",
           "- **옮기는 금액 = 회수가능액**(실제 낭비한 광고비, 확실). **우선순위 크기 = 임팩트**(놓친 매출, 선형확장 추정).\n"]

    if funding.empty:
        out.append("## 1. 재원 요약\n\n이번 기간에는 예산 레버 손실(광고비 과집행)이 탐지되지 않아 "
                   "재배분 대상 재원이 없습니다. 예산 이동 없이 현 배분을 유지합니다.\n")
        return _finish(out)

    out.append("## 1. 재원 요약 (어디서 얼마를 회수할 수 있나)\n")
    out += ["| 재원 채널 | 회수가능액 | 기회손실(임팩트) | 빈도 | 발생 |",
            "|-----------|-----------|-----------------|------|------|"]
    for _, f in funding.iterrows():
        out.append(f"| {f['channel']} | {_won(f['recoverable_won'])} | {_won(f['impact_won'])} | "
                   f"{f['frequency']}주 | {f['weeks']} |")
    out.append("\n> 회수가능액(옮길 돈)은 실지출이라 확실하고, 기회손실(임팩트)은 '평소 효율이었다면' 가정이 섞인 추정치다.\n")

    if plans.empty:
        out.append("## 2. 재배분안\n\n재원은 있으나 증액 여력이 검증된 수혜처(벤치마크 우수 채널·오가닉 성장)가 "
                   "없어 구체적 재배분안을 제시하지 않습니다. 재원은 유보 후 채널 효율 개선을 우선합니다.\n")
        return _finish(out)

    out.append("## 2. 재배분안 (우선순위 순)\n")
    for _, r in plans.iterrows():
        out.append(_plan_block(r))

    shared = plans.groupby('source').size().gt(1).any()
    if shared:
        out.append("> **재원 공유 주의**: 위 안들은 같은 재원(과집행 회수분)을 공유한다 — 돈은 한 번만 쓴다. "
                   "1순위를 우선 집행하고, 성과를 확인한 뒤 잔여·후속분을 다음 순위로 순차 배분한다.\n")

    out += ["## 3. 우선순위, 이렇게 정했습니다 (판단 기준)\n",
            "재배분안을 어떤 순서로 실행할지는 아래 기준으로 정합니다. 아무렇게나가 아니라 데이터 규칙으로 줄을 세웁니다.\n"]
    for i, (title, body) in enumerate(PRIORITY_CRITERIA, 1):
        out.append(f"{i}. **{title}** — {body}")
    out.append(f"\n**한계(정직한 고지)**: {PRIORITY_CAVEAT}\n")
    return _finish(out)


def _finish(out):
    out += ["## 4. 방법론·재현성\n",
            "> 재원·수혜·우선순위는 전부 Python(calculate.py·detect_issues.py·reallocate.py)이 계산하고, "
            "해석·문구는 규칙 기반 템플릿으로 채운다. 새 성과 CSV를 넣으면 동일 구조로 자동 재생성된다 "
            "(`python3 src/reallocate.py [입력CSV] [출력MD]`).\n"]
    return "\n".join(out).replace('~', '–')


if __name__ == '__main__':
    data_path = sys.argv[1] if len(sys.argv) > 1 else DATA
    out_path = sys.argv[2] if len(sys.argv) > 2 else OUT
    report = build_reallocation(data_path)
    with open(out_path, 'w') as fp:
        fp.write(report)
    print(f"생성 완료: {out_path} ({len(report):,}자)")
