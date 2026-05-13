# nightshift — 개발 기록 (CLAUDE.md)

Windows 멀티모니터 색온도 제어 앱 (f.lux 클론). Python + tkinter, PyInstaller 단일 exe(≤40MB)로 빌드해 GitHub Releases 배포.

## 작업 방식 — PDCA 사이클
- 모든 작업은 `cycles/cycle-NN/` 단위로 진행. 각 폴더에 `plan.md`(목표·범위·검증기준) → `do.md`(작업 로그) → `check.md`(검증 결과·발견 이슈) → `act.md`(다음 사이클 반영)를 채운다.
- 사이클 종료 시: 이 파일의 "사이클 로그"에 한 줄 추가 + 커밋(작성자 `hanmailco34 <hanmailco34@naver.com>`, 이 레포 로컬 git config에 설정됨).
- 다음 사이클은 직전 `act.md`의 "착수 항목"에서 시작.

## 프로젝트 구조
```
src/nightshift/
  __init__.py            # 버전, Kelvin 상수
  __main__.py            # 엔트리포인트(기본=UI+트레이+스케줄러, --diagnose=모니터 진단). **absolute import** (PyInstaller 호환).
  color/
    temperature.py       # kelvin_to_rgb(k) -> (r,g,b) 배율 (Tanner Helland)
    gamma.py             # build_gamma_ramp / identity_ramp / apply_kelvin (clamp_to_windows_limit) / reset + CLI
    controller.py        # Controller(day/night/single) + visual_floor/effective_target_for + from_config
  display/monitors.py    # list_monitors() -> [Monitor], find_by_device()
  config/store.py        # load/save/default_config/ensure_monitor_entries + schema v2(mode/single_k/presets) + v1→v2 자동 마이그레이션
  schedule/engine.py     # Scheduler(데몬 스레드, 30s tick, 5s 보간) + current_target_mode/next_transition (manual/astral)
  platform/
    registry.py          # GdiICMGammaRange 읽기 전용 (winreg)
    autostart.py         # HKCU\...\Run 등록/해제, sync_with_config
    fullscreen.py        # is_fullscreen_app_visible (GetForegroundWindow + 모니터 rect 매칭)
  ui/
    main_window.py       # tkinter 메인 + 모드 라디오(주간/야간/단일) + 동적 슬라이더 + 프리셋 칩 영역(저장·이름변경·삭제) + 사이드 카드 + 상태바 + 일시중지 배너 + 확장 모드 다이얼로그
    tray.py              # pystray 트레이(열기/일시중지/야간 즉시/프리셋 ▶/종료)
tests/                   # pytest (temperature, gamma ramp, config, controller, schedule engine, autostart, fullscreen)
cycles/cycle-NN/         # plan/do/check/act
scripts/
  probe_unclamped.py     # GdiICMGammaRange 시각 확인 진단
  make_icon.py           # assets/nightshift.ico 재생성 (Pillow 16/32/48/256)
assets/nightshift.ico    # exe + 윈도우 아이콘 (make_icon.py 출력 커밋)
nightshift.spec          # PyInstaller 6.x spec (onefile, windowed)
.github/workflows/release.yml  # v*.*.* 태그 푸시 시 windows-latest 자동 빌드 + Releases 업로드
```

## 개발 셋업
- `pip install -e .` + `pip install -r requirements-dev.txt` (PyInstaller 포함) → `python -m nightshift` (메인 윈도우 + 트레이), `python -m nightshift --diagnose` (모니터 진단), `python -m nightshift.color.gamma --help` (CLI 스모크).
- `python -m pytest`
- 빌드: `python scripts/make_icon.py` (아이콘 변경 시) → `pyinstaller --clean --noconfirm nightshift.spec` → `dist/nightshift.exe` (~32 MB).
- 릴리스: `pyproject.toml` 버전 업데이트 → `git tag v0.X.Y && git push origin v0.X.Y` → GitHub Actions가 자동 빌드 + Releases 업로드.

## 핵심 제약 (cycle-00에서 실측 — `cycles/cycle-00/check.md` 참고)
- 색온도 제어 = GPU 감마 램프(`SetDeviceGammaRamp`). Windows는 선형에서 ±0x8000 넘게 벗어난 램프를 거부 → **기본 상태 시각적 하한 ≈ 3300K**.
- `HKLM\...\ICM\GdiICMGammaRange=256` + **실제 Windows 재부팅** 시 그 제한이 풀려 1500K까지 시각 적용 확인됨(`scripts/probe_unclamped.py`로 재현). 관리자 권한·재부팅 필요 → 일반 사용자에겐 강요 안 함.
- 채택안 (**C**): 기본은 클램핑(`apply_kelvin` 항상 성공, ≈3300K에서 효과 포화). 옵션으로 **"확장 색온도 범위"** 토글 — 활성화 시 안내 다이얼로그 → 관리자 권한으로 레지스트리 설정 + 재부팅 안내 → 이후 클램핑 끄고 풀범위 사용. (cycle-01에서 구현)
- `SetDeviceGammaRamp`/`apply_kelvin` 반환값(성공/실패)을 항상 확인할 것 (HDR/드라이버 거부 가능).

## 사이클 로그
- **cycle-00** (색온도 제어 PoC) — 레포 스캐폴딩 + temperature/gamma/monitors 구현 + 단위테스트 11 green. 모니터 3대 열거 OK, 색온도 적용 OK(단 ≥~3300K), Windows 감마 클램프 제약 발견·문서화. → 다음: cycle-01 UI + config + 모니터별 개별 설정.
- **cycle-01** (UI + config + 확장 색온도 범위) — config/store, platform/registry, color/controller, ui/main_window 구현 + `apply_kelvin`에 `clamp_to_windows_limit` 키워드 인자 추가. tkinter 메인 윈도우(개별ON=탭, 개별OFF=글로벌 단일 페이지, day/night 슬라이더 + 미리보기, 슬라이더=현재 모드 자동전환). 확장 색온도 범위 옵트인 토글(레지스트리 안내 다이얼로그 + 자가 진단). 단위테스트 33 green, 실 PC 7항목 수동 검증 통과. → 다음: cycle-02 스케줄/트레이/자동실행/전체화면감지.
- **cycle-02** (스케줄 + 트레이 + 자동실행 + 전체화면 감지) — schedule/engine(Scheduler 데몬 스레드, 30s tick, 5초 20스텝 K 보간, manual/astral 모드, `on_mode_change` 콜백), platform/autostart(HKCU Run), platform/fullscreen(GetForegroundWindow rect 매칭), ui/tray(pystray, 4메뉴) 추가. ui/main_window 보강 — 사이드 카드(스케줄+위/경도+적용버튼/자동실행/기타 토글), 일시중지 노란 배너, 하단 상태바, 창 X = 트레이 최소화, 슬라이더 입력 시 보간 즉시 취소. 단위테스트 66 green(+33), 실 PC 7항목 수동 검증 통과 + 사용자 피드백 3건(적용 버튼/일시중지 배너/모드 라디오 동기화) 반영. → 다음: cycle-03 PyInstaller onefile 빌드 + GitHub Releases.
- **cycle-03** (PyInstaller onefile + GitHub Releases) — scripts/make_icon.py + assets/nightshift.ico(16/32/48/256 멀티사이즈 노란 디스크), nightshift.spec(PyInstaller 6, onefile windowed, hiddenimports pystray._win32/PIL._tkinter_finder, excludes astral.geocoder/tkinter.test 등, upx=False), .github/workflows/release.yml(v*.*.* 태그 푸시 시 windows-latest 자동 빌드 + softprops/action-gh-release@v2 업로드), README 보강(Download/SmartScreen 안내/빌드 명령). `__main__.py`의 relative import → absolute로 교체(PyInstaller가 entry 모듈을 패키지 컨텍스트 없이 실행하는 함정). 첫 빌드 8MB가 알고 보니 import 실패한 stub였고 패치 후 진짜 31.58MB(40MB 한계의 79%). 회귀 통과, 단위테스트 66 green 유지. → v0.1.0 릴리스 (GitHub Actions로 자동 빌드 + nightshift.exe 첨부).
- **cycle-04** (단일 모드 + 프리셋) — config schema v2(`mode`, `global.single_k`, `monitors[d].single_k`, `presets`) + v1→v2 자동 마이그레이션. controller에 `Mode = Literal["day","night","single"]` + `visual_floor()` / `effective_target_for()`(raw K는 보존하면서 OS에는 `max(floor, raw)`만 전달). schedule.engine은 mode=="single"일 때 evaluate skip. ui/main_window: 모드 라디오에 "단일" 추가, MonitorPage가 mode별로 day+night 슬라이더 vs single 슬라이더 1개를 동적 빌드, 본문 하단에 프리셋 칩 영역(빌트인 4개 시드 + "+ 저장"/우클릭 컨텍스트로 이름 변경·삭제), 라벨/미리보기가 floored K 표시(슬라이더 thumb과 일치). ui/tray: 메뉴에 "프리셋 ▶" 서브메뉴(`Icon.update_menu`로 동적). 사용자 피드백 2건 반영: 확장 OFF 시 K<3300 프리셋 disabled, 확장 OFF 토글 후 화면이 실제로 ~3300K로 변하도록 visual floor 도입. 단위테스트 79 green(+13). → 다음: cycle-05 후보(프리셋 export/import, 단축키, 코드 사이닝 등).
