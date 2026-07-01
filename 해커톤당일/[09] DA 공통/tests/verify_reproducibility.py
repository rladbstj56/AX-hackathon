"""재현성 검증: 원본 + 변형 픽스처 전부에 파이프라인을 돌려 크래시 없이
동일 구조 리포트가 나오는지 자동 점검한다.

각 CSV마다: (1) 진단 리포트 생성 성공·필수 섹션·변화율 라벨·기회 섹션, (2) 예산 재배분 기획안
생성 성공·필수 섹션을 점검한다. 재배분은 재원(과집행)·수혜처(오가닉) 유무가 데이터마다 달라
(B 오가닉없음·A 과집행없음 등) 크래시 없이 조건부로 대응하는지가 핵심. 하나라도 실패하면 exit 1.
"""
import os
import re
import sys

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, '..', 'src'))
from reallocate import run_pipeline, build_reallocation  # noqa: E402
from generate_report import build_report  # noqa: E402
from generate_html import build_insight_html, build_reallocation_html  # noqa: E402

FIX = os.path.join(HERE, 'fixtures')
CASES = [
    ('원본(8주·5채널)', os.path.join(HERE, '..', 'data', 'marketing_performance.csv')),
    ('A 짧은·소채널(4주·3채널)', os.path.join(FIX, 'variant_a_short.csv')),
    ('B 오가닉 없음', os.path.join(FIX, 'variant_b_noorganic.csv')),
    ('C 주차 재라벨(W5-W12)', os.path.join(FIX, 'variant_c_relabel.csv')),
]
REQUIRED = ['데이터 개요', '핵심 수치', 'ROI', '이슈', '변화율']


# 재원 유무와 무관하게 항상 있어야 하는 섹션. '우선순위 판단 기준'은 재배분안이 있을 때만(아래 조건부).
REALLOC_REQUIRED = ['예산 재배분 기획안', '재원 요약', '방법론']


def check(label, path):
    d = run_pipeline(path)          # 한 번 실행해 md·html이 같은 결과 공유(예외 시 크래시=실패)
    report = build_report(data=d)
    missing = [s for s in REQUIRED if s not in report]
    wow = re.search(r'(W\d+)\s*→\s*(W\d+)', report)
    wow_txt = f'{wow.group(1)} → {wow.group(2)}' if wow else '없음'
    has_opp = '오가닉 성장' in report
    tilde = '~' in report  # 취소선 유발 물결표가 남아있으면 안 됨(T-001)

    insight_html = build_insight_html(d)      # HTML 생성 크래시 체크
    realloc_html = build_reallocation_html(d)
    html_ok = len(insight_html) > 500 and len(realloc_html) > 300 and '~' not in insight_html

    realloc = build_reallocation(data=d)  # 예외 나면 재배분 재현성 실패
    r_missing = [s for s in REALLOC_REQUIRED if s not in realloc]
    r_tilde = '~' in realloc
    n_plans = realloc.count('[재배분안 #')
    if '재배분 대상 재원이 없습니다' in realloc:
        r_state = '재원 없음(유지 권고)'
    elif n_plans == 0:
        r_state = '재원 있으나 수혜처 없음'
    else:
        r_state = f'재배분안 {n_plans}건'
        if '판단 기준' not in realloc:  # 재배분안이 있으면 우선순위 설계 근거 섹션 필수
            r_missing.append('우선순위 판단 기준')

    ok = not missing and not tilde and not r_missing and not r_tilde and html_ok
    print(f'[{"OK " if ok else "FAIL"}] {label}')
    print(f'       진단: 길이 {len(report):,}자 | 변화율 {wow_txt} | 기회섹션 {"있음" if has_opp else "없음"} | 물결표 {"있음(문제)" if tilde else "없음"}')
    print(f'       재배분: 길이 {len(realloc):,}자 | {r_state} | 물결표 {"있음(문제)" if r_tilde else "없음"}')
    print(f'       HTML: 진단 {len(insight_html):,}자·재배분 {len(realloc_html):,}자 | {"OK" if html_ok else "문제"}')
    if missing:
        print(f'       진단 누락 섹션: {missing}')
    if r_missing:
        print(f'       재배분 누락 섹션: {r_missing}')
    return ok


def main():
    results = [check(label, path) for label, path in CASES]
    print('\n' + ('전체 통과' if all(results) else '실패 케이스 있음'))
    sys.exit(0 if all(results) else 1)


if __name__ == '__main__':
    main()
