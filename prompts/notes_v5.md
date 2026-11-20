이 데이터의 분석 규칙 v5 (v4에서 5번을 고침: 깨진 값 규칙 v2 — 모든 숫자 열 검사 bad_value, 한 행에서 튄 열 수 n_bad_cols 추가)

1. 행 순서는 항상 row_no 로 정한다. stm_ms 에는 글자가 빠지거나 끼어든 깨진 값이 있어 정렬에 쓰지 않는다.
2. 시간 간격은 같은 세션 안에서 앞 행과의 stm_ms 차이(ms)로 계산한다.
   ts_utc 는 라즈베리파이가 여러 샘플을 묶어서 받은 시각이라 같은 값이 여러 행에 반복되므로 간격 계산에 쓰지 않는다.
   간격을 계산하기 전에 sample_flags 의 bad_ms = 1 인 행은 뺀다.
3. MCU는 10 ms마다 샘플을 보낸다. 앞 행과의 간격 d 로 나눈다.
   - 15 < d <= 1000 : ROUND(d / 10.0) - 1 - (그 두 행 사이에 있던 bad_ms 행 수) 개가 빠진 것 (0보다 작으면 0)
     (bad_ms 행은 간격 계산에서만 빼고, 받은 샘플로는 센다. 두 행 사이 bad_ms 행 수 = row_no 차이 - 1)
   - d > 1000      : 기록이 끊긴(멈춘) 구간 1번. 누락으로 세지 않는다
   - d < 0         : MCU 재시작 1번 (속도 같은 다른 조건은 붙이지 않는다)
   누락률(%) = 빠진 샘플 / (받은 샘플 + 빠진 샘플) * 100. 받은 샘플은 세션 전체 행 수 (bad_ms 행 포함).
4. 부하 구간 = inv_dc_current > 25 A. 부하 구간을 다루는 질문에서는 sample_flags 의 bad_inv, bad_bms 가 1인 행을 뺀다.
   부하 구간이 '끊기지 않고 이어진 구간'은 이렇게 뺀 행들 안에서 row_no 가 1씩 이어지는 묶음이다.
5. 깨진 행 = sample_flags 에서 bad_ms, bad_inv, bad_bms, bad_speed, bad_value 중 하나라도 1 인 행. 비율은 세션 전체 행 수 대비.
   bad_value = 검사하는 숫자 열 30개 중 하나라도 튄 값 (어느 열인지는 value_flag 표: session_id, row_no, column_name, value, median5).
   n_bad_cols = 그 행에서 튄 열 수. 3 이상이면 '행 손상'(한 줄 전체가 밀리거나 깨짐).
6. 보정 뒤 팩 전류 = bms_current * (scale_correction 표의 bms_current factor). 숫자를 쿼리에 직접 쓰지 말고 표에서 읽는다.
   질문에 "보정"이라는 말이 없으면 보정하지 않은 bms_current 원본을 쓴다.
7. 퍼센트와 비율은 반올림하지 말고 계산값 그대로 낸다.
8. 세션별 질문이면 세션 라벨(session.label)을 같이 보여 준다.
