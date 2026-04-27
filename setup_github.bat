@echo off
REM ============================================================
REM  GLP-1 Trend - GitHub 첫 설정 스크립트
REM  이 파일을 더블클릭하면 git 초기화 + 첫 커밋까지 자동 진행됩니다.
REM  마지막에 "git push" 명령어만 직접 실행하시면 됩니다.
REM ============================================================
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo ============================================================
echo  GLP-1 Trend - GitHub 셋업 시작
echo ============================================================
echo.

REM 1. Git 사용자 정보 확인
for /f "tokens=*" %%a in ('git config --global user.name 2^>nul') do set GIT_NAME=%%a
for /f "tokens=*" %%a in ('git config --global user.email 2^>nul') do set GIT_EMAIL=%%a

if "%GIT_NAME%"=="" (
    echo [필수 정보 입력]
    set /p GIT_NAME_IN="GitHub 사용자 이름을 입력하세요: "
    git config --global user.name "!GIT_NAME_IN!"
    setlocal enabledelayedexpansion
)
if "%GIT_EMAIL%"=="" (
    set /p GIT_EMAIL_IN="GitHub 이메일을 입력하세요: "
    git config --global user.email "!GIT_EMAIL_IN!"
)

echo  Git 사용자:
git config --global user.name
echo  Git 이메일:
git config --global user.email
echo.

REM 2. Git repo 초기화
if exist .git (
    echo  [SKIP] 이미 git repo 입니다.
) else (
    echo  [1/4] git init 실행...
    git init -b main
)

REM 3. 모든 파일 스테이징
echo  [2/4] 파일 스테이징...
git add .

REM 4. 첫 커밋
echo  [3/4] 첫 커밋 생성...
git commit -m "initial: GLP-1 Trend crawler" 2>nul
if errorlevel 1 echo    (이미 커밋되어 있어서 스킵)

REM 5. 안내
echo.
echo ============================================================
echo  로컬 git 셋업 완료!
echo ============================================================
echo.
echo  이제 다음 두 명령어만 실행하면 GitHub에 업로드됩니다.
echo  (먼저 GitHub.com에서 'glp1-trend' 라는 빈 저장소를 만들어두세요)
echo.
echo  ▶ 명령어를 복사해서 PowerShell 또는 이 창에서 실행:
echo.
echo     git remote add origin https://github.com/[본인ID]/glp1-trend.git
echo     git push -u origin main
echo.
echo  [본인ID] 부분을 실제 GitHub 아이디로 바꾸세요.
echo  예: git remote add origin https://github.com/jungwoo123/glp1-trend.git
echo.
echo ============================================================
echo.
pause
