"""공개용 가짜 주행 로그. 실제 로그(팀 데이터)를 올릴 수 없어서, 모양만 같은 데이터를 만든다.

사용: python synth.py            -> synthetic/sensor_log_20990101_가짜1차~3차.csv.gz
실제 로그에서 본 성질을 흉내 낸다:
- MCU 10 ms 간격, 약 20샘플마다 1개씩 빠짐(간격 11 ms 다음 19 ms) -> 누락률 약 5%
- 라즈베리파이 수신 시각(timestamp)은 여러 샘플이 묶여 같은 값
- 팩 전류 = 인버터 전류 x 0.8 + 잡음  (스케일 계수가 빠진 상태를 그대로 재현)
숫자는 실제 차량 값이 아니다. 파이프라인과 검사가 돌아가는지 보는 용도.
"""
from __future__ import annotations

import gzip
import io
import math
import random
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent
HEADER = ['timestamp', 'stm_ms', 'schema_version', 'pi_boot_id', 'sender_instance_id', 'batch_seq', 'uart_rx_mono_ns',
          'pi_clock_source', 'stm_epoch', 'stm_wrap_count', 'stm_extended_ms', 'pi_mono_fixed_5ms_ns', 'pi_mono_est_ns',
          'FR', 'FL', 'RR', 'RL', 'x_g', 'y_g', 'z_g', 'ecu_temp', 'steering_angle', 'steering_speed', 'inv_temp_igt',
          'inv_temp_motor', 'inv_motor_speed', 'vehicle_speed_kmh', 'inv_dc_current', 'inv_voltage', 'motor_precharge',
          'motor_main_contactor', 'motor_inverter_mode', 'INV_shudder_torque', 'INV_id_feedback', 'INV_iq_feedback',
          'INV_torque_commanded', 'INV_torque_feedback', 'INV_id_command', 'INV_iq_command', 'bms_charge', 'bms_voltage',
          'bms_current', 'bms_ccl', 'bms_dcl', 'bms_temp_maxvalue', 'bms_capacity', 'can1', 'can2']


def session(n: int, rng: random.Random, start_ms: int) -> pd.DataFrame:
    rows = []
    t = start_ms
    v = 0.0
    soc_v = 285.0
    k = 0
    while len(rows) < n:
        # 시계: 보통 10 ms, 가끔 11 -> 19 (한 샘플 빠짐)
        k += 1
        if k % 20 == 0:
            t += 11
        elif k % 20 == 1 and k > 1:
            t += 19
        else:
            t += 10
        phase = (t - start_ms) / 1000.0
        throttle = max(0.0, math.sin(phase / 3.0)) ** 2 if (phase % 60) < 50 else 0.0   # 50초 주행, 10초 정지
        accel = 2.5 * throttle - 0.04 * v - (1.5 if throttle == 0 and v > 0 else 0)
        v = max(0.0, v + accel * 0.01 * 3.6)
        inv = max(0.0, 3.0 + 150 * throttle + 0.4 * v + rng.gauss(0, 4)) if throttle > 0 else max(0.0, rng.gauss(1, 1))
        bms = 0.8 * inv + rng.gauss(0, 3)
        soc_v -= inv * 1e-6
        ts_ms = start_ms + 50 * ((t - start_ms) // 50)     # 50 ms마다 묶여서 받은 것처럼
        rec = dict.fromkeys(HEADER, "")
        rec.update({
            "timestamp": pd.Timestamp("2099-01-01") + pd.Timedelta(milliseconds=ts_ms),
            "stm_ms": t, "vehicle_speed_kmh": round(v, 3), "inv_dc_current": round(inv, 1),
            "inv_voltage": round(soc_v + rng.gauss(0, 0.3), 1), "bms_current": round(bms, 1),
            "bms_voltage": round(soc_v - 3 + rng.gauss(0, 0.3), 1), "x_g": round(accel / 9.8, 3),
            "y_g": 0.0, "z_g": 1.0, "FR": 0.0, "FL": 0.0, "RR": 0.0, "RL": 0.0,
            "motor_main_contactor": 1, "can1": 1, "can2": 1,
        })
        rows.append(rec)
    df = pd.DataFrame(rows, columns=HEADER)
    df["timestamp"] = df["timestamp"].dt.strftime("%Y/%m/%d %H:%M:%S.%f").str[:-3]
    return df


def main() -> None:
    out = ROOT / "synthetic"
    out.mkdir(exist_ok=True)
    rng = random.Random(2099)
    for i, n in enumerate([12000, 18000, 15000], start=1):
        df = session(n, rng, start_ms=100_000 * i)
        buf = io.StringIO()
        df.to_csv(buf, index=False)
        path = out / f"sensor_log_20990101_가짜{i}차.csv.gz"
        with gzip.open(path, "wt", encoding="utf-8", newline="") as fh:
            fh.write(buf.getvalue())
        print(path.name, len(df), "행")


if __name__ == "__main__":
    main()
