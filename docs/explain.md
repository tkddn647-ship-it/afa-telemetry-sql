# 설명 노트 — 핵심 SQL 기법과 AI 활용

이 프로젝트를 남에게 설명할 때 쓰는 노트입니다. 기법마다 **문제 → 쿼리(레포의 실제 코드, 줄임) → 결과 → 예상 질문** 순서로 적었습니다.
숫자는 모두 2026-08-11 로그 10세션 기준이고, 재현 명령은 [README](../README.md)와 [상세](details.md)에 있습니다.

---

## 1. 이웃 행과 비교하기 — `LAG` / `LEAD`

**문제.** MCU 시각(`stm_ms`)에 숫자 글자가 빠지거나 끼어든 행이 있습니다 (예: 오후1차 11419·11420행의 `37721243`, `37222` — 앞뒤 행과 1초 넘게 다름). 값 하나만 보면 정상인지 모르고, **앞뒤 행과 비교해야** 압니다.

**쿼리** ([`sql/01_flags.sql`](../sql/01_flags.sql)):
```sql
WITH w AS (
    SELECT s.*, LAG(stm_ms) OVER o AS p_ms, LEAD(stm_ms) OVER o AS n_ms,
                LAG(stm_ms, 2) OVER o AS p2_ms, LEAD(stm_ms, 2) OVER o AS n2_ms
    FROM sample s
    WINDOW o AS (PARTITION BY session_id ORDER BY row_no)
)
SELECT w.*,
    COALESCE((ABS(stm_ms - p_ms) > 1000 AND ABS(stm_ms - n_ms) > 1000 AND n_ms - p_ms BETWEEN 0 AND 200), 0)
 OR COALESCE((ABS(stm_ms - p_ms) > 1000 AND ABS(stm_ms - n2_ms) > 1000 AND n2_ms - p_ms BETWEEN 0 AND 300), 0)
 ...  AS bad_ms
```
- **"이 행만 앞뒤와 1초 넘게 다르고, 앞뒤끼리는 0~200 ms"**여야 깨진 시각입니다. 앞뒤끼리도 멀면 진짜 멈춘 구간입니다.
- 정렬 기준이 `stm_ms`가 아니라 **`row_no`(파일 안 순서)**입니다. 시각 자체가 깨질 수 있어서입니다.
- 깨진 시각이 **두 행 연달아** 오는 경우(오후1차 11419·11420행)는 한 칸 건너 이웃(`LAG(.., 2)`)과도 비교합니다. 처음엔 이걸 못 잡아 가짜 MCU 재시작 1번이 나왔습니다.
- `COALESCE(..., 0)`: 세션 첫 행은 이웃이 없어 비교가 `NULL`이 되고, `WHERE NOT bad_ms`에서 정상 행까지 빠졌습니다. 그래서 0으로 둡니다.

**결과.** 결함 주입 시험에서 깨진 시각 899/900을 잡습니다. 놓친 1개는 MCU 재시작 바로 앞 행이었습니다.

**예상 질문.**
- Q. 왜 `stm_ms`로 정렬하지 않았나? → 시각이 깨진 행은 엉뚱한 위치로 가 버립니다. 받은 순서(`row_no`)가 더 믿을 만합니다.
- Q. `PARTITION BY session_id`를 빼면? → 앞 세션의 마지막 행과 다음 세션의 첫 행을 비교해 버립니다.

---

## 2. MEDIAN 없이 중앙값 구하기 — 전체 중앙값과 5행 이동 중앙값

**문제.** SQLite에는 `MEDIAN`이 없습니다. 그런데 두 곳에서 중앙값이 필요합니다. 하나는 세션별 전류 비율(이상한 값에 덜 흔들리는 대표값), 다른 하나는 **튄 값 판정용 5행 이동 중앙값**입니다.

**쿼리 ① 세션 전체 중앙값** ([`sql/02_ratio_median.sql`](../sql/02_ratio_median.sql)):
```sql
ranked AS (
    SELECT session_id, r,
           ROW_NUMBER() OVER (PARTITION BY session_id ORDER BY r) AS rn,
           COUNT(*)     OVER (PARTITION BY session_id)            AS n
    FROM load)
SELECT ..., AVG(r) AS 비율_중앙값
FROM ranked WHERE rn IN ((n + 1) / 2, (n + 2) / 2)    -- 홀수면 같은 행, 짝수면 가운데 두 행
GROUP BY session_id
```

**쿼리 ② 5행 이동 중앙값** ([`sql/01a_value_flags.sql`](../sql/01a_value_flags.sql)):
```sql
(SELECT x FROM (SELECT a AS x UNION ALL SELECT b UNION ALL SELECT v UNION ALL SELECT d UNION ALL SELECT e)
 ORDER BY x LIMIT 1 OFFSET 2) AS med          -- a, b = 앞 2행, d, e = 뒤 2행 (LAG/LEAD)
```
- 판정: `|값 − 5행 중앙값| > 열별 기준`이고, 그 값이 50 ms 이하로만 나타났으면 튄 값입니다.
- **왜 5행인가:** 3행 이상 이어진 값은 5행 안에서 다수가 되어 중앙값이 그 값이 됩니다. 그래서 1~2행짜리 값만 잡힙니다. CAN 값은 약 10행(100 ms)마다 바뀌므로 1~2행만 나타난 값은 새 프레임일 수 없습니다.
- 처음엔 7행 Hampel 필터(중앙값 ± MAD × k)였습니다. 7행은 3행 유지값까지 잡았고, MAD 항은 실제 로그 1,351칸 중 5칸만 바꿨습니다. CAN 값이 유지되어 MAD가 0이 되는 현상(Pearson 외 2016의 'implosion')으로 설명됩니다. 그래서 둘 다 뺐습니다.

**결과.** 전류 비율 중앙값은 0.801·0.795·0.796입니다 (pandas로 따로 계산해도 같음). 튄 값 규칙은 두 행 연달아 튄 값을 0%에서 99.5%로 잡게 됐고, 실제 로그의 깨진 행은 88에서 610행이 됐습니다.

**예상 질문.**
- Q. 평균 대신 중앙값을 쓴 이유? → 깨진 행(274.5 A 같은 값)이 평균을 끌고 갑니다. 중앙값은 절반 가까이 틀리지 않는 한 버팁니다.
- Q. 기준을 왜 열마다 다르게? → CAN 값(유지됨)은 범위의 5%, 서스펜션·조향(매 행 바뀜)은 1배, 가속도(노면 충격이 정상)는 2배입니다. 열의 성질이 다릅니다.

---

## 3. 이어진 구간 묶기 — gaps-and-islands

**문제.** "인버터 전류 > 25 A인데 팩 전류 ≤ 0.5 A"인 행이 **10행 이상 이어지면** 불일치 1번으로 셉니다. 행 단위 조건은 쉽지만 "이어진 덩어리"를 묶는 건 다른 문제입니다.

**쿼리** ([`sql/10_cross_signal.sql`](../sql/10_cross_signal.sql)):
```sql
mm AS (
    SELECT session_id, row_no,
           row_no - ROW_NUMBER() OVER (PARTITION BY session_id ORDER BY row_no) AS grp
    FROM c WHERE inv_dc_current > 25 AND bms_current <= 0.5),
mm_run AS (SELECT session_id, grp, COUNT(*) AS n FROM mm GROUP BY session_id, grp)
SELECT ... (SELECT COUNT(*) FROM mm_run r WHERE ... AND n >= 10) AS 전류_불일치
```
- 조건에 맞는 행만 남기고 번호를 다시 매기면, **이어진 행끼리는 `row_no − 새 번호`가 같습니다.** 예를 들어 행 5, 6, 7은 새 번호가 1, 2, 3이라 차이가 모두 4이고, 행 20은 새 번호가 4라 차이가 16입니다. 이 차이를 덩어리 이름으로 씁니다.

**결과.** 10행 이상 이어진 불일치는 10세션에서 11번이었습니다. 10행 미만 108번은 두 CAN 메시지의 갱신 시점 차이로 봤습니다. 처음 보고서엔 "세션마다 10~179행"이라고 썼는데, 짧은 것까지 다 더한 수여서 고쳤습니다.

**예상 질문.**
- Q. 10행 기준은 어디서? → CAN 한 주기가 약 100 ms(10행)입니다. 한 주기보다 길게 어긋나면 갱신 차이로 설명이 안 됩니다.

---

## 4. 간격으로 빠진 샘플 세기

**문제.** MCU는 10 ms마다 보내는데 파일엔 빠진 샘플이 있습니다. 빠진 줄은 없으니 **시각 간격**으로 셉니다.

**쿼리** ([`sql/06_sample_loss.sql`](../sql/06_sample_loss.sql)):
```sql
gap AS (
    SELECT session_id, stm_ms - LAG(stm_ms) OVER w AS d,
           row_no - LAG(row_no) OVER w - 1 AS skipped           -- 그 사이에 뺀 깨진 시각 행
    FROM clean WINDOW w AS (PARTITION BY session_id ORDER BY row_no)),
miss AS (
    SELECT session_id, d,
           CASE WHEN d > 15 AND d <= 1000 THEN MAX(ROUND(d / 10.0) - 1 - skipped, 0) ELSE 0 END AS m
    FROM gap)
```
- 간격 30 ms면 두 개가 빠진 것입니다 (`ROUND(30/10) − 1 = 2`). 1초 넘는 간격은 주행을 멈춘 것, 음수는 MCU 재시작입니다.
- `skipped`: 깨진 시각 행은 간격 계산에서 빼지만 받은 샘플입니다. 처음엔 그 자리를 빠진 샘플로 한 번 더 셌습니다. 결함 주입 시험에서 심은 344개를 524개로 세는 걸 보고 찾았습니다.

**결과.** 누락률은 5.0~12.5%입니다. 그중 **약 5%는 200 ms마다 한 칸씩 빠지는 고정 패턴**(19 ms + 11 ms 간격)이고, ECU 온도 읽기와 같은 위상입니다 (온도가 바뀐 행의 87.5%). 나머지 누락은 깨진 행과 비율 0.106으로 함께 움직입니다 (10세션 상관 0.999). [`sql/11`](../sql/11_loss_structure.sql)

**예상 질문.**
- Q. 상관 0.999면 인과인가? → 아닙니다. 세션 간 상관은 크기 차이가 키웁니다. 그래서 세션 안 10초 창 단위(0.86)도 같이 봤습니다. 원인 추정(전송 버퍼가 차면 줄 앞부분만 씀)은 펌웨어 코드와 로그 흔적 두 가지로 받쳤지만 실차로 확인하지는 않았습니다.

---

## 5. 정의를 한 곳에 두기 — 뷰와 기준 표

**문제.** 분석 쿼리 10개가 모두 "깨진 행을 뺀 데이터"를 씁니다. 쿼리마다 조건을 쓰면 하나만 바꿔도 결과가 어긋납니다.

**쿼리** ([`sql/01_flags.sql`](../sql/01_flags.sql)):
```sql
CREATE VIEW sample_clean AS
SELECT * FROM sample_flags WHERE NOT (bad_ms OR bad_inv OR bad_bms OR bad_speed OR bad_value);
```
- 숫자 기준도 쿼리에 박지 않고 **표로** 둡니다: 보정 계수(`scale_correction`), 경고 기준(`quality_rule`), 열별 튄 값 기준(`rules/value_check.csv` → `value_check` 표), 로그 형식 대응(`rules/formats.csv`).
- 바꾸면 모든 쿼리가 따라 바뀌고, 왜 그 값인지가 데이터 옆에 남습니다.
- 튄 값은 30열 × 20만 행이라 매번 계산하면 15~30초가 걸립니다. 그래서 결과를 `value_flag` 표에 두고 **새로 넣은 세션만** 다시 계산합니다.

**예상 질문.**
- Q. 뷰 대신 표로 만들면? → 빠르지만 기준을 바꿀 때마다 다시 만들어야 하고, 잊으면 옛 결과를 봅니다. 그래서 비싼 부분(`value_flag`)만 표로 두었습니다.

---

## 6. 같은 규칙을 세 번 구현해 대조하기

**문제.** SQL 결과가 맞는지를 SQL로 확인할 수는 없습니다.

**방법.** 같은 규칙을 따로 세 번 구현해 같은지 봅니다.
- SQL: `sql/01a`, `01`
- pandas: [`verify.py`](../verify.py) `value_flags`
- 한 행씩 받는 실시간 판정: [`replay.py`](../replay.py)

**결과.** 10세션에서 (세션, 행, 열) **1,319칸이 모두 일치**합니다. 분석 숫자 15개도 SQL과 pandas가 같습니다. 규칙을 바꿀 때마다(`test_all.sh`) 다시 대조합니다. 실제로 이 대조로 찾은 버그가 있습니다: 주석(`--`)이 같은 줄의 열 3개를 삼켜 SQL 결과의 열이 밀린 것입니다.

**예상 질문.**
- Q. 세 개 다 같은 버그가 있으면? → 그래서 정답을 아는 결함을 심는 시험(결함 주입)을 따로 둡니다. 구현끼리 대조는 "같은 규칙인가", 결함 주입은 "규칙이 맞는가"를 봅니다.

---

## 7. AI를 어떻게 썼고, 어떻게 믿었나

**① AI가 SQL을 짜게 하고 채점.** 정답을 아는 질문 25개(개발용 17 + 따로 둔 8)를 만들고, AI가 짠 SQL을 실행한 결과를 정답 쿼리 결과와 비교했습니다. [`eval_ai_sql.py`](../eval_ai_sql.py)
- 틀린 이유는 SQL 문법이 아니라 **이 데이터의 정의**였습니다 (누락률 정의, 깨진 행을 빼는지, 보정을 하는지). 그래서 AI에게 주는 정의서를 v1 → v6으로 고쳤습니다. 개발용 정답률은 8~10 → 16/17이 됐습니다.
- **과적합 확인:** 정의서를 고칠 때 보지 않은 8문항을 따로 둡니다 (v6 7~8/8). 따로 둔 문항만 맞히려고 넣은 문장을 하나 발견해 지운 적이 있습니다.
- **범위로 보고:** 같은 지시로 돌려도 답이 달라서 버전마다 3번씩 돌렸습니다 (Atil 외 2024). 그러자 v4·v5·v6의 차이는 범위 안이라 **구분할 수 없다**는 게 보였습니다.

**② 분석 에이전트.** AI가 세션 하나를 도구(SQL 실행, 품질 지표, 열 요약)로 혼자 조사해 보고서를 씁니다. [`agent.py`](../agent.py)
- AI 주장마다 근거 SQL을 **다시 실행해 값이 같은지** 봅니다 (`verify`). 135/135, 98/99, 95/95가 재현됐고, 재현 안 된 1개는 이 검사가 걸러 냈습니다.
- 규칙에 없는 이상을 숨겨 찾게 했습니다. 처음엔 이상 하나를 찾으면 멈춰서 실행마다 9개 중 5~9개로 흔들렸습니다. 열 요약 도구와 "모든 열 확인" 지시를 넣어 36/36이 됐습니다.
- 처음 보는 이상 종류와 새 위치로 시험해, 시험에 맞춘 것이 아닌지 확인했습니다.

**③ AI가 틀린 것을 기록.** [`AI_LOG.md`](../AI_LOG.md)에 49건이 있습니다. 예:
- 프리차지 기준을 95%(독일 규정)로 썼는데, 팀 대회 규정은 90%였습니다.
- "프리차지 미달 6/6"을 위반일 수 있다고 보고했는데, 펌웨어를 보니 신호 정의 결함이었습니다.
- 정지 세션의 "전류 불일치 0번"을 통과로 셌는데, 신호가 없어 잴 수 없었던 것입니다.

**예상 질문.**
- Q. AI가 짠 코드를 어떻게 믿었나? → 같은 결과를 다른 방법으로 다시 계산했습니다 (SQL ↔ pandas ↔ 실시간 구현, AI 주장마다 SQL 재실행). 정답을 아는 결함과 질문으로 채점했습니다.
- Q. 정답 쿼리는 누가 맞다고 보장하나? → pandas로 따로 계산해 맞췄고, 정답이 바뀐 이유는 AI_LOG에 남겼습니다.
