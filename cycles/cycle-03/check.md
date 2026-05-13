# cycle-03 — Check: 검증 결과

## 단위 테스트
`python -m pytest -q` → **66 passed** (cycle-00 13 + cycle-01 20 + cycle-02 33). `__main__.py` absolute import 변경 후에도 회귀 없음.

## 빌드 / 실행

| plan.md 검증 기준 | 결과 |
|---|---|
| 1. `pyinstaller --clean --noconfirm nightshift.spec` 빌드 성공, `dist/nightshift.exe` 생성 | **OK** |
| 2. exe 크기 ≤ 40MB | **OK** — **31.58 MB** (한계의 79%) |
| 3. `dist/nightshift.exe` 더블클릭 실행 → 메인 윈도우 + 트레이 정상 | **OK** (1차 시도 import 에러 → `__main__.py` absolute import 패치 후 통과) |
| 4. cycle-01/02 기능 회귀 (슬라이더/탭/확장 모드/트레이 4메뉴/창 X 트레이 최소화) | **OK** (사용자 수동 확인 통과) |
| 5. 다른 사용자 계정/클린 VM 검증 | 보너스 항목, 미실측 |
| 6. 워크플로 dry-run (로컬 동일 명령이 성공하면 워크플로도 OK 가정) | **OK** — 워크플로는 동일 명령(`pip install -e .`, `pip install -r requirements-dev.txt`, `pyinstaller --clean --noconfirm nightshift.spec`)을 windows-latest에서 실행. 실제 `git tag v0.1.0 && git push origin v0.1.0`은 사용자 자율 시점 |

## 발견 / 메모
- **PyInstaller 6 + relative import 함정** (do.md 상세). 1차 빌드 사이즈가 8MB로 의심스럽게 작았는데 실제론 패키지 import 실패 빌드였음. absolute import 패치 후 31.58MB의 실제 빌드.
- `pystray._win32`, `PIL._tkinter_finder` hidden import는 빌드 후 트레이/UI 동작으로 검증 통과 (Pillow가 ImageDraw로 트레이 아이콘 생성 후 표시 OK, pystray Win32 메뉴 4개 동작 OK).
- `astral.geocoder` exclude 후에도 use_sunset 모드는 본 머신에서 manual 모드만 검증함(astral 실측은 cycle-02에서 unit tests로 검증, exe 빌드 후 astral 직접 호출 미실측 — 사용자가 use_sunset 토글 켜서 "다음 일몰 hh:mm" 라벨이 정상 갱신되는지 확인하면 보너스).
- `nightshift.spec`이 `.gitignore`의 `*.spec`에 잡히던 문제는 `!nightshift.spec` 예외로 해결.
- 워크플로 `permissions: contents: write`는 `softprops/action-gh-release@v2`가 릴리스를 생성하려면 필수.

## 결론
- cycle-03 plan의 In-scope 전부 구현, 검증 4항목(필수) 통과.
- 단일 exe(31.58 MB) 빌드 가능, GitHub Actions로 태그 푸시 시 자동 배포 가능 (실제 태그 푸시는 사용자가 시점 결정).
- 4 cycle PDCA 완주 — cycle-00 PoC → cycle-01 UI → cycle-02 스케줄/트레이 → cycle-03 빌드/배포.
