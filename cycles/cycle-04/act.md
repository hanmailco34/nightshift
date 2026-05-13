# cycle-04 — Act: 다음 사이클 반영사항

## 결정 / 확정된 인터페이스
1. **`color.controller`**
   - `Mode = Literal["day", "night", "single"]`.
   - `Controller.target_for(device) -> int` — *raw* K (UI 슬라이더 IntVar와 controller monitors에 저장된 값).
   - `Controller.visual_floor() -> int` — 현재 `extended_range`에 따라 1500 또는 3300.
   - `Controller.effective_target_for(device) -> int` — `max(visual_floor, target_for)`. **OS에 전달되는 K**.
   - `Controller.apply_current(devices)`가 effective K 사용.
2. **`config.store` 스키마 v2**
   - `mode` (top-level), `global.single_k`, `monitors[d].single_k`, `presets`.
   - 프리셋 항목 = `{name: str, default_k: int|None, kelvins: {device: int}}`.
   - v1 → v2 자동 마이그레이션(load 시 1회).
3. **`schedule.engine.Scheduler`**: `_evaluate_once`가 mode=="single"이면 즉시 return.
4. **`ui.tray.Tray`**: `on_apply_preset` / `get_presets`를 받음. `get_presets()`는 `[(name, enabled), ...]` 또는 `[name, ...]` 둘 다 지원. `update_presets()` 호출로 메뉴 재빌드.

## cycle-05 후보 (우선순위 추천 순)
- **프리셋 export/import** (JSON 파일 또는 클립보드) — 공유 / 백업.
- **키보드 단축키** — 메인 윈도우 포커스 시: `Ctrl+1/2/3` (모드), `Ctrl+P` (프리셋 빠른 적용 다이얼로그), `Ctrl+,` (설정). 전역 핫키는 OS-수준 등록 필요해 별도 검토.
- **빌트인 프리셋 read-only 표기** — 사용자가 실수로 빌트인을 지우는 케이스 방지 옵션. 현재는 모두 자유 편집인데 cycle-04에서 단순화한 결정.
- **확장 모드 자가 진단 깜빡임 정리** — 직전 K 복원 단계를 effective K로 하면 ON 토글 직후 안정. (cycle-04 발견 메모 참고)
- **코드 사이닝** — SmartScreen 우회. 비용 발생, 운영 결정 사항.
- **자동 업데이트** — GitHub Releases API 폴링 + 다운로드 흐름.
- **macOS / Linux 백엔드** — gamma.py를 backend 레이어로 분리.

## 운영 / 릴리스
- 다음 릴리스 시점 결정 시: `pyproject.toml` `version = "0.2.0"` 으로 올리고 `git tag v0.2.0 && git push origin v0.2.0` → GitHub Actions가 자동 빌드/Releases 첨부.
- 사용자 v1 config가 있는 경우 첫 실행 시 자동 v2 마이그레이션 — README에 별도 안내 불필요(투명).

## 미해결 / 리스크
- **자가 진단 깜빡임** (cycle-04 check.md 메모) — 확장 ON 토글 직후 ~수십 ms 동안 살구색 노출. UI 마찰 미미.
- **프리셋 device 키 불일치** — 모니터 교체 시 저장된 device 키가 무효화. 현재는 누락 device는 default_k로 폴백 또는 무시. 사용자 안내 없음. 베타 피드백 받으며 결정.
- **GdiICMGammaRange=256 환경의 시각 검증** — 확장 ON에서 1500K까지 검증됨. 확장 OFF에서 effective floor=3300K → ramp clamp=True 사용. 깊은 warm에서도 ramp가 안전 범위 안 (clamp 코드가 ±32000 강제).
- **HDR 모니터** — 본 머신엔 없음. 베타 피드백 필요(cycle-03 act 동일 리스크).

## 최종 상태
- cycle-00 ~ cycle-04 PDCA 5사이클 완주. 단위테스트 79 green. PyInstaller onefile 31.58 MB.
- 기능 커버리지: 모니터별 day/night/단일 K, 자동 스케줄(manual/astral), 5s 페이드, 시스템 트레이, 자동 실행, 전체화면 비활성화, 확장 색온도 범위 옵트인, 빌트인+사용자 프리셋.
- v0.1.0 릴리스됨. v0.2.0은 cycle-04 반영 시점 결정.
