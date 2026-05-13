# cycle-02 — Plan: 스케줄 + 트레이 + 자동실행 + 전체화면 감지

## 목표
cycle-01의 정적 UI에 **자동 모드 전환**(스케줄러)과 **백그라운드 운영**(시스템 트레이 + 자동실행 + 전체화면 감지)을 추가해 f.lux와 동일한 일상 사용 흐름을 완성한다. 추가 의존성은 이미 `requirements.txt`에 있는 `pystray` / `Pillow` / `astral`만 사용.

## 스레딩 정책 (핵심)
- **tk 메인 스레드**만 `controller` / `store` / `gamma.apply_kelvin`을 호출한다.
- **스케줄러** = 데몬 스레드, 30초 tick으로 목표 mode만 계산. 실제 전환이 필요하면 `root.after(0, on_mode_change)` 콜백으로 tk 스레드에 위임.
- **트레이(pystray)** = 자체 스레드. 메뉴 핸들러는 모두 `root.after(0, ...)`로 마샬링.
- **보간 / 전체화면 폴링**은 tk의 `after` 타이머에서 실행(스레드 안전).
- → controller는 단일 스레드에서만 변경되므로 락 불필요.

## 범위 (In)

### `schedule/engine.py` (신규)
- 두 모드:
  - **manual**: `config.schedule.night_start` / `day_start`, "HH:MM" 문자열. 21:00 ≤ 현재 < 다음날 07:00이면 night, 그 외 day.
  - **astral**: `astral.LocationInfo` + `astral.sun.sun(date, observer)`. `sunset ≤ 현재 < 다음날 sunrise` 이면 night.
- 스위치: `config.toggles.use_sunset` (true=astral, false=manual). 기존 `config.schedule.manual` 키는 deprecated — 무시(향후 정리).
- `current_target_mode(now, cfg) -> "day"|"night"` — 순수 함수, 테스트 용이.
- `next_transition(now, cfg) -> datetime` — UI의 "다음 일몰/일출 hh:mm" 라벨용.
- `Scheduler` 클래스:
  - `Scheduler(controller, get_devices_fn, root, get_cfg_fn, interp_duration_ms=5000, interp_steps=20)`
  - `start()` → 데몬 스레드 시작 (30s tick). `stop()` → 스레드 종료. `pause()` / `resume()`.
  - tick: `target = current_target_mode(now, cfg)` → `controller.mode`와 다르면 `root.after(0, lambda: _begin_transition(target))`.
  - `_begin_transition(target)`: tk 스레드에서 실행. 현재 모드의 K → 목표 모드의 K를 20스텝 동안 250ms 간격으로 임시 K로 보간 적용(`apply_kelvin` 직접 호출, controller.mode는 마지막에만 변경). 보간 중 사용자가 슬라이더 만지면(`set_temperature` 호출 받으면) 외부에서 `cancel_transition()` 호출 → 진행 중 `after` job 취소.
- 보간 토큰: 새 전환 시작할 때마다 보간 ID 증가, after 콜백이 자기 ID와 다르면 무시 → 빠른 연속 전환 안전.

### `platform/autostart.py` (신규)
- `HKCU\Software\Microsoft\Windows\CurrentVersion\Run\nightshift` 값 = 실행 명령.
- `_command() -> str`:
  - `sys.frozen` 진실값이면 `f'"{sys.executable}"'`
  - 아니면 `f'"{sys.executable}" -m nightshift'`
- `is_registered() -> bool`, `register() -> None`, `unregister() -> None` — 일반 사용자 권한으로 가능(HKCU).
- `sync_with_config(cfg) -> None` — `toggles.autostart`가 True면 register, False면 unregister.

### `platform/fullscreen.py` (신규)
- `is_fullscreen_app_visible(monitors) -> bool`:
  - `user32.GetForegroundWindow` → `GetWindowRect`.
  - 클래스명을 `RealGetWindowClassW`로 받아 `{"Progman", "WorkerW", "Shell_TrayWnd"}` 면 False.
  - 모니터 중 하나의 `(x, y, x+w, y+h)`와 ±2px 이내 일치하면 True.
- 매칭 로직은 monitor 좌표 입력만 받는 작은 헬퍼(`_rect_matches_monitor(win_rect, mon)`)로 분리 → 단위 테스트 가능.
- UI가 300ms `after` 타이머로 폴링.
- 진입 시: `controller.reset_all(devices)` + 내부 플래그 ON (controller.mode·targets는 그대로). 벗어남: 플래그 OFF + `controller.apply_current(devices)`.
- 토글: `config.toggles.disable_on_fullscreen`.

### `ui/tray.py` (신규)
- `pystray.Icon` + `Pillow`로 16x16 단색 달 아이콘(in-memory `Image.new` + 원 그리기 또는 단순 색 사각).
- 메뉴 4개:
  - **열기** → `root.after(0, lambda: (root.deiconify(), root.lift()))`
  - **일시중지 / 다시 시작** (`pystray.MenuItem` `checked` 콜백) — pause = `Scheduler.pause()` + `controller.reset_all(devices)` + 내부 플래그 ON. resume = 플래그 OFF + `Scheduler.resume()` + `controller.apply_current(devices)`.
  - **야간 즉시** → `controller.set_mode("night")` + 보간 트리거(`Scheduler._begin_transition("night")` 강제 호출 또는 별도 메서드).
  - **종료** → `Scheduler.stop()` + `controller.reset_all(devices)` + `tray.icon.stop()` + `root.destroy()`.
- 모든 핸들러는 `root.after(0, fn)`로 tk 스레드에 위임. `Icon.run_detached()`로 트레이 스레드 데몬 시작.

### `ui/main_window.py` 보강
- 우측 사이드 카드(현재 placeholder) 활성화 — `ttk.LabelFrame` 3개:
  1. **스케줄**: 라디오(수동 / 일몰 감지) — `toggles.use_sunset`와 동기. 시간 입력 2개(`Spinbox` 또는 `Entry`, HH:MM 검증). 위/경도 `Entry` 2개. astral 모드일 때만 "다음 일출 hh:mm / 다음 일몰 hh:mm" 라벨 갱신(`Scheduler.next_transition` 사용, 1분마다 갱신).
  2. **자동 실행**: 체크박스 `toggles.autostart` — 변경 시 `autostart.sync_with_config` 호출.
  3. **기타**: `toggles.disable_on_fullscreen` 체크박스.
- **하단 상태바**(`ttk.Label`, sticky bottom): 평상시 "주간 6500K (수동 21:00→야간)" 같은 한 줄 요약. `apply_current` 실패 시 빨간색으로 "Monitor 2 적용 실패 (HDR/드라이버)".
- **창 X 동작 변경**: `_on_close` 에서 `reset_all` 제거 → `self.root.withdraw()`. 첫 닫기 시 트레이가 풍선 알림(`Icon.notify`) 한 번만 띄움(`_first_minimize` 플래그).
- 트레이 "종료"가 유일한 실제 reset 지점.

### `__main__.py` 와이어업
- UI 진입점에서 한 번에 다 묶음:
  ```python
  win = MainWindow()
  scheduler = Scheduler(win.controller, lambda: [m.device_name for m in win.monitors],
                         win.root, lambda: win.cfg)
  fullscreen = FullscreenGuard(win.controller, lambda: win.monitors, win.root)
  tray = Tray(win.root, scheduler, win.controller, ...)
  autostart.sync_with_config(win.cfg)
  scheduler.start(); fullscreen.start(); tray.start()
  win.run()  # blocks
  # main loop exited (tray "종료")
  scheduler.stop()
  ```
- `MainWindow.__init__`에 위 객체 참조 보관해서 슬라이더 콜백이 `scheduler.cancel_transition()` 호출 가능.

### 인터페이스 보강 (cycle-01 → cycle-02, breaking 없음)
- `MainWindow` 생성자에 선택 인자 추가 또는 attach 메서드:
  - `attach_scheduler(scheduler)`, `attach_tray(tray)`, `attach_fullscreen(fg)`.
- 슬라이더 변경 콜백에서 `scheduler.cancel_transition()` 호출(보간 중이면).

### 테스트
- `tests/test_schedule_engine.py`
  - manual 경계: 06:59→day, 07:00→day, 20:59→day, 21:00→night, 02:00→night, 23:30(밤)→night 등.
  - astral: 모킹된 `astral.sun.sun()` 결과(고정 sunrise=06:00, sunset=19:00)로 06:30→day, 18:59→day, 19:01→night, 05:30→night.
  - `next_transition` 시각 계산.
  - 보간 K 시퀀스: 6500K→2700K 20스텝이 (a) 정확히 21개 값, (b) 단조 감소, (c) 양 끝점 6500/2700.
- `tests/test_autostart.py`
  - `_command()` 가 sys.frozen 분기에 따라 다르게 반환.
  - `register/is_registered/unregister`를 in-memory dict로 monkeypatch한 winreg에 대해 round-trip.
- `tests/test_fullscreen.py`
  - `_rect_matches_monitor(win_rect, mon)` 단위 — 정확 일치, ±2px 이내, 4px 차이는 False.

UI / 트레이 / 자동실행 ON 후 재부팅은 수동 검증.

## 범위 (Out — cycle-03 이후)
- PyInstaller `nightshift.spec` (`--onefile --windowed`, 아이콘, exclude로 ≤40MB).
- GitHub Actions release workflow.
- README 사용법/제약/다운로드 안내 마무리.

## 검증 기준
1. `python -m pytest -q` 전부 green (cycle-00/01 회귀 + cycle-02 신규).
2. `schedule.night_start`를 임시로 "현재+1분"으로 두고 메인 윈도우 실행 → 약 1분 후 **5초 동안 부드럽게** 야간으로 전환.
3. `use_sunset` 켜고 위/경도 변경 → "다음 일몰 hh:mm" 라벨이 즉시 갱신, 실제 일몰 도달 시 야간 전환.
4. 자동실행 토글 ON → 재부팅 시 트레이로 자동 기동(메인 창 숨김 상태).
5. 전체화면 영상/게임 실행 → 색온도 즉시 정상색 복귀, 종료 시 야간 복귀.
6. 트레이 메뉴 4가지 모두 동작 (열기 / 일시중지↔다시 시작 / 야간 즉시 / 종료).
7. 창 X로 닫고 트레이 "열기"로 복원, controller state·슬라이더 위치 유지.

## 리스크 / 미정
- `astral` API 사용법 (LocationInfo / observer / sun()의 timezone 처리) — 첫 구현 시 한국 시간대(+09:00) 명시. 머신 로컬 타임존이 다른 경우 검토.
- pystray 트레이 아이콘이 일부 Windows 11 (예: 알림 영역 그룹화)에서 첫 시작 시 숨겨질 수 있음 — README에 "꺽쇠 ^ 클릭 후 nightshift 아이콘을 작업표시줄로 드래그" 안내 추가 검토.
- PyInstaller(`pystray` 포함) onefile 크기 — cycle-03에서 측정. 초과 시 `--exclude` 폭증.
- 보간 중 트레이 "일시중지" 동시 입력 → 일시중지가 우선해서 보간 취소 + reset (cancel 토큰으로 처리).

## 산출 (사이클 종료 시 채워질 것)
- `do.md` / `check.md` / `act.md`
- `CLAUDE.md` 사이클 로그에 한 줄 추가
