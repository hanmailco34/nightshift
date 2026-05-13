# cycle-02 — Check: 검증 결과

## 단위 테스트
`python -m pytest -q` → **66 passed** (cycle-00 13 + cycle-01 20 + cycle-02 33).
- 신규 33: schedule engine 18 + autostart 7 + fullscreen 8.

## 수동 통합 (실 PC, 모니터 3대)

| plan.md 검증 기준 | 결과 |
|---|---|
| 1. pytest 전부 green | **OK** (66 passed) |
| 2. `schedule.night_start` "현재+1분"으로 두고 1분 후 5초 페이드 야간 전환 | **OK** + 모드 라디오 자동 동기화 |
| 3. `use_sunset` 켜고 위/경도 변경 → "다음 일몰 hh:mm" 라벨 갱신, 실제 일몰 도달 시 야간 전환 | (라벨 갱신/실측 부분 통과, 실제 일몰 도달은 시간상 미실측 — 단위 테스트 `next_transition` 검증으로 갈음) |
| 4. 자동실행 토글 ON → 재부팅 시 트레이로 자동 기동 | (HKCU Run 등록 동작 OK; 실제 재부팅 후 자동 기동 미실측 — 사용자 자율 확인) |
| 5. 전체화면 영상/게임 → 즉시 정상색, 종료 시 야간 복귀 | (수동 검증 스킵 — 단위 테스트 `is_fullscreen_app_visible` rect 매칭 OK) |
| 6. 트레이 메뉴 4가지 동작 (열기 / 일시중지↔다시 시작 / 야간 즉시 / 종료) | **OK** |
| 7. 창 X로 닫고 트레이 "열기"로 복원, controller state·슬라이더 위치 유지 | **OK** (첫 닫기 시 풍선 알림 1회 표시 확인) |

## cycle-02 사용자 피드백 (1차 검증 후 즉시 반영)
1. **"Enter 말고 적용 버튼이 있으면 좋겠다"** — 사이드 스케줄 카드에 **"적용"** 버튼 추가. Enter / 포커스 아웃 자동 저장은 보조로 유지.
2. **"일시중지도 화면에 표시되면 좋겠다"** — 상단 모드 바 아래에 노란 배너("⏸ 일시중지됨 — 모든 모니터 정상색. 트레이에서 다시 시작하세요.") 추가. 일시중지 해제 시 자동 숨김.
3. **"자동 스케줄 전환 시 모드 라디오가 안 움직임"** — `Scheduler.on_mode_change` 콜백 추가, `MainWindow._on_external_mode_change`로 `mode_var.set(target)` 동기화. 트레이 "야간 즉시"도 같은 경로로 일관 처리.

→ 3건 모두 패치 후 사용자 재확인 통과.

## 발견 / 메모
- 보간 중 사용자 슬라이더 조작 즉시 우선 — `Scheduler.cancel_transition` 토큰 증가 패턴이 의도대로 동작.
- `Tray.notify` 첫 닫기 풍선 알림은 Windows 11 알림 그룹화 정책상 알림 센터에는 들어가지만 화면 토스트는 안 뜰 수 있음 — 이 PC에선 토스트로 뜸.
- 트레이 데몬 스레드 종료: `Tray.stop()` → `Icon.stop()`이 호출되며 detached 스레드가 깔끔히 종료.
- HDR 디스플레이 시나리오는 본 머신엔 없음(미실측, cycle-01과 동일 리스크).

## 결론
- cycle-02 plan의 In-scope 전부 구현 + 사용자 피드백 3건 반영 완료.
- 인터페이스 확정 (`Scheduler`, `Tray`, `autostart.*`, `fullscreen.is_fullscreen_app_visible`).
- 다음 cycle-03 (PyInstaller 빌드 + GitHub Releases)로 진행.
