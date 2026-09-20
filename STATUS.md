# WARNO KoreanPatch 현황

## 현재 기준

기존 번역 초안과 임시 산출물을 폐기한 뒤, 게임 설치 데이터에서 캐시 없이 새로 추출했다. 새 결과는 `FreshExtraction/`에 보관하고 `English/`와 해시를 대조했다.

| 파일 | 원본 물리 행 수 | 현재 상태 |
|---|---:|---:|---:|
| `COMPANIES.csv` | 9,343 | 번역 초안 삭제, 원본만 보존 |
| `PLATOONS.csv` | 8,044 | 번역 초안 삭제, 원본만 보존 |
| `UNITS.csv` | 9,449 | 번역 초안 삭제, 원본만 보존 |
| `INTERFACE_INGAME.csv` | 759 | 번역 초안 삭제, 원본만 보존 |
| `INTERFACE_OUTGAME.csv` | 655 | 번역 초안 삭제, 원본만 보존 |

## 검증 결과

- 새 추출 CSV 5개는 `English/`와 모두 SHA-256이 일치했다.
- 새 리포트는 `FreshExtraction/EXTRACTION_REPORT.txt`에 저장했다.
- `UNRESOLVED_*.csv`는 DIC에만 존재하는 해시 진단용이며 번역 파일이 아니다.
- `COMPANIES`·`PLATOONS`는 현재 CSV 토큰이 모두 DIC에 나타났고, unresolved는 추가/중복 DIC 엔트리다.
- `INTERFACE_*` unresolved는 일부 중복 문자열과 현재 CSV에 없는 레거시·정적 DIC 문자열이 섞인 결과다.
- `English/` 원본과 활성 모드의 빈 템플릿 CSV는 수정하지 않았다.
- 프로젝트 `Mods/KoreanPatch/Gen/`은 삭제했으며, 이전 생성 사전은 최신 상태로 간주하지 않는다.
- `English/` 원본 파일은 수정하지 않았다.

## 다음 번역 작업 규칙

- 외부 번역기·번역 API·로컬 번역기를 사용하지 않는다.
- CSV를 행별로 직접 번역하고, 토큰·변수·마크업·줄바꿈을 보존한다.
- 번역이 끝난 뒤에만 CSV를 활성 모드에 복사하고 WARNO `.dic`를 한 번 생성한다.
