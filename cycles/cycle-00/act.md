# cycle-00 — Act: 다음 사이클 반영사항

## 결정
1. **색온도 슬라이더는 2700K–6500K 그대로 두되, 램프는 기본 클램핑** (`build_gamma_ramp` 기본 동작 — cycle-00에서 구현 완료). `apply_kelvin`이 실패하지 않음. 단 ≈3300K 아래는 시각 효과가 포화되므로:
   - UI에 "기본 상태 실제 하한 ≈3300K, 확장 모드 시 ~1500K까지" 안내. 슬라이더 트랙에 3300K 지점 마커 표시 검토.
   - **옵트인 "확장 색온도 범위" 토글 채택** (안 C). `GdiICMGammaRange=256` + 실제 Windows 재부팅 후 풀범위 시각 적용 확인됨(scripts/probe_unclamped.py). cycle-01에서 config 플래그 + UI 토글 + 첫 활성화 시 안내 다이얼로그(관리자 권한 레지스트리 설정 + 재부팅 안내) 구현. 활성 시 `apply_kelvin`에 `clamp_to_windows_limit=False` 전달.
2. **`apply_kelvin` 반환값을 호출부에서 항상 확인** — 실패(드라이버/HDR 등) 시 사용자에게 상태표시. bool 반환 유지.
3. **모니터 라벨 보강** — 모델명이 "Generic PnP Monitor"로 겹치므로 UI 탭/리스트에서 `해상도` 또는 `DISPLAYn`을 부제로 노출.
4. **확정된 인터페이스 (cycle-01이 의존)**
   - `display.monitors.list_monitors() -> list[Monitor]` / `Monitor.device_name` / `.label`
   - `color.gamma.apply_kelvin(device_name, kelvin, brightness=1.0) -> bool`
   - `color.gamma.reset(device_name) -> bool`
   - `color.temperature.kelvin_to_rgb(k) -> (r,g,b)` — UI 미리보기 박스 색상에 그대로 사용.

## cycle-01 착수 항목
- `config/store.py` (`%APPDATA%\nightshift\config.json`: 모니터별 day/night K, 개별설정 토글, 스케줄 21:00/07:00, 위도/경도(기본 서울), 토글 3종, `extended_range` 플래그).
- `ui/main_window.py` (tkinter): 모니터 탭 3개 + day/night 슬라이더(하한은 `extended_range`에 따라 1500K/3300K 동적) + 미리보기 박스 2개 + "모니터별 개별 설정" 토글. 슬라이더 → `apply_kelvin` 실시간, 저장 시 config 반영.
- **확장 색온도 범위** 토글 — 비활성 시 클램핑 ON·하한 3300K; 활성 시 첫 활성화 안내 다이얼로그(관리자 PowerShell로 `GdiICMGammaRange=256` 설정 + Windows 재부팅 안내 + 현재 레지스트리 상태 표시 + 재부팅 후 풀범위 사용 가능) → 이후 클램핑 OFF·하한 1500K. 토글 끄면 다시 클램핑 ON(재부팅 불필요, 레지스트리는 그대로 둬도 무해).
- 색온도 적용을 모아 관리할 얇은 `color/controller.py`(현재 모드/모니터별 목표값 보관, day↔night 전환 시 호출) 도입 검토.

## 미해결 / 리스크
- `GdiICMGammaRange=256`(+재부팅) → 이 PC에선 **유효 확인**. 다른 GPU/드라이버에서도 유효한지는 확장 모드 활성 직후 `apply_kelvin(unclamped)` 결과로 자가 진단하는 로직을 cycle-01에서 추가 검토.
- Night light 동시 사용 시 동작 미검증.
- 클램핑 한계값(현재 32000)은 경험값. 다른 GPU/드라이버에서 더 빡빡할 수 있음 → 그 경우 `apply_kelvin` 실패 시 한계값을 낮춰 재시도하는 로직 검토.
