# cycle-02 — Do: 작업 로그

## 만든 것

### 신규 모듈
- `src/nightshift/schedule/` (`__init__.py`, `engine.py`)
  - 순수 함수: `current_target_mode(now, cfg)`, `next_transition(now, cfg)`, `interp_sequence(start, end, steps)`, `_kelvin_for_mode(controller, device, mode)`. 모드 분기는 `cfg.toggles.use_sunset` (true=astral / false=manual). manual은 `schedule.day_start/night_start` HH:MM 문자열, astral은 `_astral_sun_for_date()` 래퍼로 `astral.sun.sun()` 호출 (테스트는 이 래퍼만 monkeypatch).
  - `Scheduler` 클래스: 데몬 스레드 30s tick → `root.after(0, _evaluate_once)`로 tk 스레드에 위임. 모드 변경 시 5초/20스텝(250ms) 선형 K 보간(`gamma.apply_kelvin` 직접 호출, controller.mode는 마지막 스텝에서만 변경). `cancel_transition()` 토큰 증가로 보간 중단. `pause/resume`, `begin_transition_now(target)`, `on_mode_change` 콜백(보간 완료 시 호출 — UI 모드 라디오 동기화용).
- `src/nightshift/platform/autostart.py`
  - `_command()`: `sys.frozen` 진실값이면 `"<exe>"`, 아니면 `"<python>" -m nightshift`.
  - `_read_value() / _write_value() / _delete_value()`: HKCU\...\Run\nightshift 읽기·쓰기·삭제 (각각 `winreg` 호출 단위, 테스트에서 monkeypatch 가능).
  - `is_registered() / register() / unregister() / sync_with_config(cfg)`.
- `src/nightshift/platform/fullscreen.py`
  - `_rect_matches_monitor(win_rect, mon)`: ±2px 톨러런스 기하 비교 (단위 테스트 대상).
  - `_get_foreground_rect()` / `_foreground_class_name()`: Win32 호출 격리.
  - `is_fullscreen_app_visible(monitors)`: shell 클래스 (`Progman/WorkerW/Shell_TrayWnd/Button`) 제외 + 모니터 rect 매칭.
- `src/nightshift/ui/tray.py`
  - `Tray` 클래스: `pystray.Icon` + Pillow 16x16 노란 디스크 아이콘. 메뉴 4개(열기/일시중지[체크박스]/야간 즉시/종료) — 모든 콜백은 외부에서 받은 `on_*` 함수를 호출만 함 (호출자가 `root.after(0, ...)`로 마샬링). `start()`는 `icon.run_detached()`로 데몬 스레드 시작.

### 보강된 파일
- `src/nightshift/ui/main_window.py`
  - 레이아웃 재구성: 상단(모드 라디오/개별/확장 토글) + 우측 사이드 카드(스케줄/자동실행/기타 LabelFrame) + 좌측 모니터 페이지(기존) + 하단 상태바.
  - 사이드 스케줄 카드: 라디오(수동/일출-일몰), HH:MM Entry 2개, 위/경도 Entry 2개, **"적용" 버튼**, "다음 야간/주간 전환: hh:mm" 라벨(1분마다 자동 갱신).
  - 사이드 자동실행 카드: 체크박스 → `autostart.sync_with_config`.
  - 사이드 기타 카드: `disable_on_fullscreen` 체크박스.
  - 상태바: "주간 6500K - 수동 스케줄" 같은 한 줄 요약. 실패 시 빨간 텍스트로 "적용 실패: <devices>".
  - 일시중지 배너: 트레이 "일시중지" 시 모드 바 아래에 노란 배너 "⏸ 일시중지됨 — 모든 모니터 정상색...". 재개 시 사라짐.
  - 창 X(`WM_DELETE_WINDOW`) 동작 변경: `root.withdraw()` (트레이 최소화). 첫 닫기 시 트레이 풍선 알림 1회.
  - 슬라이더 변경 콜백에서 `scheduler.cancel_transition()` 호출 — 보간 중에도 사용자 입력 즉시 우선.
  - 통합 객체: `Scheduler` + `Tray` 인스턴스를 `__init__`에서 생성. `run()`에서 `tray.start()`, `scheduler.start()`, `_fullscreen_tick()` 시작 후 `mainloop`. 트레이 "종료"가 유일한 실제 `reset_all` + `root.destroy` 지점.
  - `_on_external_mode_change(mode)` — 스케줄러 보간 완료 시 모드 라디오(`mode_var`) 동기화.
  - 시작 시 `engine.current_target_mode(now, cfg)`로 현재 시각의 모드 즉시 적용(보간 없이).
- `src/nightshift/schedule/engine.py` (위에서 설명) — `on_mode_change` 파라미터 cycle-02 검증 중 추가.

### 테스트 (33 → 66 green)
- `tests/test_schedule_engine.py` 18 케이스 — manual 표준/inverted 윈도우, astral 모킹, `next_transition` 시각, `interp_sequence` 길이/단조성/0스텝, `_kelvin_for_mode` 분기.
- `tests/test_autostart.py` 7 케이스 — `_command()` frozen/dev 분기, in-memory 백엔드로 register/is_registered/unregister round-trip, `sync_with_config`.
- `tests/test_fullscreen.py` 8 케이스 — `_rect_matches_monitor` 정확/톨러런스/오프셋 모니터, `is_fullscreen_app_visible`의 shell 필터/normal window/no rect 분기.
- 전체 **66 green** (cycle-00 13 + cycle-01 20 + cycle-02 33).

## 도중에 결정한 것
- 보간 K 시퀀스: 20스텝 + 250ms 간격 = 5초. 사용자 슬라이더 입력은 토큰 증가로 즉시 취소.
- 모드 라디오 자동 동기화: cycle-02 1차 구현 후 사용자 피드백 → `Scheduler.on_mode_change` 콜백 추가, `MainWindow._on_external_mode_change`로 `mode_var.set(target)`.
- 일시중지: cycle-02 1차 구현은 상태바 텍스트만 변경 → 사용자 피드백 → 노란 배너 추가(모드 바 아래, `pack(before=self.side)`).
- 스케줄 설정 저장: 1차 `<FocusOut>`/`<Return>` 트리거만 → 사용자 피드백 → 명시적 **"적용"** 버튼 추가 (Enter/포커스 아웃은 보조로 유지).
- 트레이 "야간 즉시": `controller.mode`을 미리 set하지 않고 보간 종료 시점의 `on_mode_change`에 맡김 → 모드 라디오 동기화와 일관.
- 전체화면 진입 시 controller.mode/targets는 그대로, `reset_all`로 임시 정상색만. 빠져나오면 `apply_current`로 복귀. 토글 OFF 중에도 동일 정리.

## 환경 / 명령
- `pip install -e .` 그대로(cycle-00에서 설치). 신규 deps 없음 (pystray/Pillow/astral은 cycle-00 requirements에 이미 있고 이번에 처음 사용).
- 실행: `python -m nightshift` (메인 윈도우 + 트레이 + 스케줄러 + 풀스크린 폴링 동시 시작).
- `python -m nightshift --diagnose`는 그대로 동작.
