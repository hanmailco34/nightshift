# cycle-04 — Check: 검증 결과

## 단위 테스트
`python -m pytest -q` → **79 passed** (cycle-00 13 + cycle-01 20 + cycle-02 33 + cycle-04 13).
- config v2: schema 확장, v1→v2 마이그레이션, 프리셋 시드/라운드트립 (+4).
- controller single 모드 분기, visual floor 작용/비작용, mode 읽기 (+7).
- schedule single 모드 skip, day/night 트리거 정상 (+2).

## 수동 통합 (실 PC, 모니터 3대)

| plan.md 검증 기준 | 결과 |
|---|---|
| 1. pytest green | **OK** (79 passed) |
| 2. 모드 라디오에 "단일" 보임, 선택 시 슬라이더 1개로 변경 | **OK** |
| 3. 단일 모드에서 schedule.night_start 현재+1분이어도 자동 전환 안 함 | **OK** (engine._evaluate_once skip 확인) |
| 4. 프리셋 영역 빌트인 4개 칩, "할로겐 (3400K)" 클릭 시 모든 모니터 즉시 3400K | **OK** |
| 5. "+ 저장" 다이얼로그 → 이름 입력 → 새 칩 등장 | **OK** |
| 6. 칩 우클릭 → 삭제 → 사라짐, config 영구 반영 | **OK** |
| 7. 트레이 "프리셋" 서브메뉴 동일 목록 → 적용 동작 | **OK** |
| 8. 재실행 시 mode / 프리셋 / single_k 복원, v1 config 자동 v2 마이그레이션 | **OK** |

## 사용자 피드백 (cycle-04 검증 도중 즉시 반영)

### 1) "확장 색온도 범위가 아닌데 프리셋 때문에 백열등과 촛불이 선택돼"
→ `_is_preset_enabled` 추가, 확장 OFF면 K<3300K 프리셋 칩 disabled (회색 + 클릭 불가). 트레이 서브메뉴 항목도 동일하게 비활성. 확장 ON 토글 시 즉시 활성화.

### 2) "촛불에서 내가 확장색 온도 범위를 껐는데 색은 변하지 않아"
→ 디버그 print로 진단: `apply_kelvin(d, 1900, clamp=True)`가 정확히 호출되지만 그 결과 시각이 사용자 기대(=3300K warm white)와 불일치(=살구색)였음. 근본 원인은 cycle-01 "raw K 보존" 정책에서 시각 floor를 명시하지 않은 것. `controller.effective_target_for(device)` 도입으로 `apply_current`가 `max(floor, raw)`만 OS에 전달 — raw K는 보존, 시각은 슬라이더 표시와 일치.

→ 두 패치 후 재검증 통과 (사용자 직접 확인).

## 발견 / 메모
- 확장 토글 OFF → ON 다이얼로그 통과 직후, 자가진단 코드의 "직전 상태 복원" 단계가 raw K (1900)로 복원해 잠시 (수십 ms) 살구색이 보였다가 set_extended_range(True) + apply_now가 real 1900K로 재적용 → 매우 짧은 시각 깜빡임이긴 하나 일상 사용엔 무해. cycle-05에서 정리 검토.
- 프리셋의 디폴트 시드는 사용자가 모두 삭제 가능. 마이그레이션은 schema_version로 1회만 동작하므로 의도된 빈 상태 보존됨.
- pystray 메뉴 동적 갱신(`Icon.update_menu`)이 Windows 11에서 안정 동작 확인.

## 결론
- cycle-04 plan In-scope 모두 구현 + 검증 8항목 통과 + 사용자 피드백 2건 반영 완료.
- 인터페이스 확정: `controller.visual_floor()` / `effective_target_for()`, `Mode = "day"|"night"|"single"`, config schema v2 (presets/single_k/mode).
- 다음: cycle-05는 코드 사이닝 / 자동 업데이트 / 프리셋 export/import / 단축키 등 운영 품질 개선이 후보.
