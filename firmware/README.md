# 펌웨어 수정안 (afa2026 기준, 실차 시험 전)

팀 계측 코드 [afa2026](https://github.com/tkddn647-ship-it/afa2026)은 2026 버전이라 그대로 두고, 로그 분석(이 레포)에서 나온 수정안을 패치로 따로 둡니다.
기준 커밋: afa2026 `main` **357ff0e** (2026-10-06). **컴퓨터 시험만 통과했고 보드 빌드·실차 시험은 안 했습니다.**

| 패치 | 고치는 것 | 근거 (분석 레포) |
|--|--|--|
| `0001-uart-line-integrity.patch` | MCU 전송 버퍼가 차면 줄 앞부분만 쓰던 것 → 통째로 쓰거나 안 씀. 라즈베리파이 파서: 칸 수가 맞지 않는 줄을 0으로 채우지 않고 버림, 깨진 바이트를 지우지 않고(`errors="ignore"` → `strict`) 버림, 버린 이유를 셈. HB 줄에 MCU가 버린 줄 수 2칸 추가 | README 6-3절, `sql/09` (손상 행의 can2 = 0: 83.6% vs 정상 0.007%) |
| `0002-crc16.patch` | 줄 끝에 CRC-16 (`*HHHH`, 다항식 0xA2EB = Koopman 표기 0xD175, 초깃값 0xFFFF). 처음 넣은 CRC-8은 이 줄 길이(약 1,550비트)에서 해밍 거리 2라 바꿈 | Koopman CRC 표, FAA TC-14/49 |
| `0003-vsm-contactor-mapping.patch` | `motor_main_contactor`를 인버터 VSM 상태 ≥ 2(초기충전 중)부터 1로 기록하던 것 → CAN Protocol V5.9대로 3~6만 닫힘, 1~2는 초기충전 | README 6-4절 REQ-14 (로그의 '닫힘' 뒤 전류 0 A로 전압 16% → 90% 약 920 ms) |

## 적용과 시험

```bash
git clone https://github.com/tkddn647-ship-it/afa2026 && cd afa2026
git checkout 357ff0e
git am /path/to/firmware/patches/*.patch
bash device/tests/make_and_run.sh     # gcc, python3 필요. 보드 없이 컴퓨터에서 돎
```

시험 내용 (`device/tests/`):
- 전송 버퍼: 넘칠 때 줄을 반만 쓰지 않는지, 버린 줄 수를 세는지
- 파서: 지금 펌웨어 줄·예전 줄·CRC 붙은 줄을 받고, 칸 수가 틀리거나 CRC가 틀린 줄은 버리는지
- UART 줄 결함 주입: 글자 빠짐·끼어듦·쉼표 빠짐·바이트 뒤바뀜 약 4만 개 → 받아들인 줄 0개
- VSM 매핑: 11개 상태 (2 = 초기충전 중은 닫힘 아님)

## 아직 모르는 것
- 보드에서 빌드되는지, 타이밍(통째로 쓰기 때문에 버린 줄이 늘 수 있음)
- 인버터가 실제 AIR를 제어하는지. 실제 릴레이 상태가 필요하면 CAN `0x0AA` 바이트 3(Relay State)을 따로 기록해야 함
- 누락의 5%(200 ms마다 한 칸, ECU 온도 읽기와 같은 위상)는 이 패치로 고치지 않음. 보드에서 ADC 읽기 시간을 먼저 재야 함 (README 9절)
- 수정 효과 판정: 수정 펌웨어로 달린 로그를 `pipeline.py`에 넣으면 '기준 세션 대비 변화'에 결합비가 나옴 (README 9절)
