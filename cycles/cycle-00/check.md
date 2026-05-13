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
Windows는 `SetDeviceGammaRamp`에 넘긴 램프의 각 엔트리가 선형 램프에서 일정 범위(약 ±32768/65536) 이상 벗어나면 거부한다. 색온도를 낮출수록 파란 채널 상단(`blue[~200]` 부근)이 선형에서 크게 떨어져 이 한계를 넘는다 → 약 **3300K 아래로는 기본 상태에서 적용 불가**.
- HDR/드라이버 이슈가 아니라 OS 차원의 제약. 3대 모두 동일 임계값(≈3300K)을 보임.
- `HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\ICM\GdiICMGammaRange` 레지스트리 값은 **현재 없음**(기본 = 제한 범위). 이 DWORD를 `256`으로 설정하고 재부팅하면 허용 편차가 넓어진다는 것이 커뮤니티(f.lux 설치 프로그램, gammy 등)의 알려진 우회법 — **단, 관리자 권한 필요**, 이 PC에서는 비관리자 셸이라 적용/검증 못함(`Requested registry access is not allowed`).

### 야간 모드(Night light) 충돌
- 별도 검증 필요(현재 켜져있지 않다고 가정). cycle-01에서 토글 상태 감지 후 경고 추가.

## 결론
- 감마 램프 방식 자체는 **동작한다**. 모니터별 개별 적용도 된다.
- 다만 **2700K 같은 강한 야간값은 레지스트리 설정(관리자) 없이는 불가**. 기본 동작 한계 ≈ 3300K.
