# cycle-00 — Act: 다음 사이클 반영사항

## 결정
1. **색온도 슬라이더는 2700K–6500K 그대로 두되, 램프는 항상 클램핑** (`build_gamma_ramp` 기본 동작 — cycle-00에서 구현 완료). `apply_kelvin`이 실패하지 않음. 단 ≈3300K 아래는 시각 효과가 포화되므로:
   - UI에 "이 환경의 실제 한계 ≈3300K" 안내(작은 텍스트/툴팁). 슬라이더 트랙에 3300K 지점 마커 표시 검토.
   - `GdiICMGammaRange=256` + 재부팅은 이 PC에서 무효 확인됨 → "확장 모드" 기능은 보류. README엔 "일부 환경에서 효과 없음"으로만 언급. (원하면 cycle-01에서 `512/1024/65536` 값으로 사용자가 추가 실험.)
2. **`apply_kelvin` 반환값을 호출부에서 항상 확인** — 실패(드라이버/HDR 등) 시 사용자에게 상태표시. bool 반환 유지.
3. **모니터 라벨 보강** — 모델명이 "Generic PnP Monitor"로 겹치므로 UI 탭/리스트에서 `해상도` 또는 `DISPLAYn`을 부제로 노출.
4. **확정된 인터페이스 (cycle-01이 의존)**
   - `display.monitors.list_monitors() -> list[Monitor]` / `Monitor.device_name` / `.label`
   - `color.gamma.apply_kelvin(device_name, kelvin, brightness=1.0) -> bool`
   - `color.gamma.reset(device_name) -> bool`
   - `color.temperature.kelvin_to_rgb(k) -> (r,g,b)` — UI 미리보기 박스 색상에 그대로 사용.

## cycle-01 착수 항목
- `config/store.py` (`%APPDATA%\nightshift\config.json`: 모니터별 day/night K, 개별설정 토글, 스케줄 21:00/07:00, 위도/경도(기본 서울), 토글 3종, 확장모드 플래그).
- `ui/main_window.py` (tkinter): 모니터 탭 3개 + day/night 슬라이더(하한 동적) + 미리보기 박스 2개 + "모니터별 개별 설정" 토글. 슬라이더 → `apply_kelvin` 실시간, 저장 시 config 반영.
- 색온도 적용을 모아 관리할 얇은 `color/controller.py`(현재 모드/모니터별 목표값 보관, day↔night 전환 시 호출) 도입 검토.

## 미해결 / 리스크
- `GdiICMGammaRange=256`(+재부팅) → 이 PC에선 **무효 확인**. 더 큰 값 미시도. 사용자가 원하면 추후 실험.
- Night light 동시 사용 시 동작 미검증.
- 클램핑 한계값(현재 32000)은 경험값. 다른 GPU/드라이버에서 더 빡빡할 수 있음 → 그 경우 `apply_kelvin` 실패 시 한계값을 낮춰 재시도하는 로직 검토.
