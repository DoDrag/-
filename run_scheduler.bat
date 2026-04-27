@echo off
REM GLP-1 Trend - 매일 자동 크롤 데몬 실행
REM 이 창을 닫으면 스케줄러도 멈춥니다. 백그라운드 상시 실행은 작업 스케줄러 등록을 권장.

cd /d "%~dp0"
python scheduler.py
pause
