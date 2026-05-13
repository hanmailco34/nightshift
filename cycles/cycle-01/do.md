# cycle-01 — Do: 작업 로그

## 만든 것 / 바꾼 것

### 신규 패키지
- `src/nightshift/config/` (`__init__.py`, `store.py`)
  - `load() / save() / default_config() / config_path() / ensure_monitor_entries()`. `%APPDATA%\nightshift\config.json`(없으면 `~/.nightshift/config.json`로 폴백). 부분 키만 있는 파일은 `default_config`과 재귀 머지 → 누락 키 채우고 사용자가 추가한 미지의 키도 보존. JSON 파싱 실패/빈 파일이면 기본값으로 폴백.
- `src/nightshift/platform/` (`__init__.py`, `registry.py`)
  - `read_gdi_icm_gamma_range() -> int | None`. `winreg.HKEY_LOCAL_MACHINE\...\ICM\GdiICMGammaRange` 읽기 전용. 쓰기는 절대 안 함(관리자 PS 명령은 사용자가 직접 실행).
- `src/nightshift/color/controller.py`
  - `Controller` 데이터클래스 + `from_config(cfg)`. 상태: `mode`, `extended_range`, `per_monitor_enabled`, `monitors`(device→{day_k, night_k}), `global_targets`.
  - `apply_current(devices)` — 현재 모드의 K를 각 device에 `gamma.apply_kelvin(d, k, clamp_to_windows_limit=not extended_range)`로 적용, 실패 device 리스트 반환. `OSError`도 실패로 집계.
  - `reset_all`, `set_mode`, `set_temperature`, `set_extended_range`, `set_per_monitor_enabled`.
  - `gamma.apply_kelvin` / `gamma.reset`을 **모듈 속성 접근**으로 호출 → 테스트가 `monkeypatch.setattr(gamma, ...)`로 가로채는 단일 진입점.
- `src/nightshift/ui/` (`__init__.py`, `main_window.py`)
  - `MainWindow` + `MonitorPage`(ttk.Frame). 상단 바: 모드 라디오(주간/야간), 개별 토글, 확장 토글. 본문: 개별ON이면 `ttk.Notebook` 탭(모니터별 페이지), 개별OFF면 단일 글로벌 페이지. 각 페이지: day/night 슬라이더(`tk.Scale`, resolution=50, length=420) + 미리보기 박스(`tk.Frame`, `kelvin_to_rgb`로 hex 배경색).
  - 슬라이더 드래그: 200ms `after` debounce → `controller.apply_current` → 라디오 모드 자동 전환. 슬라이더 `<ButtonRelease-1>`: pending debounce 취소·즉시 적용·`store.save` 저장.
  - 확장 토글 ON → `Toplevel` 모달(설명·현재 레지스트리 값 표시·PS 명령 텍스트·"명령 복사"/"취소"/"이미 설정함 + 재부팅 완료" 버튼). 확인 시 primary에 `apply_kelvin(primary, 2000, clamp_to_windows_limit=False)` 자가 진단 후 직전 상태 복원, 실패 시 토글 자동 OFF + 경고.
  - 종료(`WM_DELETE_WINDOW`): 모든 모니터 `reset` + `store.save` 후 `root.destroy`.

### 변경된 파일
- `src/nightshift/color/gamma.py`
  - `_apply_ramp_to_device(device, ramp)` 헬퍼로 ctypes 호출부 분리. `apply_kelvin(device_name, kelvin, brightness=1.0, clamp_to_windows_limit=True)` — 키워드 인자 추가, 기본값은 cycle-00 동작 보존. `reset()`도 헬퍼 사용.
- `src/nightshift/__main__.py`
  - 기본은 `ui.main_window.run()` 호출(메인 윈도우). `--diagnose`로 cycle-00의 모니터 열거 출력 유지.
- `cycles/cycle-01/plan.md` — 4가지 UX 결정사항(지금 적용 버튼 없음 / 개별OFF=탭 숨김 단일 페이지 / 확장 OFF 시 K값 보존 / 슬라이더=현재 모드 자동전환) 반영.

### 테스트
- `tests/test_gamma_ramp.py` — `apply_kelvin`이 `clamp_to_windows_limit`을 `build_gamma_ramp`에 정확히 전파(monkeypatch로 호출 인자 캡처).
- `tests/test_config_store.py` (10 케이스) — 기본값, 파일 부재→default, 라운드트립, 부분키 머지, 미지의 키 보존, schema_version 보존, JSON 깨짐→default, `ensure_monitor_entries`, `config_path` APPDATA/홈 폴백.
- `tests/test_controller.py` (9 케이스) — `apply_current`가 mode→K 매핑·`extended_range→clamp` 전파, 개별 ON/OFF 분기, 실패 device 리스트, OSError 집계, `from_config` 채움.
- 전체 33 green (cycle-00 14 + cycle-01 19).

## 도중에 고치거나 결정한 것
- `tk.Scale.set()`/`var.set()`이 `command` 콜백을 다시 트리거 → `MonitorPage._refreshing` 가드 플래그 도입(refresh 중에는 콜백 무시) → set_values가 controller에 역기록하지 않도록.
- 슬라이더 하한이 올라가도(예: 확장 OFF) `controller.monitors[d].night_k`는 그대로 보존(Tk의 Scale은 표시값만 클램프) → 다시 확장 ON 시 원래 K 복원되는 UX 확보.
- 자가 진단의 "직전 상태 복원"은 controller의 `target_for(primary)`로 직전 K 계산 후 `apply_kelvin`으로 즉시 되돌리는 방식. 확장 OFF 상태에서의 진단이면 복원도 클램프 ON으로 들어감.
- 첫 실행 시 `list_monitors()` 결과로 `monitors` 키가 비어있던 config에 entry 자동 추가(`ensure_monitor_entries`).

## 환경 / 명령
- `pip install -e .` (cycle-00에서 이미 설치) → `python -m nightshift`로 메인 윈도우, `python -m nightshift --diagnose`로 진단.
- 추가 의존성 없음(tkinter / winreg / json 모두 표준 라이브러리).
