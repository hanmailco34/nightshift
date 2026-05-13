# cycle-03 — Plan: PyInstaller onefile + GitHub Releases

## 목표
nightshift를 **단일 .exe** (≤40MB, Windows 10/11)로 빌드해 GitHub Releases로 배포할 수 있게 한다. 태그 푸시 → 자동 빌드/업로드 워크플로까지. 코드 사이닝(인증서)은 비용상 cycle-03 범위 외 — README로 SmartScreen 안내.

## 범위 (In)

### 아이콘 자산 (사용자 확정 — 자동 생성 노란 디스크)
- **`scripts/make_icon.py`** — Pillow로 노란 디스크 그리고 `assets/nightshift.ico`에 16/32/48/256 멀티사이즈로 저장. 트레이 `ui/tray._make_icon_image()`와 디자인 일치(같은 색·모양).
- **`assets/nightshift.ico`** — 생성 결과를 레포에 커밋(작은 바이너리, 빌드마다 재생성 회피). 디자인 변경 시 스크립트 재실행 후 재커밋.
- 트레이 아이콘은 in-memory `_make_icon_image()` 유지 (런타임 .ico 재로드 불필요).

### `nightshift.spec` (PyInstaller)
- `Analysis(['src/nightshift/__main__.py'], pathex=['src'])` — src layout 인식.
- `icon='assets/nightshift.ico'`.
- `console=False` (windowed), `onefile`.
- `hiddenimports=['pystray._win32', 'PIL._tkinter_finder']` — pystray Win32 백엔드와 PIL-Tk 브리지를 PyInstaller가 정적 import로 못 찾는 케이스 방어.
- `excludes=['astral.geocoder', 'tkinter.test', 'unittest', 'pydoc_data']` — `astral.geocoder`는 큰 도시 DB(우린 lat/lon만 사용).
- `upx=False` (UPX 도구 설치 회피; 사이즈 ≤40MB 달성 가능하다고 가정. 초과 시 act.md에서 검토).

### `.gitignore` 수정
- 기존 `*.spec`은 그대로 두고 `!nightshift.spec` 예외 한 줄 추가 (다른 임시 spec 파일은 계속 무시, 우리 spec만 추적).

### `.github/workflows/release.yml`
- Trigger: `on: push: tags: 'v*.*.*'`.
- `runs-on: windows-latest`, `python-version: '3.12'`.
- 단계:
  1. `actions/checkout@v4`
  2. `actions/setup-python@v5` (3.12)
  3. `pip install -e .` (editable install로 src/ 노출)
  4. `pip install -r requirements-dev.txt`
  5. `pyinstaller --clean --noconfirm nightshift.spec`
  6. `softprops/action-gh-release@v2`로 `dist/nightshift.exe` 업로드 (`generate_release_notes: true`, `name: nightshift ${{ github.ref_name }}`).
- 빌드 실패 시 워크플로 fail → 릴리스 안 만들어짐.

### README 보강
- "Features" 그대로 두고 새 섹션 추가:
  - **Download**: `https://github.com/hanmailco34/nightshift/releases/latest` 링크. "nightshift.exe 다운로드 후 더블클릭 실행. 설치 불필요."
  - **SmartScreen 안내**: 첫 실행 시 "Windows에서 PC 보호" 화면 → "자세한 정보" → "실행". 사이닝 안 된 exe라 정상 동작.
  - **트레이 아이콘 보이기**: Windows 11 알림영역 그룹화 시 ^ 클릭 후 nightshift 아이콘을 작업표시줄로 드래그.
- "Dev setup"에 빌드 절차 한 줄: `pip install -r requirements-dev.txt && pyinstaller nightshift.spec`.
- 가능하면 스크린샷 1장(메인 윈도우) placeholder.

## 범위 (Out — cycle-04 이상)
- 코드 사이닝 인증서, SmartScreen 우회.
- 자동 업데이트(in-app).
- macOS / Linux 포트.
- exe 사이즈 더 줄이기(UPX, onedir+zip).

## 검증 기준
1. `pyinstaller --clean --noconfirm nightshift.spec` 로컬 빌드 성공, `dist/nightshift.exe` 생성.
2. **크기 ≤ 40MB** (`(Get-Item dist\nightshift.exe).Length/1MB` 확인).
3. `dist/nightshift.exe` 더블클릭 실행 → 메인 윈도우 + 트레이 정상 시작 (config는 `%APPDATA%\nightshift\` 그대로 사용).
4. cycle-01/02 기능 회귀: 슬라이더/탭/확장 모드 다이얼로그/트레이 4메뉴/스케줄 자동 전환(임시 시간으로 1분 후 페이드)/창 X 트레이 최소화/일시중지 배너.
5. 가능하면 다른 사용자 계정 또는 클린 VM에서 실행 검증 (보너스).
6. 워크플로 dry-run: 로컬에서 `pyinstaller --clean ...`이 성공하면 워크플로도 동일 명령으로 성공 가정. 실제 `git tag v0.1.0 && git push origin v0.1.0`은 사용자 자율 시점.

## 리스크 / 미정
- **pystray hidden import**: `pystray._win32` 누락 시 트레이 메뉴 무동작 → 빌드 후 트레이 동작 우선 확인.
- **astral 동작**: `astral.geocoder` exclude 후 `astral.sun.sun()`이 정상인지 — 빌드된 exe에서 use_sunset 모드로 토글해서 확인.
- **PyInstaller가 `astral`의 timezone 데이터를 못 가져올 수도**: Python 3.12 `zoneinfo`는 OS tzdata 사용. Windows 11이 `tzdata` 파이썬 패키지를 별도로 요구하는 경우 있음 → 필요 시 `tzdata`를 `requirements.txt`에 추가.
- **사이즈 40MB 초과 시**: act.md에 후속 정책 — (a) onefile→onedir + zip, (b) `numpy`/`scipy`/`PIL.ImageTk` 추가 exclude, (c) UPX 도입.
- **첫 실행 시 SmartScreen 경고**: 정상 — README가 우회 방법 안내.

## 산출 (사이클 종료 시)
- `do.md` / `check.md` / `act.md`
- `CLAUDE.md` 사이클 로그에 한 줄 추가
- 커밋·push (v0.1.0 태그 실제 푸시는 사용자 결정 후)
