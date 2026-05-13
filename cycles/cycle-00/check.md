# cycle-00 — Check: 검증 결과

## 단위 테스트
`python -m pytest -q` → **11 passed**. (temperature 5, gamma ramp 6)

## 모니터 열거 — OK
`python -m nightshift` 가 모니터 3대를 라벨/디바이스/해상도/좌표/primary와 함께 출력. 정렬(좌→우, 상→하) 정상.
- 한계: 이 PC에선 셋 다 모델명 "Generic PnP Monitor" (EDID로 모델 문자열 미보고). cycle-01 UI에선 라벨 끝에 `(DISPLAYn)` 또는 해상도를 함께 보여 구분 보강 필요.

## 색온도 적용 — 부분 성공 + 중요한 제약 발견 ⚠️
| 동작 | 결과 |
|---|---|
| `--reset` (항등 램프) — 3대 모두 | **OK** (항상 성공) |
| `--apply <i> 3500` — 3대 모두 | **OK**, 화면이 눈에 띄게 따뜻해짐, reset으로 복원됨 |
| `--apply <i> 3300` — 3대 모두 | **OK** |
| `--apply <i> 3200` 이하 (3000/2700) — 3대 모두 | **FAILED** (`SetDeviceGammaRamp`가 0 반환) |

### 원인: Windows 감마 램프 선형-편차 클램프
Windows는 `SetDeviceGammaRamp`에 넘긴 램프의 각 엔트리가 선형 램프에서 약 ±0x8000(32768/65536) 이상 벗어나면 거부한다. 색온도를 낮출수록 파란 채널 상단(`blue[~200]` 부근)이 선형에서 크게 떨어져 이 한계를 넘는다 → 약 **3300K 아래로는 적용 불가**(3대 모두 동일 임계값).

### `GdiICMGammaRange` 레지스트리 우회법 — 이 PC에선 **효과 없음** ❌
`HKLM\...\ICM\GdiICMGammaRange` DWORD = `256` 설정 + 재부팅(관리자 권한으로 실측)했으나, 임계값은 **그대로 ≈3300K**. 커뮤니티(f.lux 설치 프로그램, gammy 등)에서 알려진 우회법이지만 Windows 11 26200 + 현재 GPU 드라이버에선 무효. (더 큰 값은 미시도.)

### 대응: 램프를 Windows 허용 범위로 클램핑 (코드에 반영)
`build_gamma_ramp(..., clamp_to_windows_limit=True)`(기본값)로 각 엔트리를 선형 ±32000 안으로 잘라낸다. 결과:
- `--apply <i> 1500` 까지도 **OK** (이제 `SetDeviceGammaRamp` 실패 없음).
- 단 시각적 따뜻함은 ≈3300K 부근에서 **포화**(그 아래 슬라이더 값은 더 안 따뜻해짐). f.lux 등도 클램프 미적용 Windows에선 동일.

### 야간 모드(Night light) 충돌
- 별도 검증 필요(현재 켜져있지 않다고 가정). cycle-01에서 토글 상태 감지 후 경고 추가.

## 결론
- 감마 램프 방식 자체는 **동작한다**. 모니터별 개별 적용 OK.
- 시각적 색온도 하한 ≈ **3300K** (레지스트리 우회 무효). 클램핑으로 그 아래 값도 실패 없이 받아들이되 효과는 포화. 단위테스트 13 green.
