# GLP-1 Trend — 일일 자동 리서치 크롤러

GLP-1 비만치료제 / 메디컬푸드 / 약사·한약사협회 정책 이슈를 매일 자동 크롤링하고 HTML 리포트를 생성합니다.

## 폴더 구조

```
GLP-1 Trend/
├── research_keywords.json   ← 크롤링 키워드 편집 (사용자 입력)
├── config.json              ← API 키·스케줄·외부 동기화 설정
├── research_crawler.py      ← 메인 크롤러 (Google News RSS + 선택 네이버 API)
├── html_reporter.py         ← HTML 리포트 생성기
├── scheduler.py             ← APScheduler 데몬 (매일 자동 실행)
├── run_once.bat             ← 1회 즉시 실행 (더블클릭)
├── run_scheduler.bat        ← 매일 자동 데몬 실행
├── requirements.txt
├── data/                    ← JSON 누적 (당일 + 마스터)
├── db/                      ← 신규 기사 추적 (seen 링크)
├── logs/                    ← 일별 로그
└── reports/
    ├── research_daily.html        ← 항상 최신 (이 파일을 공유)
    └── research_YYYYMMDD.html     ← 날짜별 스냅샷
```

## 설치 (1회만)

```powershell
cd "C:\Users\JUNGWC\Documents\Claude\GLP-1 Trend"
pip install -r requirements.txt
```

## 사용법

### 1) 즉시 1회 실행
- `run_once.bat` 더블클릭 또는
- `python research_crawler.py`

→ `reports/research_daily.html` 생성됨

### 2) 매일 자동 실행 (포그라운드)
- `run_scheduler.bat` 더블클릭 또는
- `python scheduler.py`

기본 시각: 매일 09:00 메인 + 14:00 보조(메인 실패 시).
시각 변경은 `config.json` → `schedule.main_hour` 등.

### 3) 매일 자동 실행 (백그라운드, PC 부팅 시 자동 시작)
Windows 작업 스케줄러에 등록 (PowerShell 관리자):
```powershell
schtasks /Create /SC DAILY /TN "GLP1_Trend_Crawl" /TR "python \"C:\Users\JUNGWC\Documents\Claude\GLP-1 Trend\research_crawler.py\"" /ST 09:00
```

### 4) 스케줄 상태 확인
```powershell
python scheduler.py --status
```

## 키워드 추가/수정

`research_keywords.json` 을 텍스트 에디터로 열어 `groups` 배열을 편집하세요.

```json
{
  "group_id": "my_topic",        // 영문/숫자/_ (섹션 ID)
  "label": "내 주제",            // 리포트 표시명
  "badge": "dom",                // dom(빨강)/intl(파랑)/policy(주황)
  "lang": "ko",                  // ko 또는 en
  "max_per_keyword": 10,
  "keywords": ["키워드1", "키워드2"]
}
```

저장 후 `run_once.bat` 실행하면 즉시 반영됩니다.

## 외부 컴퓨터(미국 등)에서 접속하기

### 옵션 A — Google Drive 공유 (가장 간단, 추천 🥇)
1. `reports/research_daily.html` 을 Google Drive에 업로드
2. 우클릭 → **공유** → **링크가 있는 모든 사용자** → 링크 복사
3. 그 링크를 형님께 카톡/이메일로 전송 → 브라우저로 열면 끝
4. 매일 자동 갱신: `config.json`의 `external_sync.target_folder`를 Drive 동기화 폴더로 지정 →
   PC가 켜져 있을 때 자동으로 Drive에 업로드됨

```json
"external_sync": {
  "enabled": true,
  "target_folder": "C:\\Users\\JUNGWC\\Google Drive\\GLP-1 Trend"
}
```

### 옵션 B — Netlify Drop (URL이 깔끔, 5분 설정)
1. https://app.netlify.com/drop 접속
2. `reports/research_daily.html` 드래그 앤 드롭
3. 즉시 발급되는 URL (예: `random-name.netlify.app`) 형님께 전송
4. 단점: 매일 자동 갱신은 별도 CLI 설정 필요

### 옵션 C — GitHub Pages (영구 URL, 완전 자동)
1. GitHub 계정 → 새 repository 생성 (예: `glp1-trend`, public)
2. `reports/` 폴더만 push
3. Settings → Pages → Source: `main` branch, `/reports` folder
4. URL: `https://[username].github.io/glp1-trend/research_daily.html`
5. 매일 자동 push: `cron_push.bat` 만들기 (아래 예시) + 작업 스케줄러로 매일 09:30 실행

```batch
@echo off
cd /d "C:\Users\JUNGWC\Documents\Claude\GLP-1 Trend"
git add reports/
git commit -m "daily update %date%"
git push
```

### 옵션 D — 이메일 자동 전송 (옵션 추가 예정)
- 매일 리포트를 PDF/HTML로 첨부해 형님 이메일로 발송
- 구현 필요 시 알려주세요

## 외부 동기화 사용 방법

`config.json` 편집:
```json
"external_sync": {
  "enabled": true,
  "target_folder": "C:\\Users\\JUNGWC\\OneDrive\\GLP-1 Trend"
}
```

크롤 후 `research_daily.html` + 당일 스냅샷이 자동으로 해당 폴더에 복사됩니다.

## 트러블슈팅

- **`research_daily.html`이 비어있음** → `data/articles_master.json` 확인. 비어있으면 RSS 응답 실패 가능 → `logs/` 확인.
- **Windows에서 한글 깨짐** → 파이썬 3.10+ 권장. 코드 내 stdout 인코딩 강제는 처리됨.
- **너무 많은 기사** → `research_keywords.json`의 `max_per_keyword` 줄이기.
- **신규 기사 표시 안 됨** → `db/{group_id}_seen.json` 삭제하면 다음 실행 시 모두 신규로 표시.

## 데이터 정책

- 마스터 파일은 최근 1500건만 유지 (오래된 기사 자동 삭제)
- `seen` 추적은 그룹별 최근 3000개만 유지
- 로그 파일은 일자별로 자동 분리 (`crawl_YYYYMMDD.log`)
