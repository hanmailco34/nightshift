# cycle-03 — Act: 다음 사이클 / 운영 반영사항

## 결정 / 운영 가이드
1. **첫 릴리스 시점**은 사용자 결정. `git tag v0.1.0 && git push origin v0.1.0`을 누르면 GitHub Actions가 자동으로 빌드해서 Releases에 `nightshift.exe` 첨부.
2. **버전 관리**: `pyproject.toml`의 `version`이 진실값. 릴리스 전 0.1.0 → 0.1.1 등으로 올리고 같은 값으로 태그 푸시. 자동 동기화 로직은 cycle-04(필요 시).
3. **아이콘 디자인 변경 시**: `python scripts/make_icon.py` 재실행 → `assets/nightshift.ico` 재커밋. PyInstaller가 이 파일을 그대로 사용.
4. **사이즈 관찰**: 현재 31.58 MB / 40 MB 한계의 79%. 새 의존성 추가 시 빌드 후 재측정.

## (선택) cycle-04 후보
- **코드 사이닝** — SmartScreen 경고 제거. Authenticode 인증서 구매(연 $80~$400)와 빌드 단계 변경. 비용 발생.
- **자동 업데이트** — 앱 내부에서 GitHub Releases API로 최신 버전 체크 → 다운로드/재시작 흐름. PyUpdater 등 도구 검토.
- **로깅 / 크래시 리포팅** — 사용자 PC에서 무엇이 실패했는지 보내는 옵트인 텔레메트리.
- **macOS / Linux 포트** — `SetDeviceGammaRamp` 대체(CGSetDisplayTransferByFormula on macOS, X11 `XRRSetCrtcGamma` / Wayland gamma protocol on Linux). 별 패키지로 분리하거나 backend 레이어 추가.
- **`schedule.manual` deprecated 필드 정리** — config schema_version 2 도입.

## 미해결 / 운영 리스크
- **SmartScreen 첫 실행 경고**: 사이닝 없는 한 사용자에게 "Windows protected your PC" 다이얼로그가 뜸. README가 우회 방법 안내, 코드 사이닝 비용 발생 — 베타 사용자 피드백 후 결정.
- **HDR / 기타 GPU**: `SetDeviceGammaRamp`가 거부될 수 있는 환경(HDR 활성, 일부 Intel/AMD 드라이버) — `controller.apply_current()` 실패 device를 상태바에 빨갛게 표시(cycle-02에서 구현). 베타 피드백 받아 후속 조치 결정.
- **`astral` exe 동작 검증 미실측** (manual 모드만 확인). 사용자가 use_sunset 토글로 한 번 검증하면 좋음.
- **PyInstaller relative-import 함정**: `__main__.py` 안의 import는 항상 absolute여야 함. 향후 다른 entry 추가 시 동일 규칙 적용.
- **첫 빌드 사이즈가 작으면 의심**: 패키지 import가 안 잡힌 stub 빌드일 수 있음(이번 케이스 — 8MB로 의심스럽게 작았음). 항상 빌드 후 exe 실행 검증.

## 운영 절차
- **새 기능 → 새 릴리스 순서**:
  1. 코드 변경 + 단위 테스트 + 메인 윈도우 수동 회귀.
  2. `pyinstaller --clean --noconfirm nightshift.spec` 로컬 빌드 + 더블클릭 실행 회귀.
  3. `pyproject.toml`의 `version` 업데이트 + 커밋.
  4. `git tag v0.X.Y && git push origin v0.X.Y` → GitHub Actions 자동 빌드/업로드.
  5. Releases 페이지에서 노트 다듬기 (필요 시).

## 최종 상태
- cycle-00 ~ cycle-03 PDCA 사이클 4회 완주.
- 단위테스트 66 green. PyInstaller onefile 빌드 31.58 MB.
- 모든 기능 코드 + 자동 빌드 워크플로 + 사용자 가이드(README) 완비.
- v0.1.0 첫 릴리스 시점은 사용자 자율.
