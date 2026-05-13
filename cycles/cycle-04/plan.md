# cycle-04 — Plan: 단일 모드 + 프리셋

## 목표
사용자 요청 2건 반영:
1. **시간 분기 없이** 하나의 K로 항상 사용하는 "단일" 모드.
2. **모드별 클릭**으로 간편하게 적용하는 프리셋(Reading / Movie / Candle 같은) — 모니터별 K 맵을 저장하고 한 번에 적용.

cycle-00~03의 인터페이스는 가능한 한 보존하면서 mode 도메인을 `"day"|"night"`에서 `"day"|"night"|"single"`로 확장하고 프리셋 영역을 추가.

## UX 결정 (사용자 확정)
- **단일 모드**: 상단 모드 라디오 "주간 / 야간" 옆에 **"단일"** 추가. 선택 시 모니터 페이지의 슬라이더가 **single 1개**로 동적 변경, 스케줄러 자동 전환 비활성.
- **프리셋 단위**: **모니터별 K 맵** 스냅샷 (현재 각 모니터의 *현재 mode* K 묶음). 클릭 시 각 device의 현재 mode K에 그 맵을 덮어쓰고 `apply_current`.

## 범위 (In)

### `config/store.py` — 스키마 v2 + 마이그레이션
- `SCHEMA_VERSION = 2`.
- `default_config()`:
  - `mode`: `"day"` (controller의 mode를 config에도 영구 저장).
  - `global`: `{day_k: 6500, night_k: 3300, single_k: 3300}` (single_k 신규).
  - `monitors[device]` 항목: `{day_k, night_k, single_k}` (single_k 신규).
  - `presets`: `[{name, kelvins: {device: k}}]` — 시드 4개:
    - `"주광 (6500K)"` / `"할로겐 (3400K)"` / `"백열등 (2700K)"` / `"촛불 (1900K)"` (모든 device에 동일 K).
- `_merge`가 미존재 키를 default로 채워주므로 single_k는 자동 채움. presets는 별도 마이그레이션 헬퍼:
  - `load()` 호출 결과의 `schema_version`이 2 미만이면 `_migrate_v1_to_v2(cfg)` 적용 후 저장. presets 시드는 빈 배열일 때만 채움(사용자가 의도적으로 비워둔 경우 보존하지 않아도 됨 — 첫 마이그레이션에선 항상 시드).
- `ensure_monitor_entries`는 single_k도 자동 채움.

### `color/controller.py` — single 모드
- `Mode = Literal["day", "night", "single"]`.
- `target_for(device_name)`: `key = f"{self.mode}_k"` 그대로 작동 (single 시 `single_k` 자연 분기). 단, 빈 monitors entry에서 `global_targets["single_k"]` 폴백.
- `set_temperature(device, target_mode, kelvin)`: target_mode 검증 시 single 허용.
- `from_config(cfg)`: cfg.global.single_k / cfg.monitors[*].single_k 채움. cfg.mode가 있으면 controller.mode에 반영.
- `apply_current(devices)`: 변경 없음 (target_for가 알아서 single_k 반환).

### `schedule/engine.py` — single 모드 evaluate skip
- `Scheduler._evaluate_once`: `self.controller.mode == "single"`이면 즉시 return (자동 전환 안 함).
- 다른 부분은 그대로 — `current_target_mode`/`next_transition`은 시간 기반이라 day/night만 반환. UI의 "다음 전환 hh:mm" 라벨은 단일 모드일 때 숨기거나 회색으로.
- `begin_transition_now(target)`는 그대로 (트레이 "야간 즉시"는 단일 모드에서도 동작 — target을 "night"으로 명시).

### `ui/main_window.py` — 모드 라디오 + 동적 슬라이더 + 프리셋 영역
- 상단 모드 라디오:
  - "주간 / 야간 / **단일**" 3개. 변경 시 `controller.set_mode`, `_refresh_pages`(슬라이더 재구성), `_apply_now`, `_save`.
- `MonitorPage`:
  - 기존 day/night 슬라이더 빌드 + **single 슬라이더** 빌드해서 보관.
  - 새 메서드 `set_visible_mode(mode)` — mode가 "single"이면 single 슬라이더만 `grid`, 아니면 day/night 슬라이더만.
  - 또는 `_refresh_pages` 재호출 시 mode를 받아 페이지를 다른 형태로 빌드 (single용 페이지 vs day/night용 페이지) — 단순.
- **프리셋 영역**: 사이드 카드 아래 또는 본문 하단에 `ttk.LabelFrame("프리셋")`.
  - 칩은 `ttk.Button`으로 표현, `grid`로 wrap 레이아웃 (행 채우면 다음 행).
  - 각 칩 좌클릭 → 적용 (`controller.set_temperature` 각 device에 + `apply_current`).
  - 각 칩 우클릭 → `tk.Menu` 컨텍스트 (이름 변경 / 삭제).
  - 끝에 **"+ 저장"** 버튼 → `simpledialog.askstring`으로 이름 → 현재 모니터들의 현재 mode K를 스냅샷.
- 프리셋 적용 device 누락 처리: 프리셋 K 맵에 없는 device는 그대로 둠 (덮어쓰기 안 함).
- 프리셋 영역 갱신 시 `tray.update_presets(new_list)` 호출(트레이 메뉴 동기화).
- 단일 모드일 때 사이드 카드의 스케줄 그룹은 회색(`disabled` 모양)으로 — 의미 없음 안내. (간단히 LabelFrame 텍스트 옆에 "(단일 모드 — 비활성)" 추가).

### `ui/tray.py` — 프리셋 서브메뉴
- `Tray.__init__`에 `get_presets: Callable[[], list[str]]`, `on_apply_preset: Callable[[str], None]` 추가.
- 메뉴: 열기 / 일시중지 / 야간 즉시 / **프리셋 ▶** / 종료.
- 서브메뉴 구성은 `pystray.Menu(lambda: ...)`로 lazy하게 매번 호출 — `Icon.update_menu()` 안 불러도 트레이 클릭 시 최신 목록.
- `update_presets(names)` 메서드 — 명시적 갱신 트리거가 필요한 경우 `self.icon.update_menu()` 호출.

### 테스트
- `tests/test_config_store.py`:
  - `default_config()`에 single_k / presets / mode 필드 있음.
  - v1 cfg(json) load → v2로 마이그레이션, presets 시드, schema_version=2.
  - 라운드트립.
  - presets는 사용자가 비워도 다음 load에 다시 시드되지 않음 (마이그레이션은 schema_version 검사로 1회만).
- `tests/test_controller.py`:
  - `from_config`가 single_k 읽음.
  - `mode="single"`에서 `target_for`가 single_k 반환.
  - `set_temperature(device, "single", k)`가 single_k 갱신.
- `tests/test_schedule_engine.py`:
  - `Scheduler._evaluate_once`가 controller.mode=="single"이면 `_begin_transition` 호출 안 함 (monkeypatched gamma.apply_kelvin 호출 0회).

신규 ~10 케이스 → 총 ~76 green 목표.

## 범위 (Out — cycle-05 이상)
- 프리셋 export/import.
- 키보드 단축키.
- 프리셋별 자동 트리거(앱 포커스 등).
- 코드 사이닝.

## 검증 기준
1. `python -m pytest -q` 전부 green.
2. 모드 라디오에 "단일" 보임, 선택 시 슬라이더가 1개로 변경 (single).
3. 단일 모드에서 `schedule.night_start`를 임시로 현재+1분으로 두어도 1분 후 자동 전환 **안 일어남**.
4. 프리셋 영역에 빌트인 4개 칩 보임 → "할로겐 (3400K)" 클릭 → 모든 모니터 즉시 3400K (현재 mode K 갱신).
5. "+ 저장" → 이름 입력 → 현재 K 맵으로 저장 → 새 칩 등장.
6. 칩 우클릭 → 삭제 → 사라짐, config 영구 반영.
7. 트레이 "프리셋" 서브메뉴 동일 목록 → 클릭 시 동작.
8. 재실행 시 mode / 프리셋 / single_k 복원, v1 config가 있었다면 자동 v2 마이그레이션.

## 리스크 / 미정
- pystray 메뉴 lambda 동적 갱신이 안정적인지 — 안되면 `Icon.update_menu()` 명시 호출 폴백.
- 프리셋 device 키 불일치(모니터 교체) — 누락 device는 그대로 둠 (no-op) 폴리시 명시.
- v1 마이그레이션 단위 테스트 단단히.
- 단일 모드일 때 트레이 "야간 즉시"가 mode를 night로 바꿔버림 — 의도된 동작(즉시 명시적 야간). 단일 모드로 돌아오려면 라디오 다시 단일로.

## 산출
- `do.md` / `check.md` / `act.md`
- `CLAUDE.md` 사이클 로그 한 줄
- 커밋 (+ 사용자 결정 시 `v0.2.0` 태그)
