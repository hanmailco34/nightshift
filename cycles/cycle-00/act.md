# cycle-00 — Act: 다음 사이클 반영사항

## 결정
1. **색온도 하한 2단계 제공**
   - 기본 모드: 슬라이더 하한 = **3300K** (레지스트리 설정 없이 어디서나 동작). UI 슬라이더는 `apply` 실패 시 자동으로 가능한 가장 낮은 값까지 후퇴(binary search 1회)하고, 그 값을 "이 모니터에서 가능한 최저"로 표시.
   - 확장 모드(설정 토글 "확장 색온도 범위 — 1회 설정 필요"): 켜면 `GdiICMGammaRange=256` 레지스트리 설정 + 재부팅 안내(관리자 권한 헬퍼 또는 수동 안내 다이얼로그). 적용 후 하한 2700K(요청 사양).
   - README에 이 제약과 설정법을 명시.
2. **`apply_kelvin` 반환값을 호출부에서 반드시 확인** — 실패 시 사용자에게 토스트/상태표시. 현재 bool 반환은 유지.
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
- `GdiICMGammaRange=256` 값이 실제로 2700K까지 허용하는지 이 PC에서 미검증(관리자 필요). cycle-01에서 사용자가 관리자 셸로 1회 검증 필요.
- Night light 동시 사용 시 동작 미검증.
