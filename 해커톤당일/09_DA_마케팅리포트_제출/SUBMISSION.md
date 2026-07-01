# 제출물 안내 — 마케팅 성과 리포트 자동화 (목표: Challenge 160점)

이 폴더 하나로 Basic·Standard·Challenge 산출물이 모두 들어 있습니다. 아래 순서로 보시면 됩니다.

## 1. 실행 (명령 한 줄씩)

```bash
python3 src/generate_report.py [입력CSV] [출력MD]   # 진단 리포트(md)  — 기본: insight_report.md
python3 src/reallocate.py       [입력CSV] [출력MD]   # 예산 재배분 기획안(md)
python3 src/generate_html.py    [입력CSV]            # 위 둘의 HTML 대시보드 2개
python3 tests/verify_reproducibility.py             # 재현성 자동 검증(원본+변형 4종)
```
인자 생략 시 `data/marketing_performance.csv`를 읽어 `output/`에 생성합니다. 새 성과 CSV를 넣으면 동일 품질로 자동 재생성됩니다(주차·채널·기간 달라도 적응).

## 2. 산출물 ↔ 채점 항목 매핑

### 🟢 Basic (100)
| 채점 항목 | 산출물 위치 |
|-----------|-------------|
| 핵심 수치 요약(총지출·총매출·전체ROI·총전환) | [output/insight_report.md](output/insight_report.md) §핵심 수치 요약 |
| 채널별 ROI 순위 + 해석 | 동 §채널별 ROI 순위 |
| 이슈 3가지(해석·근거·조치) | 동 §이슈 (비즈니스 임팩트 순) |
| 전주 대비 변화율(W7→W8) | 동 §전주 대비 변화율 |

### 🟡 Standard (+30)
| 채점 항목 | 산출물 위치 |
|-----------|-------------|
| 파이프라인 재현성 | [src/](src/) (calculate·detect_issues·reallocate·generate_report) + [.claude/skills/generate.md](.claude/skills/generate.md) + [tests/](tests/) 자동 검증 |
| 주간 리포트 설계 근거 | [docs/REPORT_DESIGN.md](docs/REPORT_DESIGN.md) (경영진·마케팅팀 관점) |

### 🔴 Challenge (+30)
| 채점 항목 | 산출물 위치 |
|-----------|-------------|
| 예산 재배분 기획안 실효성 | [output/budget_reallocation.md](output/budget_reallocation.md) §재원 요약·재배분안 |
| 양식·우선순위 설계 | 동 §우선순위 판단 기준(설계 근거) + [decisions.md](decisions.md) Step 18·20 |

## 3. 계산·해석 분리 (과제 핵심 원칙)

합계·ROI·변화율·이슈 임팩트·재배분은 **전부 Python**(`src/`)이 계산합니다. Claude는 계산 완료 수치로 **해석·서술만** 담당합니다. 모든 표현물(md·html)은 `reallocate.run_pipeline()` **하나의 계산 결과**를 공유하므로 수치가 서로 어긋나지 않습니다.

## 4. HTML 대시보드에 대하여 (제약 준수 근거)

`output/insight_report.html`·`budget_reallocation.html`은 md 리포트의 **정적 렌더링**입니다. 과제 제외 범위와 충돌하지 않음을 밝힙니다:
- **이미지 차트 아님** — Matplotlib/Plotly 그래프 이미지 없이 CSS 요소로만 표시.
- **인터랙티브 웹앱/Streamlit 아님** — 자바스크립트 실행·서버 없이 파일 하나로 열리는 정적 문서.
- **계산은 Python** — HTML은 브라우저에서 계산하지 않고, Python이 계산한 값을 그대로 렌더링(md와 동일 수치).

즉 텍스트 리포트(md)가 정본이고, HTML은 같은 내용을 보기 좋게 옮긴 보조 표현입니다.

## 5. 재현성 검증

[tests/verify_reproducibility.py](tests/verify_reproducibility.py)가 원본 + 변형 3종(주차·채널 축소, 오가닉 제거, 주차 재라벨)에서 md·html 4개 산출물이 크래시 없이 데이터에 맞게 생성되는지 자동 점검합니다. 변형 데이터에서 변화율 주차·오가닉 섹션·재배분안 개수가 자동 조정됩니다.

## 6. 의사결정·작업 기록

- [decisions.md](decisions.md) — 정제·이상치·이슈·벤치마크·재배분 등 모든 판단과 근거(Step 1~20)
- [Worklog.md](Worklog.md) — 작업 이력(W-001~006)
- [Troubleshootinglog.md](Troubleshootinglog.md) — 버그·수정 기록(T-001~003)
