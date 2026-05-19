@echo off
REM Claude Code SessionStart 훅에서 호출됨.
REM 오늘자 크롤 미수행 시 백그라운드 실행.
chcp 65001 >nul
cd /d "%~dp0"
python "session_start_check.py"
