# cycle-01 — Plan: UI + 모니터별 개별 설정 + 확장 색온도 범위

## 목표
tkinter 메인 창을 띄워 모니터별 day/night 색온도를 실시간 조절·저장하고, "확장 색온도 범위"(GdiICMGammaRange 우회) 옵트인 토글까지 도입한다. cycle-00의 `apply_kelvin`/`list_monitors`/`kelvin_to_rgb`를 그대로 사용. 스케줄·트레이·자동실행은 cycle-02로 미룬다.

## 범위 (In)
- `config/store.py`
  - 위치: `%APPDATA%\nightshift\config.json` (env `APPDATA` 없으면 `~/.nightshift/config.json`로 폴백).
  - 스키마(JSON):
    ```jsonc
    {
      "schema_version": 1,
      "per_monitor_enabled": false,             // 개별 설정 토글
      "global": { "day_k": 6500, "night_k": 3300 },
      "monitors": {                              // key = device_name e.g. "\\\\.\\DISPLAY1"
        "\\\\.\\DISPLAY1": { "day_k": 6500, "night_k": 3300 }
      },
      "schedule": { "manual": true, "night_start": "21:00", "day_start": "07:00" },
      "location": { "lat": 37.5665, "lon": 126.9780 },  // 기본 서울
      "toggles": { "autostart": false, "use_sunset": false, "disable_on_fullscreen": true },
      "extended_range": false                    // 확장 색온도 범위 (옵트인)
    }
    ```
  - API: `load() -> Config`, `save(cfg)`, `default()`, 누락 키 기본값 머지(향후 마이그레이션 여지).
- `ui/main_window.py` (tkinter):
  - 레이아웃:
    - **개별 ON** → 모니터별 `ttk.Notebook` 탭(`Monitor N - <model> (<WxH>)`), 각 탭에 day/night 슬라이더 1쌍 + 미리보기 박스 2개.
    - **개별 OFF** → 탭 영역 자체를 숨기고 글로벌 단일 페이지(day/night 슬라이더 1쌍 + 미리보기 박스 2개)만 표시. global값으로 모든 모니터 동기 적용.
  - 슬라이더 범위는 `extended_range`에 따라 동적 — 끔: 3300~6500K / 켬: 1500~6500K. **확장 OFF로 되돌릴 때 config의 K값은 보존**(슬라이더 표시 하한만 3300K로 잠금, 다시 ON 시 1500K 복원).
  - 우측 사이드 카드: 현재 모드(주간/야간) 라디오·"확장 색온도 범위" 토글·"개별 설정" 토글. 스케줄/트레이/자동실행 UI는 자리만 disabled로 두고 cycle-02에서 채움.
  - **"지금 적용" 버튼 없음** — 슬라이더 드래그 = 실시간 적용. 200ms debounce 후 `apply_kelvin`. 슬라이더 release(`<ButtonRelease-1>`) 시 config 저장.
  - **슬라이더 만지면 현재 모드 자동 전환** — night 슬라이더 드래그하면 모드 라디오가 night로 바뀌고 화면도 night K로 즉시 반영. day 슬라이더도 동일.
- `color/controller.py` (얇은 오케스트레이션)
  - 상태: `mode: Literal["day","night"]`, `extended_range: bool`, 모니터별 day/night 목표값.
  - 메서드: `apply_current()` — 현재 모드·각 모니터 목표값으로 `apply_kelvin(device, k, clamp_to_windows_limit=not extended_range)` 호출, 실패 모니터 리스트 반환.
  - 메서드: `set_mode(mode)`, `set_temperature(device, mode, k)`, `set_extended_range(bool)`.
- 확장 색온도 범위 UX
  - 토글 OFF → 클램핑 ON, 슬라이더 하한 3300K (config의 K값은 보존).
  - 토글을 처음 ON으로 바꿀 때: 모달 다이얼로그(`tkinter.Toplevel`)
    1. 설명: "더 따뜻한 색(~1500K까지) 사용하려면 1회 시스템 설정과 Windows 재부팅이 필요합니다. f.lux 등도 동일한 방식입니다."
    2. 현재 레지스트리 상태 표시(`platform.registry.read_gdi_icm_gamma_range()` 결과 — `미설정` / `256` / 기타 값).
    3. 두 버튼: **"관리자 PowerShell 명령 복사"**(클립보드에 `Set-ItemProperty -Path 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\ICM' -Name GdiICMGammaRange -Value 256 -Type DWord` 복사) / **"이미 설정함 + 재부팅 완료"** 확인.
    4. 확인 후 자가 진단: 현재 primary 모니터 상태 백업 → `apply_kelvin(primary, 2000, clamp_to_windows_limit=False)` 짧게 적용(500ms 이내) → 성공/실패 즉시 직전 상태로 복원. 성공이면 토글 활성 확정·config 저장, 실패면 토글 자동 OFF + 사유 표시.
  - 토글 OFF로 되돌리기는 즉시 가능(재부팅·관리자 권한 불필요). config의 K값은 변경하지 않음.
- `platform/registry.py` — `read_gdi_icm_gamma_range() -> int | None`(`winreg` HKLM 읽기 전용). 쓰기는 사용자 본인이 관리자 PS로 실행.
- `__main__.py` — 진단 출력 대신 메인 윈도우 띄우도록 교체(`--diagnose` 플래그로 기존 출력 유지).
- 인터페이스 변경 (cycle-00 → cycle-01)
  - `color.gamma.apply_kelvin(device_name, kelvin, brightness=1.0, clamp_to_windows_limit=True) -> bool` — 키워드 인자 추가, 기본값은 cycle-00 동작 보존.
- 단위 테스트
  - `tests/test_gamma_ramp.py` 회귀: `apply_kelvin`이 `clamp_to_windows_limit`을 `build_gamma_ramp`에 전파.
  - `tests/test_config_store.py` — 기본값 생성, 라운드트립, 부분 키 누락 시 머지, schema_version 보존.
  - `tests/test_controller.py` — `apply_current` 가 mode에 따라 올바른 K를 monkeypatched `apply_kelvin`에 전달, `extended_range` 가 `clamp_to_windows_limit`로 전파됨.
  - UI는 자동 테스트 제외(수동 검증).

## 범위 (Out — cycle-02 이후)
- 시스템 트레이(`pystray`), 자동 모드 전환 스케줄러, `astral` 일몰/일출, 자동실행(`HKCU\...\Run`), 전체화면 감지, 모드 전환 보간(slew). 슬라이더는 즉시 적용으로 충분.

## 검증 기준
1. `python -m pytest -q` 전부 green (cycle-00 + cycle-01 신규 테스트).
2. `python -m nightshift` 실행 → 모니터 3대 탭이 뜨고, primary 탭에서 야간 슬라이더를 3300K로 내리면 즉시 화면이 따뜻해짐. 다른 모니터는 그대로.
3. "모니터별 개별 설정" 끈 상태에서 global 야간을 3300K로 바꾸면 세 모니터 모두 같이 따뜻해짐.
4. 창을 닫고 다시 띄워도 슬라이더 값·토글 상태가 복원됨(`config.json` 반영 확인).
5. "확장 색온도 범위" 토글 ON → 안내 다이얼로그가 뜸. 현재 PC는 레지스트리가 이미 256이고 재부팅됨 → "이미 설정함" 버튼 → 자가 진단 통과 → 슬라이더 하한이 1500K로 확장 → 1500K 적용 시 시각적으로 깊은 주황빛.
6. 토글 OFF로 되돌리면 즉시 슬라이더 하한 3300K로 복귀.
7. 종료 시(창 닫기) `reset` 호출돼 모든 모니터 항등 램프로 복원. (cycle-02 트레이가 추가되면 동작 달라짐 — 그때 재검토.)

## 리스크 / 미정
- tkinter 슬라이더의 실시간 드래그 성능(3대 모니터 동시 `apply_kelvin` × debounce 200ms) — 충분할 것으로 봄. 안되면 슬라이더 release시에만 apply로 후퇴.
- 자가 진단 실패(다른 GPU에서 GdiICMGammaRange 무효) 케이스 → 토글 자동 OFF + 사용자에게 사유 표시.
- HDR 모니터에서 `apply_kelvin` 실패 → `controller.apply_current()` 반환값으로 UI에 표시.

## 산출 (이 사이클 종료 시 채워질 것)
- `do.md`: 실제 작업 로그.
- `check.md`: 위 7가지 검증 결과 + 발견 이슈.
- `act.md`: cycle-02(스케줄/트레이/자동실행) 착수 항목 + 인터페이스 확정.
- `CLAUDE.md` 사이클 로그에 한 줄 추가.
