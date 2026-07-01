# Skill: /insight — 인사이트 도출

/analyze 완료 후 실행. 채널별 성과 패턴을 분석하고 이슈 3가지 기준을 세웁니다.
⚠️ 계산은 Python, **해석은 여기서 직접** 합니다.

---

## Step 1: 채널별 ROI 비교 (Python 계산)

```python
import pandas as pd

df = pd.read_csv('data/marketing_performance.csv').drop_duplicates()
for c in ['impressions','clicks','spend','conversions','revenue']:
    df[c] = pd.to_numeric(df[c], errors='coerce')

# 이메일 매출 이상치 제외 (2026-04-26)
df = df[~((df['channel']=='이메일') & (df['date']=='2026-04-26'))]

g = df.groupby('channel').agg(
    spend=('spend','sum'), revenue=('revenue','sum'),
    conversions=('conversions','sum'),
    impressions=('impressions','sum'), clicks=('clicks','sum')
)
g['ROI'] = (g['revenue']/g['spend']*100).where(g['spend']>0)   # 오가닉(0)은 NaN
g['ROAS'] = (g['revenue']/g['spend']).where(g['spend']>0)
g['CTR'] = g['clicks']/g['impressions']*100
g['CVR'] = g['conversions']/g['clicks']*100
print(g.sort_values('ROI', ascending=False).round(2).to_string())
```

### 해석 방법
- ROI 높은 채널 = 광고비 대비 매출 효율 높음 → 예산 확대 후보
- ROI 낮은 채널 = 효율 낮음 → 원인(소재·타겟·이상치) 점검 후 축소 검토
- 오가닉은 광고비 0 → ROI 무한대 = **측정 불가**. 효율 순위에서 별도 표기 (전환·CVR로만 평가)
- 산출한 CTR·CVR·ROAS를 context/industry-news.md 벤치마크와 비교해 "평균 대비 우수/미흡" 판단

---

## Step 2: 이슈 3가지 탐지 기준

### 정량 기준
- **전주 대비 ±50% 이상 변화** = 이슈
- **이상치**: 매출/전환 대비 비현실적, 광고비 평소의 수 배
- **결측**: 데이터 신뢰성 이슈

```python
# 주차별 채널별 광고비·매출
wk = df.groupby(['channel','week']).agg(spend=('spend','sum'), revenue=('revenue','sum'))
wk['ROI'] = (wk['revenue']/wk['spend']*100).where(wk['spend']>0)
print(wk.round(0).to_string())
```

### 이슈 우선순위 (이 데이터 기준 권장)
1. **메타광고 W5 광고비 급등 → ROI 급락**: 광고비 평소 ~125만 → ~444만(약 3.5배), ROI 약 306%→124%. 예산 과집행 의심.
2. **카카오광고 W4 광고비 급락**: 평소 ~88만 → ~52만(약 41% 감소). 집행 누락/중단 가능성.
3. **데이터 품질 이슈**: 이메일 매출 이상치 1건(입력 오류 의심) + 완전 중복 1행 + 결측 3건 → 집계 신뢰성. (또는 오가닉이 광고비 0인데 전환·매출 최상위인 점을 전략 이슈로 선택 가능)

> 3가지 중 무엇을 고를지는 본인 판단. **선정 근거를 decisions.md에 기록.**

---

## Step 3: 전주 대비 변화율 (최근 2주 W7 → W8)

```python
def wsum(w, col): 
    s = df[df['week']==w]
    return s[col].sum()

def ctr(w):
    s = df[df['week']==w]
    return s['clicks'].sum()/s['impressions'].sum()*100

def chg(a,b): return (b-a)/a*100 if a else float('nan')

print("지표  | W7 | W8 | 변화율%")
for col,label in [('spend','지출'),('revenue','매출'),('conversions','전환수')]:
    a,b = wsum('W7',col), wsum('W8',col)
    print(f"{label}: {a:,.0f} -> {b:,.0f} ({chg(a,b):+.1f}%)")
print(f"CTR: {ctr('W7'):.2f}% -> {ctr('W8'):.2f}% ({chg(ctr('W7'),ctr('W8')):+.1f}%)")
```

---

## Step 4: 비즈니스 의미 해석

| 이슈 유형 | 수치 예시 | 비즈니스 의미 | 권장 조치 |
|---------|---------|------------|---------|
| 광고비 급증→ROI 급락 | 메타 W5 444만, ROI 124% | 예산 과집행, 효율 악화 | 일 한도 설정, 소재·타겟 점검 |
| 광고비 급락 | 카카오 W4 52만 | 집행 누락/중단 가능 | 집행 담당자 확인 |
| 매출 이상치 | 이메일 1일 3,200만 | 입력 오류·중복 집계 | 원본 재확인 후 제외/보정 |
| 오가닉 무비용 고전환 | 광고비 0, 전환 최상위 | 콘텐츠·SEO 자산 가치 | 오가닉 강화 투자 검토 |

---

## 완료 기준
- [ ] 채널별 ROI 순위표 완성 (5채널, 오가닉 "측정 불가" 표기)
- [ ] 이슈 3가지 선정 완료 (각 근거 수치 포함)
- [ ] 전주 대비 변화율 계산 완료 (W7→W8: 지출·매출·전환·CTR)
- [ ] 각 이슈에 비즈니스 의미·권장 조치 작성

→ 완료 후 /generate 실행
