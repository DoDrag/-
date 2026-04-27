@echo off
REM ============================================================
REM  GLP-1 Trend - 변경사항 GitHub에 업로드
REM  키워드 수정/코드 변경 후 이 파일 더블클릭하면
REM  자동으로 add + commit + push 됩니다.
REM ============================================================
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo ============================================================
echo  변경사항 GitHub에 업로드
echo ============================================================
echo.

git status --short
echo.

git add .

set /p MSG="커밋 메시지 (엔터만 치면 자동): "
if "%MSG%"=="" set MSG=update %date% %time:~0,5%

git commit -m "%MSG%"
if errorlevel 1 (
    echo.
    echo  변경사항이 없거나 커밋에 실패했습니다.
    pause
    exit /b
)

echo.
echo  GitHub에 푸시 중...
git push

echo.
echo  완료!
echo.
pause
