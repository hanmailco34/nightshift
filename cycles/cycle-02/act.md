# cycle-02 — Act: 다음 사이클 반영사항

## 결정 / 확정된 인터페이스
1. **`schedule.engine.Scheduler(controller, get_devices, root, get_cfg, *, on_mode_change=None, interp_steps=20, interp_duration_ms=5000, tick_seconds=30)`** — 보간 끝나면 `on_mode_change(target)` 호출. cycle-03에서 동일 시그니처 유지.
2. **순수 함수**: `engine.current_target_mode(now, cfg) -> "day"|"night"`, `engine.next_transition(now, cfg) -> datetime`, `engine.interp_sequence(start_k, end_k, steps) -> [int]`. UI 외 다른 곳에서도 재사용 가능.
3. **`platform.autostart`**: `is_registered/register/unregister/sync_with_config(cfg)`. PyInstaller 빌드 시 `sys.frozen=True`로 분기되어 exe 경로 등록.
4. **`platform.fullscreen.is_fullscreen_app_visible(monitors)`** — UI가 300ms 후 타이머로 폴링. 더 정교한 감지(특정 프로세스 화이트리스트 등)는 사용자 피드백 받고 후속 검토.
5. **`ui.tray.Tray(on_open, on_toggle_pause, on_night_now, on_quit, is_paused)`** — pystray 의존성. PyInstaller `--collect-data pystray` 또는 hidden-import 검토 필요.
6. **UI 정책**: 창 X = 트레이 최소화(처음만 풍선 알림). 트레이 "종료"가 유일한 reset 지점. 일시중지는 노란 배너 + 상태바 + 트레이 메뉴 체크박스 3중 표시.

## cycle-03 착수 항목
- **`nightshift.spec`** (PyInstaller)
  - `--onefile --windowed` 베이스. `windowed`로 콘솔창 숨김.
  - `hiddenimports`: `pystray._win32` (pystray 백엔드), `PIL._tkinter_finder`, `astral` 서브모듈.
  - `excludes`: `tkinter.test`, `PIL.ImageTk`(필요 시 검토), 불필요한 PIL 플러그인, `numpy`/`pandas`(설치 안 됐겠지만 방어), `astral.geocoder`(도시명 데이터 — 우린 lat/lon만 씀, 사이즈 큼).
  - 아이콘: `.ico` 리소스를 `--icon=...` 로 임베드. 디자인: 노란 디스크 또는 초승달.
  - 목표 크기: **≤40MB**. 첫 빌드 측정 후 exclude 폭증.
- **`.github/workflows/release.yml`**
  - Trigger: 태그 `v*.*.*` 푸시.
  - Windows-latest runner → `pip install -r requirements-dev.txt` → `pyinstaller nightshift.spec` → `actions/upload-release-asset` 또는 `softprops/action-gh-release`로 `dist/nightshift.exe` 업로드.
  - SmartScreen 경고: 코드 사이닝 없이 배포 → README에 "Windows가 알 수 없는 게시자 경고를 띄울 수 있음, 자세한 정보 → 실행" 안내.
- **README 보강**
  - 스크린샷 1~2장(메인 윈도우 / 트레이 메뉴).
  - 사용법: 다운로드 → exe 실행, 초기 설정 흐름.
  - 제약: 야간 모드 충돌, HDR, GdiICMGammaRange 안내.
  - 다운로드 링크: Releases 페이지.

## 미해결 / 리스크
- **HDR 모니터**: 본 머신엔 없음. 베타 사용자 피드백 필요.
- **PyInstaller onefile + pystray + Pillow 크기**: 첫 빌드 측정 전엔 예상 불가. 40MB 초과 시 onefile → onedir 폴백 검토.
- **Windows SmartScreen / Defender**: 서명 안 된 exe는 처음 실행 시 경고. 코드 사이닝 인증서는 비용 발생. cycle-03에선 README 안내로 갈음, 향후 검토.
- **자동실행 + 트레이 토스트**: Windows 11이 처음 실행 후 알림 센터에 묻혀 사용자가 트레이 위치를 찾기 어려움 → README에 "꺽쇠 ^ 클릭 후 nightshift 아이콘을 작업표시줄로 드래그" 안내.
- **PyInstaller가 `astral`의 timezone 데이터(`tzdata`/`zoneinfo`)를 포함하지 못하는 경우** — Python 3.12 `zoneinfo`는 OS tzdata 사용, Windows는 시스템 tz가 IANA가 아닐 수 있음. 첫 빌드에서 astral 동작 검증.
- **`schedule.manual` deprecated 필드**: config에 남아도 무시. cycle-04 스키마 정리 시 `schema_version` 올리고 삭제.

## 확정된 cycle-03 검증 기준 (초안)
1. `pyinstaller nightshift.spec` 빌드 성공, `dist\nightshift.exe` 생성.
2. exe 크기 ≤ **40MB**.
3. 클린 Windows 계정(또는 가상머신)에서 exe 단독 실행 → 메인 윈도우 + 트레이 정상 시작.
4. 모든 cycle-01/02 기능 회귀 확인(스케줄/트레이/슬라이더/확장 모드 다이얼로그 등).
5. `git tag v0.1.0 && git push --tags` → GitHub Actions 워크플로가 자동 빌드 + Releases에 exe 첨부.
6. Releases 페이지에서 exe 다운로드 → 다른 PC에서 실행 가능.
