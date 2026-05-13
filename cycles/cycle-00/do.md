# cycle-00 — Do: 작업 로그

## 만든 것
- `pyproject.toml` (src 레이아웃, `pytest.pythonpath=src`, console script `nightshift`), `requirements.txt`, `requirements-dev.txt`.
- `src/nightshift/__init__.py` — 버전 + 상수(DAY/NIGHT/MIN/MAX Kelvin).
- `src/nightshift/__main__.py` — 진단용 엔트리포인트(모니터 목록 출력). UI는 cycle-01.
- `src/nightshift/color/temperature.py` — `kelvin_to_rgb(k) -> (r,g,b)` 배율, Tanner Helland 근사. `[0,1]` 클램프.
- `src/nightshift/color/gamma.py`
  - `build_gamma_ramp(kelvin, brightness=1.0, clamp_to_windows_limit=True)` — `[red,green,blue]` 각 256개 WORD(0–65535). 채널 = 선형 램프 × 화이트포인트 배율 × brightness, 그리고 각 엔트리를 선형 ±`WINDOWS_GAMMA_DEVIATION_LIMIT`(32000) 안으로 클램핑(아래 check.md 참고).
  - `identity_ramp()` — 무보정(선형) 램프.
  - `apply_kelvin(device_name, kelvin, brightness)` / `reset(device_name)` — `CreateDCW("DISPLAY", deviceName)` → `SetDeviceGammaRamp` → `DeleteDC`. 비-Windows에선 `OSError`.
  - CLI: `python -m nightshift.color.gamma --list | --apply <idx> <kelvin> | --reset`.
- `src/nightshift/display/monitors.py` — `Monitor` 데이터클래스 + `list_monitors()`(`EnumDisplayMonitors`+`GetMonitorInfoW`로 device/geometry/primary, `EnumDisplayDevicesW`로 모델명), `find_by_device()`. 좌→우, 상→하 정렬.
- 테스트: `tests/test_temperature.py`(5케이스), `tests/test_gamma_ramp.py`(8케이스 — 형상/16bit범위/단조성/항등근사/blue감쇠/brightness/클램프한계/미클램프초과). 총 13 green.

## 설치/실행
- `pip install -e .` 로 editable 설치 → `python -m nightshift`, `python -m nightshift.color.gamma ...` 동작.

## 도중에 고친 것
- 콘솔 인코딩(cp949)이 em dash `—` 인코딩 실패 → 라벨/메시지를 ASCII 하이픈 `-` 으로 교체.
- `build_gamma_ramp(6500)`은 항등 램프와 *정확히* 같지 않음(녹색 배율 ≈ 0.976). 도큐스트링/테스트를 "근사(±3%)"로 수정. 정확한 리셋은 `identity_ramp()` 사용.

## 환경
- Windows 11 Pro 26200, Python 3.12, 모니터 3대:
  - `\\.\DISPLAY3` 2560x1440 @(-3840,-728)
  - `\\.\DISPLAY2` 1920x1080 @(0,0) — primary
  - `\\.\DISPLAY1` 1440x900 @(1920,-379)
  - 모델명은 셋 다 "Generic PnP Monitor"로 보고됨(EDID 미보고 환경).
