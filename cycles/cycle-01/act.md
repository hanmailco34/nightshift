# cycle-01 — Act: 다음 사이클 반영사항

## 결정 / 확정된 인터페이스
1. **`color.gamma.apply_kelvin(device_name, kelvin, brightness=1.0, clamp_to_windows_limit=True) -> bool`** — cycle-02에서도 동일 시그니처 유지.
2. **`color.controller.Controller`** + `from_config(cfg) -> Controller` — UI 외에서도(스케줄러) 직접 사용 가능. `apply_current(devices) -> failed[]`가 단일 진입점.
3. **`config.store`** — `load/save/default_config/config_path/ensure_monitor_entries`. `schema_version=1` 유지, 키 추가 시 `default_config`에만 채우면 자동 머지됨.
4. **`platform.registry.read_gdi_icm_gamma_range()`** — 읽기 전용. cycle-02에서 같은 패키지에 `autostart`, `fullscreen` 추가 예정.
5. UI 종료 시 모든 모니터를 `reset`하는 cycle-01 동작은 cycle-02 트레이 도입과 함께 변경됨: 창 닫기 = 트레이로 최소화(reset 안 함), 트레이 "종료"에서만 reset.

## cycle-02 착수 항목
- `schedule/engine.py`
  - 백그라운드 스레드 30s tick. config.schedule(`manual`/`night_start`/`day_start`) 또는 `astral` 기반 sunrise/sunset(`location`)로 목표 모드 산출.
  - 모드 변경 시 `controller.set_mode` + 부드러운 보간(2–3초 사이 day↔night K 선형 트윈, `apply_current` 반복 호출).
  - `toggles.use_sunset`로 manual / astral 전환.
- `platform/autostart.py`
  - `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` 등록/해제 (winreg, 일반 사용자 권한 OK). `nightshift` 값에 현재 `sys.executable` + `-m nightshift` (PyInstaller exe 시엔 exe 경로). config.toggles.autostart 동기.
- `platform/fullscreen.py`
  - `GetForegroundWindow` + `GetWindowRect`로 현재 창이 어느 모니터 전체를 덮는지 검사. desktop/shell 제외. 일치하면 `reset_all` 임시 적용, 벗어나면 `apply_current` 복귀. toggle(`disable_on_fullscreen`)로 on/off.
- `ui/tray.py`
  - `pystray` + `Pillow` 아이콘. 메뉴: 열기 / 야간 즉시 / 일시중지(스케줄 정지) / 종료(트레이 종료 시 `reset_all`).
  - 창 닫기 동작 변경: `WM_DELETE_WINDOW` → 숨김 + 트레이로 최소화 (현재 cycle-01의 reset 동작은 트레이의 "종료"로 이동).
- 메인 윈도우 보강
  - 설정 사이드 카드(스케줄/위치/3 토글) 활성화. 현재는 placeholder 상태.
  - `apply_current` 실패 device 표시(현재 stdout) → UI에 상태바/토스트 정리.

## 미해결 / 리스크
- HDR 모니터 실측 (`apply_kelvin` 실패) — 이 PC엔 없음, 베타 사용자 피드백 필요.
- 다른 GPU/드라이버에서 `GdiICMGammaRange=256` 무효 케이스 — 자가 진단으로 잡히긴 하나, 사용자에게 더 큰 값(512/1024) 시도 안내를 README에 추가 검토.
- 스케줄러 보간 중 사용자가 슬라이더 만지면 충돌 — 보간 중에는 슬라이더 disabled로 안내하거나, 사용자 입력을 우선시하고 보간 취소하는 정책 결정 필요(cycle-02 plan에서 결정).
- PyInstaller(`pystray` 포함) onefile 크기 — 40MB 제약 cycle-03에서 확인.

## 확정된 cycle-02 검증 기준 (초안)
- 야간 시각 도달 시 자동 전환(테스트는 임시로 현재+1분으로 스케줄).
- astral 모드에서 위도/경도 변경 시 일출/일몰 시각 즉시 반영.
- 자동실행 토글 ON 후 재부팅 시 트레이로 자동 기동.
- 전체화면 게임/영상 실행 시 색온도 즉시 정상 복원, 종료 시 야간 복귀.
- 트레이 메뉴 4항목 모두 동작.
