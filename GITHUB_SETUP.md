# GitHub 클라우드 운영 가이드

이 가이드대로 하면 **본인 PC가 꺼져 있어도** 매일 자동 크롤링되고 형님(미국)이 항상 최신 리포트를 볼 수 있습니다.

## 최종 결과 미리보기
- 매일 09:00 KST에 GitHub 서버에서 자동 크롤링
- 결과 HTML이 `https://[본인ID].github.io/glp1-trend/research_daily.html`에 자동 배포
- 형님은 그 URL만 북마크하면 끝
- 키워드 편집은 GitHub 웹 또는 HTML 다운로드 → 업로드

---

## STEP 1. GitHub 계정 + 저장소 생성

1. [github.com](https://github.com) 접속 → Sign up (무료)
2. 로그인 후 우측 상단 `+` → **New repository** 클릭
3. 입력:
   - **Repository name**: `glp1-trend`
   - **Public** 선택 (GitHub Actions·Pages 무제한 무료)
   - "Add a README file" 체크 X (이미 있으니까)
   - `.gitignore`, license 모두 None
4. **Create repository** 클릭
5. 생성된 페이지의 URL을 메모: `https://github.com/[본인ID]/glp1-trend`

> ⚠️ **Private repo로 하고 싶으면**: 그래도 GitHub Actions 월 2,000분 무료 (매일 5분 사용 = 월 150분)이라 충분. 단, GitHub Pages는 무료 Private repo에선 안 되므로 Public 권장.

---

## STEP 2. Git 설치 (1회만, 이미 있으면 스킵)

PowerShell에서 확인:
```powershell
git --version
```

없으면 https://git-scm.com/download/win 에서 다운로드 → 기본값으로 설치.

설치 직후 본인 정보 등록:
```powershell
git config --global user.name "본인 이름"
git config --global user.email "본인 이메일"
```

---

## STEP 3. 로컬 폴더를 GitHub에 업로드

**PowerShell** 또는 **Git Bash**에서:

```powershell
cd "C:\Users\JUNGWC\Documents\Claude\GLP-1 Trend"

# Git 초기화
git init -b main

# 모든 파일 스테이징
git add .

# 첫 커밋
git commit -m "initial: GLP-1 Trend 크롤러"

# GitHub 저장소 연결 (URL의 [본인ID] 부분만 본인 것으로 교체)
git remote add origin https://github.com/[본인ID]/glp1-trend.git

# 푸시
git push -u origin main
```

> 첫 푸시 시 GitHub 로그인 창이 뜸 → 브라우저에서 GitHub 인증 (Personal Access Token 자동 처리)

---

## STEP 4. GitHub Actions 실행 권한 확인

1. 브라우저로 본인 저장소 접속: `https://github.com/[본인ID]/glp1-trend`
2. **Settings** 탭 → 좌측 **Actions** → **General**
3. "Workflow permissions" 섹션:
   - ✅ **Read and write permissions** 선택
   - **Save** 클릭

이게 없으면 자동 commit/push가 권한 오류로 실패합니다.

---

## STEP 5. GitHub Pages 활성화

1. 같은 저장소 **Settings** 탭
2. 좌측 **Pages**
3. **Source** 드롭다운: **GitHub Actions** 선택
4. (저장 버튼 없음 — 자동 적용)

> 워크플로 파일 안에 이미 Pages 배포 단계가 들어 있으므로, 첫 워크플로 실행 후 자동으로 활성화됩니다.

---

## STEP 6. 첫 실행 (수동 트리거)

1. 저장소 **Actions** 탭 클릭
2. 좌측 "Daily Crawl" 워크플로 선택
3. 우측 **Run workflow** 버튼 클릭 → **Run workflow** (초록 버튼)
4. 잠시 후 새 실행이 표시됨 → 클릭하면 진행 상황 실시간 확인 가능
5. 약 2~5분 후 두 잡 모두 ✅ 초록색이 되면 성공

### 결과 확인
- 저장소의 `reports/research_daily.html` 파일이 새로 갱신되어 있음
- **Settings → Pages** 페이지에 URL 표시됨: `https://[본인ID].github.io/glp1-trend/`
- URL 끝에 `research_daily.html` 붙여서 접속:
  ```
  https://[본인ID].github.io/glp1-trend/research_daily.html
  ```

이게 형님께 보낼 영구 URL입니다.

---

## STEP 7. 매일 자동 실행 확인

이미 워크플로에 cron이 들어 있어서 **자동 동작**합니다.

```yaml
schedule:
  - cron: '0 0 * * *'   # 매일 00:00 UTC = 09:00 KST
```

### cron 시각 변경하고 싶으면
`.github/workflows/daily.yml` 파일을 GitHub 웹에서 직접 편집:
- `'0 0 * * *'` 의 첫 두 숫자가 `분 시` (UTC 기준)
- 한국 시간 09:00 = UTC 00:00 → `0 0`
- 한국 시간 14:00 = UTC 05:00 → `0 5`
- 한국 시간 18:30 = UTC 09:30 → `30 9`

---

## STEP 8. 키워드 편집 — 두 가지 방법

### 방법 A: GitHub 웹에서 직접 편집 (가장 빠름)
1. 저장소에서 `research_keywords.json` 파일 클릭
2. 우측 상단 **연필 아이콘 (Edit)** 클릭
3. JSON 직접 수정 (브라우저에 문법 체크 됨)
4. 하단에 commit 메시지 적고 **Commit changes**
5. 다음 09:00 KST 또는 수동 실행으로 반영

### 방법 B: HTML에서 편집기로 수정 후 업로드
1. `https://[본인ID].github.io/glp1-trend/research_daily.html` 접속
2. ⚙️ 키워드 편집 → 수정 → 💾 JSON 다운로드 (받은 파일은 `Downloads/research_keywords.json`)
3. GitHub 저장소 → `research_keywords.json` 파일 클릭
4. 연필 아이콘 옆 **점 3개 (⋯)** → **Delete this file** → Commit (또는 그냥 다음 단계로 덮어쓰기)
5. 저장소 메인으로 가서 **Add file → Upload files**
6. 받은 `research_keywords.json` 드래그 앤 드롭 → Commit
7. 다음 실행에 반영

> 형님(미국)도 GitHub 계정만 있으면 위 방법 모두 가능. 협업자(Collaborator)로 추가하면 형님도 직접 편집/커밋 가능.

### 형님을 협업자로 추가하기
1. 저장소 **Settings** → **Collaborators** → **Add people**
2. 형님 GitHub ID 또는 이메일 입력
3. 형님 메일로 초대 도착 → 수락하면 끝

---

## STEP 9. 즉시 다시 크롤하고 싶을 때

GitHub Actions 탭 → "Daily Crawl" → **Run workflow** 클릭하면 즉시 실행. 약 2~5분 후 결과 반영.

---

## 트러블슈팅

| 증상 | 원인 / 해결 |
|------|----------|
| 워크플로가 빨간색(❌) | Actions 탭에서 로그 확인. 보통 STEP 4의 "Read and write permissions" 미설정 |
| Pages URL 404 | STEP 5에서 Source가 "GitHub Actions"인지 확인. 첫 워크플로가 성공해야 활성화됨 |
| 매일 00:00 UTC 정시에 안 됨 | GitHub Actions cron은 정확하지 않음(최대 ~30분 지연 가능) — 정상 |
| 키워드 수정 후 반영 안 됨 | 다음 09:00 KST 자동 실행 또는 수동 트리거 필요. 즉시 보고 싶으면 Actions에서 Run workflow |
| `git push` 실패 — 권한 거부 | Personal Access Token 필요. 첫 push 시 GitHub Desktop 사용 권장: https://desktop.github.com |

---

## (선택) GitHub Desktop으로 더 쉽게

git 명령어가 어려우면 [GitHub Desktop](https://desktop.github.com) 사용:
1. 설치 후 GitHub 계정 로그인
2. **File → Add local repository** → `GLP-1 Trend` 폴더 선택
3. **Publish repository** 클릭 → 이름 `glp1-trend`, Public 선택 → Publish
4. STEP 4부터 동일하게 진행

이후 키워드 편집 후 GitHub Desktop에서 "Commit" + "Push origin" 클릭만으로 업로드 가능.

---

## 비용 정리

- GitHub 계정: **무료**
- Public 저장소: **무료**
- GitHub Actions (Public): **무제한 무료**
- GitHub Pages (Public): **무료** (100GB/월 대역폭)
- 도메인: github.io 서브도메인 무료. 본인 도메인 연결도 무료(도메인 구입비만 별도)

→ **월 0원**으로 PC 꺼진 상태에서도 24/7 운영됩니다.
