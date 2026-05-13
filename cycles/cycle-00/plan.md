# cycle-00 — Plan: 색온도 제어 PoC

## 목표
"실제로 Windows에서 모니터별 색온도를 바꿀 수 있는가?"를 코드로 증명한다.
GPU 감마 램프(`SetDeviceGammaRamp`) 방식이 이 PC(모니터 3대)에서 동작하는지, 제약은 무엇인지 실측한다.

## 범위 (In)
- 레포 스캐폴딩: `src/nightshift/` 패키지(`color/`, `display/`, 빈 `config/ schedule/ platform/ ui/`), `pyproject.toml`, `requirements*.txt`, `cycles/`, `CLAUDE.md`.
- `color/temperature.py` — Kelvin → RGB 화이트포인트 배율 (Tanner Helland 근사).
- `color/gamma.py` — 256엔트리×3 감마 램프 생성/항등 램프, `SetDeviceGammaRamp` 래퍼(`apply_kelvin`, `reset`), CLI 스모크(`--list / --apply / --reset`).
- `display/monitors.py` — `EnumDisplayMonitors` + `EnumDisplayDevicesW`로 모니터 열거·라벨링.
- 단위 테스트: temperature 변환, gamma 램프 형상/클램핑/단조성.

## 범위 (Out — 이후 cycle)
- tkinter UI (cycle-01), config 저장 (cycle-01), 스케줄/트레이/자동실행 (cycle-02), PyInstaller (cycle-03).

## 검증 기준
1. `python -m pytest` green.
2. `python -m nightshift` 가 모니터 3대를 사람이 식별 가능한 라벨로 출력.
3. `python -m nightshift.color.gamma --apply <i> <K>` 로 특정 모니터만 색이 눈에 띄게 바뀌고, `--reset` 으로 정상 복원.
4. gamma ramp 거부 조건(HDR/드라이버/야간모드/Windows 감마 클램프) 실측 결과를 `check.md`에 기록.
