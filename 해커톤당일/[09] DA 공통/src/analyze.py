"""데이터 품질 파악 (analyze.md Step 0~5) — 정제 전 raw CSV 진단용."""
import pandas as pd

df = pd.read_csv('[09] DA 공통/data/marketing_performance.csv')
print("=== Step 0: 로드 & 형태 ===")
print("행수:", len(df))
print("주차:", sorted(df['week'].unique()))
print("채널:", df['channel'].unique())

num_cols = ['impressions', 'clicks', 'spend', 'conversions', 'revenue']
for c in num_cols:
    df[c] = pd.to_numeric(df[c], errors='coerce')

print("\n=== Step 2: 결측치 ===")
print(df[num_cols].isna().sum())
print("\n결측 포함 행:")
print(df[df[num_cols].isna().any(axis=1)][['date', 'channel', 'week'] + num_cols])

print("\n=== Step 3: 완전 중복 행 ===")
dups = df[df.duplicated(keep=False)]
print(dups.sort_values(list(df.columns)))
print("중복 제거 전:", len(df), "→ 제거 후:", len(df.drop_duplicates()))

df_dedup = df.drop_duplicates()

print("\n=== Step 4(a): 매출 이상치 (객단가 상위 5) ===")
tmp = df_dedup.copy()
tmp['aov'] = tmp['revenue'] / tmp['conversions']
print(tmp.sort_values('aov', ascending=False)[['date', 'channel', 'conversions', 'revenue', 'aov']].head())

print("\n=== Step 4(b): 채널 x 주차 광고비 ===")
wk = df_dedup.groupby(['channel', 'week'])['spend'].sum().unstack()
print(wk.round(0))

print("\n=== Step 4(c): 오가닉 spend 합계 ===")
print(df_dedup[df_dedup['channel'] == '오가닉']['spend'].sum())

print("\n=== Step 5: 채널별 주차 행 수 ===")
pivot = df_dedup.pivot_table(index='week', columns='channel', values='spend', aggfunc='count')
print(pivot)
