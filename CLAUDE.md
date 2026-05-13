# nightshift — 개발 기록 (CLAUDE.md)

Windows 멀티모니터 색온도 제어 앱 (f.lux 클론). Python + tkinter, PyInstaller 단일 exe(≤40MB)로 빌드해 GitHub Releases 배포.

## 작업 방식 — PDCA 사이클
- 모든 작업은 `cycles/cycle-NN/` 단위로 진행. 각 폴더에 `plan.md`(목표·범위·검증기준) → `do.md`(작업 로그) → `check.md`(검증 결과·발견 이슈) → `act.md`(다음 사이클 반영)를 채운다.
- 사이클 종료 시: 이 파일의 "사이클 로그"에 한 줄 추가 + 커밋(작성자 `hanmailco34 <hanmailco34@naver.com>`, 이 레포 로컬 git config에 설정됨).
- 다음 사이클은 직전 `act.md`의 "착수 항목"에서 시작.

## 프로젝트 구조
```
src/nightshift/
  __init__.py        # 버전, Kelvin 상수
  __main__.py        # 엔트리포인트(현재: 모니터 진단 / cycle-01에서 UI)
  color/temperature.py  # kelvin_to_rgb(k) -> (r,g,b) 배율 (Tanner Helland)
  color/gamma.py        # build_gamma_ramp / identity_ramp / apply_kelvin / reset + CLI
  display/monitors.py   # list_monitors() -> [Monitor], find_by_device()
  config/ schedule/ platform/ ui/   # cycle-01~02에서 채움
tests/                 # pytest (temperature, gamma ramp)
cycles/cycle-NN/       # plan/do/check/act
```

## 개발 셋업
- `pip install -e .` (editable) → `python -m nightshift`, `python -m nightshift.color.gamma --help`
- `python -m pytest`

## 핵심 제약 (cycle-00에서 실측 — `cycles/cycle-00/check.md` 참고)
- 색온도 제어 = GPU 감마 램프(`SetDeviceGammaRamp`). Windows는 선형에서 ±0x8000 넘게 벗어난 램프를 거부 → **기본 상태 시각적 하한 ≈ 3300K**.
- `HKLM\...\ICM\GdiICMGammaRange=256` + **실제 Windows 재부팅** 시 그 제한이 풀려 1500K까지 시각 적용 확인됨(`scripts/probe_unclamped.py`로 재현). 관리자 권한·재부팅 필요 → 일반 사용자에겐 강요 안 함.
- 채택안 (**C**): 기본은 클램핑(`apply_kelvin` 항상 성공, ≈3300K에서 효과 포화). 옵션으로 **"확장 색온도 범위"** 토글 — 활성화 시 안내 다이얼로그 → 관리자 권한으로 레지스트리 설정 + 재부팅 안내 → 이후 클램핑 끄고 풀범위 사용. (cycle-01에서 구현)
- `SetDeviceGammaRamp`/`apply_kelvin` 반환값(성공/실패)을 항상 확인할 것 (HDR/드라이버 거부 가능).

## 사이클 로그
- **cycle-00** (색온도 제어 PoC) — 레포 스캐폴딩 + temperature/gamma/monitors 구현 + 단위테스트 11 green. 모니터 3대 열거 OK, 색온도 적용 OK(단 ≥~3300K), Windows 감마 클램프 제약 발견·문서화. → 다음: cycle-01 UI + config + 모니터별 개별 설정.
