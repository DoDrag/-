@echo off
REM GLP-1 Trend - 1회 즉시 크롤 + 리포트 생성
REM 더블클릭하면 바로 실행됩니다.

cd /d "%~dp0"
python research_crawler.py
echo.
echo ============================================================
echo  완료! reports\research_daily.html 을 브라우저로 여세요.
echo ============================================================
pause
