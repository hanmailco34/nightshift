# cycle-04 — Do: 작업 로그

## 만든 것 / 바꾼 것

### config 스키마 v2 (`src/nightshift/config/store.py`)
- `SCHEMA_VERSION = 2`.
- 신규 필드:
  - `mode` (`"day"|"night"|"single"`) — 현재 controller mode를 영구 저장.
  - `global.single_k` / `monitors[device].single_k` — 단일 모드 K (기본 3300).
  - `presets`: `[{name, default_k, kelvins}]` — 빌트인 4개 시드 ("주광 6500K / 할로겐 3400K / 백열등 2700K / 촛불 1900K"). `default_k`는 device-별 K가 없을 때의 폴백.
- `_migrate_v1_to_v2(cfg)` — `_merge`가 default에서 v2 키들(global.single_k, presets, mode)을 채워준 뒤, v1 monitors entry들에 누락된 `single_k`만 backfill하고 schema_version=2 표기. v2 cfg에는 no-op.
- `ensure_monitor_entries`도 신규 device에 single_k 자동 세팅.
- `save()`는 UTF-8 + `ensure_ascii=False`로 한글 프리셋명을 깨지지 않게.

### color/controller.py — 단일 모드 + visual floor
- `Mode = Literal["day", "night", "single"]`.
- `global_targets` 기본값에 `single_k=3300` 추가.
- `target_for(device)`는 그대로 — `f"{mode}_k"` 키 기반이라 single 자동 분기.
- **신규**: `CLAMPED_VISUAL_FLOOR_K = 3300`, `UNCLAMPED_VISUAL_FLOOR_K = 1500`, `controller.visual_floor()`, `controller.effective_target_for(device)`. `apply_current`가 effective(=floored) K를 `gamma.apply_kelvin`에 전달.
- `from_config(cfg)`가 cfg.mode / single_k 모두 읽어 controller에 반영.

### schedule/engine.py — single 모드 evaluate skip
- `Scheduler._evaluate_once`: `controller.mode == "single"`이면 즉시 return — 자동 day/night 전환 안 함.

### ui/main_window.py — 모드 라디오 / 동적 슬라이더 / 프리셋 영역
- 상단 모드 라디오: "주간 / 야간 / **단일**" 3개. mode 변경 시 `controller.set_mode` + `_refresh_pages` + `_refresh_next_label_now` + `_apply_now` + `_save`.
- `MonitorPage` 재작성:
  - 생성자가 `current_mode`를 받아 `mode="single"`이면 single 슬라이더 1개, 아니면 day+night 슬라이더 2개를 빌드.
  - `_build_section(which, ...)` 팩토리로 day/night/single 섹션을 동일 코드로 생성.
  - `set_values(day_k, night_k, single_k)` — **IntVar에는 raw K, 라벨/미리보기는 max(scale.from_, raw)**로 floored 표시 (UI 표시가 OS 출력과 일치).
- 본문 레이아웃 변경: `self.body` 안에 `pages_area`(상단·확장) + `presets_area`(하단·고정).
- `presets_area` (`ttk.LabelFrame "프리셋"`):
  - 빌트인/사용자 프리셋을 4열 grid 칩 버튼으로 표시 + 끝에 **"+ 저장"** 버튼.
  - 우클릭(`<Button-3>`) → context menu (이름 변경 / 삭제).
  - `_is_preset_enabled(p)`: 확장 OFF면 K가 하한(3300) 미만인 프리셋은 disabled로 회색.
  - `_apply_preset(p)`: 현재 mode K에 default_k 또는 per-device 값으로 controller.set_temperature 호출 → apply_current.
  - `_save_preset_dialog`: `simpledialog.askstring`로 이름 입력 → 현재 모니터별 raw K를 스냅샷 → cfg.presets 추가 → save + refresh + tray sync.
  - `_rename_preset` / `_delete_preset`: 이름 중복 검사, 삭제 확인 다이얼로그.
- `_save()`: `self.cfg["mode"] = self.controller.mode` 포함.
- `_refresh_status`: mode 라벨 "주간/야간/단일" 매핑, `controller.effective_target_for(primary)` 사용. single 모드일 때 "자동 전환 안 함" 표기.
- `_refresh_next_label_now`: single 모드면 "(단일 모드 — 스케줄 사용 안 함)" 표시.
- 시작 시 mode==single이면 `engine.current_target_mode`로 덮어쓰지 않음 — 사용자 선택 보존.
- `_on_external_mode_change` (스케줄러 보간 끝): `_refresh_pages` 호출 추가 — mode 전환 시 슬라이더 레이아웃도 갱신.
- `_tray_toggle_pause` resume 시 mode==single이면 자동 모드 변경 안 함.
- `_on_extended_change`: 확장 OFF/ON 시 `_refresh_presets` + `tray.update_presets()` 호출 — 칩/서브메뉴의 disabled 상태 즉시 갱신.

### ui/tray.py — 프리셋 서브메뉴
- 생성자에 `on_apply_preset` / `get_presets` 추가.
- `_build_menu`가 `get_presets()` 결과를 받아 "프리셋" 서브메뉴 구성. 각 entry가 `(name, enabled)` tuple이면 `MenuItem(enabled=...)`로 disable 반영.
- `update_presets()`: 메뉴 재빌드 + `Icon.update_menu()` 호출.

### 테스트 추가
- `tests/test_config_store.py`: v1→v2 자동 마이그레이션, single_k backfill, 빌트인 프리셋 시드, 라운드트립, v2 cfg 재마이그레이션 안 함 (+4 케이스 = 14).
- `tests/test_controller.py`: single 모드 target_for / per-monitor override / set_temperature, from_config가 mode/single_k 읽음, apply_current가 single_k 적용, **visual floor가 확장 OFF에서 작용/확장 ON에서 통과** (+7 케이스 = 16).
- `tests/test_schedule_engine.py`: single 모드에서 `_evaluate_once`가 transition 호출 안 함, day/night에서는 호출 (+2 케이스 = 20).
- 신규 13 케이스. 총 **79 green** (cycle-00 13 + cycle-01 20 + cycle-02 33 + cycle-04 13).

## 도중에 발견·고친 것 (사용자 피드백 2건)

### 1) 확장 OFF인데 백열등/촛불 프리셋이 클릭 가능했던 버그
사용자 보고: "확장 색온도 범위가 아닌데 프리셋 때문에 백열등과 촛불이 선택돼".
원인: 프리셋 적용 시 controller에 raw K(2700/1900)를 그대로 써넣어, 슬라이더가 3300K 하한으로 잠긴 상태와 불일치.
수정: `_is_preset_enabled(p)`로 확장 OFF면 K가 하한 미만인 프리셋 칩을 `state="disabled"` (회색)으로 표시. 트레이 서브메뉴도 동일 — `get_presets()`가 `[(name, enabled), ...]` 튜플을 반환하도록 변경, `Tray._build_menu`가 `MenuItem(enabled=...)`로 반영.

### 2) 1900K 프리셋 후 확장 OFF로 토글해도 화면 색이 안 변하던 버그
사용자 보고: "촛불에서 내가 확장색 온도 범위를 껐는데 색은 변하지 않아".
디버그 print로 추적: controller가 K=1900을 `gamma.apply_kelvin(d, 1900, clamp=True)`로 정확히 전달 + `apply_current` 성공(failed=[]). 하지만 우리 `build_gamma_ramp`의 클램프(±32000 deviation)는 ramp 엔트리만 잘라낼 뿐 시각적으로 "정확히 3300K"가 되지 않음 — K=1900 입력 시 빨강 100% / 초록 51% / 파랑 51% = 살구색이 나오고, 사용자는 "여전히 따뜻 = 안 변함"으로 인지.
근본 원인: cycle-01에서 도입한 "raw K 보존 + 슬라이더 하한만 3300K로 잠금" 정책의 빈 구멍 — 사용자가 보는 슬라이더 값(3300K)과 화면(살구색)이 어긋남.
수정: `controller.visual_floor()`와 `effective_target_for()` 도입. `apply_current`가 raw K가 아닌 `max(floor, raw)`를 OS에 전달. raw K는 controller.monitors에 그대로 보존(확장 ON 토글 시 즉시 복원됨). UI 라벨/미리보기도 floored K를 표시해 일관성 확보.

## 환경 / 명령
- 추가 의존성 없음.
- 실행: `python -m nightshift`. 단위테스트: `python -m pytest -q` → 79 green.
- 디버그 print는 사후 모두 제거.
