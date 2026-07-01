# Skill: /analyze — 데이터 파악

마케팅 성과 raw CSV를 로드하고, 분석 전 데이터 품질 문제를 전부 파악합니다.
데이터: `data/marketing_performance.csv` (280행 = 8주 W1~W8 × 5채널 × 7일).
컬럼: date, channel, impressions, clicks, spend, conversions, revenue, week — **모두 raw 지표** (CTR/CVR/ROAS 없음, 직접 계산).

---

## Step 0: 로드 & 형태 확인

```python
import pandas as pd
df = pd.read_csv('data/marketing_performance.csv')
print("행수:", len(df))                 # 280이어야 정상
print("주차:", sorted(df['week'].unique()))   # W1~W8
print("채널:", df['channel'].unique())        # 네이버광고/메타광고/카카오광고/오가닉/이메일
print(df.head())
```

---

## Step 1: 숫자형 변환

```python
num_cols = ['impressions','clicks','spend','conversions','revenue']
for c in num_cols:
    df[c] = pd.to_numeric(df[c], errors='coerce')   # 빈 셀/문자는 NaN
print(df[num_cols].dtypes)
```

---

## Step 2: 결측치 확인 (3건 존재)

```python
print("컬럼별 결측 개수:")
print(df[num_cols].isna().sum())
print("\n결측 포함 행:")
print(df[df[num_cols].isna().any(axis=1)][['date','channel','week'] + num_cols])
```
→ 처리: 결측 행은 합산 시 자동 제외(groupby는 NaN을 빼고 더함). 0으로 채우지 말고 리포트에 "데이터 없음" 명시.

---

## Step 3: 완전 중복 행 탐지 (1쌍 존재)

```python
dups = df[df.duplicated(keep=False)]
print("완전 중복 행:")
print(dups.sort_values(list(df.columns)))
print("\n중복 제거 전:", len(df), "→ 제거 후:", len(df.drop_duplicates()))
df = df.drop_duplicates()   # 집계 전 반드시 제거 (안 하면 매출·전환 부풀려짐)
```

---

## Step 4: 이상치 탐지

### (a) 매출 이상치 — 전환수 대비 비현실적 매출
```python
df['aov'] = df['revenue'] / df['conversions']     # 객단가
print("객단가 상위 5건 (이상치 후보):")
print(df.sort_values('aov', ascending=False)[['date','channel','conversions','revenue','aov']].head())
```
→ 이메일 특정 일자(2026-04-26)의 매출이 같은 채널 평소의 ~9배. 입력 오류 의심 → 제외 또는 별도 표기.

### (b) 광고비 이상치 — 주별 급등/급락
```python
wk = df.groupby(['channel','week'])['spend'].sum().unstack()
print("채널 × 주차 광고비:")
print(wk.round(0))
```
→ 메타광고 W5 광고비가 평소의 ~3.5배(예산 과집행), 카카오광고 W4가 평소의 ~0.6배(급락) 등 확인.

### (c) 오가닉 spend=0 (정상이지만 ROI 계산 시 주의)
```python
print("오가닉 광고비 합계:", df[df['channel']=='오가닉']['spend'].sum())  # 0
```
→ ROI = revenue/spend 에서 0으로 나누기 발생. spend>0 채널만 ROI 산출하고 오가닉은 "측정 불가" 처리.

---

## Step 5: 채널 × 주차 데이터 완전성 점검

```python
pivot = df.pivot_table(index='week', columns='channel', values='spend', aggfunc='count')
print("채널별 주차 행 수 (정상=7, 결측/중복 영향 행은 다를 수 있음):")
print(pivot)
```

---

## 완료 기준
- [ ] 행수 280 확인 (중복 제거 전)
- [ ] 결측 3건 위치 파악 완료
- [ ] 완전 중복 1쌍 식별·제거 완료
- [ ] 매출 이상치 1건(이메일) 식별 완료
- [ ] 오가닉 spend=0 확인 (ROI 측정 불가 처리 방침 결정)
- [ ] 주별 급등(메타 W5)·급락(카카오 W4) 패턴 확인

→ 완료 후 /insight 실행
