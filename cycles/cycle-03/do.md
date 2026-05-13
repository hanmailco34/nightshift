# cycle-03 — Do: 작업 로그

## 만든 것
- **`scripts/make_icon.py`** — Pillow로 노란 디스크 16/32/48/256 멀티사이즈 `.ico` 생성. 트레이 `_make_icon_image()`와 디자인 일치.
- **`assets/nightshift.ico`** — `make_icon.py` 결과 커밋 (4.3 KB).
- **`nightshift.spec`** — PyInstaller 6.x 모던 폼.
  - entry: `src/nightshift/__main__.py`, `pathex=['src']`.
  - `icon='assets/nightshift.ico'`, `console=False` (windowed), onefile.
  - `hiddenimports=['pystray._win32', 'PIL._tkinter_finder']`.
  - `excludes=['astral.geocoder', 'tkinter.test', 'unittest', 'pydoc_data']`.
  - `upx=False`.
- **`.github/workflows/release.yml`**
  - Trigger: `v*.*.*` 태그 푸시.
  - windows-latest + Python 3.12. `pip install -e .` + `pip install -r requirements-dev.txt` → `pyinstaller --clean --noconfirm nightshift.spec` → `softprops/action-gh-release@v2`로 `dist/nightshift.exe` 자동 업로드 + 자동 릴리스 노트.
  - `permissions: contents: write` 명시.

## 변경한 것
- **`.gitignore`**: `*.spec` 직후에 `!nightshift.spec` 예외 한 줄 추가 (다른 임시 spec은 계속 무시).
- **`src/nightshift/__main__.py`**: relative import 2건(`from .display.monitors`, `from .ui.main_window`)을 absolute(`from nightshift.display.monitors`, `from nightshift.ui.main_window`)로 교체. 이유는 아래 "도중에 고친 것" 참고.
- **`README.md`**:
  - "Features" 끝줄 "Planned: single-file .exe ... cycle-03"을 완료 상태("Single-file `.exe` (~32 MB, no install)")로 바꿈.
  - 새 섹션 **Download**: Releases 페이지 링크 + SmartScreen "More info → Run anyway" 안내 + Windows 11 트레이 아이콘 ^ 드래그 안내.
  - "Dev setup"을 UI 기준으로 정리 (`python -m nightshift`가 메인 윈도우, `--diagnose`로 진단). gamma CLI 라인은 제거(있어도 됐는데 dev 셋업 단순화).
  - 새 서브섹션 **Build the .exe locally**: `pyinstaller --clean --noconfirm nightshift.spec` 명령 + GitHub Actions가 같은 명령을 자동 실행한다는 설명.

## 도중에 고친 것
- **첫 빌드(8.02 MB)가 사실은 import 실패 빌드였음**. `dist/nightshift.exe` 실행 시 `ImportError: attempted relative import with no known parent package` (`__main__.py` line 27, 32). PyInstaller가 `__main__.py`를 entry로 잡으면 그 파일을 top-level `__main__` 모듈로 직접 실행해서 패키지 컨텍스트(`__package__`)가 없어짐 → relative import 실패. 다른 모듈(controller / engine / main_window 등)의 relative import는 그대로 둬도 됨 — 그것들은 entry가 아니라 import되는 입장이라 패키지 컨텍스트가 살아있음. **`__main__.py`만** absolute로 바꾸면 됨. 수정 후 재빌드 → **31.58 MB** (진짜 사이즈, 패키지가 실제로 번들됨). 40MB 한계 안.
- 첫 빌드는 PyInstaller가 entry 모듈만 빌드하고 import 그래프를 못 탄 채 마무리되어 사이즈가 작게 나온 것. 런타임에서야 import 실패가 드러남 → "사이즈가 갑자기 작아지면 의심해라" 교훈.

## 빌드 / 검증 명령
- `pip install pyinstaller` (cycle-03 진입 시 첫 설치 — `requirements-dev.txt`에 명시는 있었지만 cycle-00에서 안 깔린 상태였음).
- `pyinstaller --clean --noconfirm nightshift.spec` → `dist/nightshift.exe` (31.58 MB).
- `dist\nightshift.exe` 더블클릭 → 메인 윈도우 + 트레이 정상 시작 (사용자 회귀 확인 통과).
- 단위테스트 66 green 유지(absolute import 변경 후 회귀 없음).

## 환경 / 의존성
- PyInstaller 6.20 (`pip install pyinstaller`로 신규 설치). altgraph, pefile, pyinstaller-hooks-contrib, pywin32-ctypes가 transitive로 같이 설치됨.
- 신규 런타임 의존성 없음.
