# cycle-01 — Check: 검증 결과

## 단위 테스트
`python -m pytest -q` → **33 passed** (cycle-00 14 + cycle-01 19).
- temperature 5
- gamma ramp 9 (cycle-00 8 + `apply_kelvin` clamp kwarg 전파 회귀 1)
- config store 10
- controller 9

## 수동 통합 (실 PC, 모니터 3대 — `\\.\DISPLAY1/2/3`)
| 항목 (plan.md 검증 기준) | 결과 |
|---|---|
| 1. pytest 전부 green | **OK** (33 passed) |
| 2. 메인 윈도우 표시, 개별 OFF 기본 → 글로벌 페이지 | **OK** |
| 3. 글로벌 야간 슬라이더 → 3대 동시 따뜻 + 라디오 자동 야간 전환 | **OK** |
| 4. 개별 ON → 탭 3개 등장, primary 탭만 조작 시 그 모니터만 변화 | **OK** |
| 5. 확장 토글 ON → 다이얼로그 → "이미 설정함" → 자가 진단 통과 → 슬라이더 하한 1500K로 확장 → 1500K 시각적 강한 주황빛 | **OK** |
| 6. 확장 토글 OFF → 슬라이더 하한 3300K로 잠금 (config K값은 보존) | **OK** |
| 7. 창 X 닫기 → 모든 모니터 항등 램프로 복원 | **OK** |

## 발견 / 메모
- 콘솔 인코딩(cp949)에서 `print` 출력은 ASCII 유지 — UI 안의 한국어 라벨은 tkinter 유니코드라 무관.
- `tk.Scale` 슬라이더는 키보드 포커스로도 ±50K 미세 조정 가능 (resolution=50). 의도된 동작.
- 자가 진단은 ~50ms 안에 끝나므로 시각적 깜빡임은 한순간. 사용자가 인지 가능하나 거슬리지 않음.
- HDR 디스플레이 케이스는 이 머신엔 없음 → `apply_current`의 실패 리스트는 cycle-01에선 콘솔 stdout으로만 알림(UI 표시는 cycle-02 토스트와 함께 정리).

## 결론
- cycle-01 plan의 In-scope 전부 구현, 검증 7항목 모두 통과. 확장 색온도 범위 옵트인 토글 동작 확인.
- 인터페이스 확정: `apply_kelvin(..., clamp_to_windows_limit=True)`, `controller.Controller` + `from_config`, `store.load/save/default_config/ensure_monitor_entries`, `registry.read_gdi_icm_gamma_range`.
- 다음 cycle-02로 스케줄/트레이/자동실행/전체화면감지 진행.
