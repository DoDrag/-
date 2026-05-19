# -*- coding: utf-8 -*-
"""
GLP-1 Trend / session_start_check.py

Claude Code SessionStart 훅에서 호출됨.
- 오늘자 articles_YYYYMMDD.json이 존재하면 → 스킵 (이미 크롤 완료)
- 없으면 → scheduler.py --once를 백그라운드(분리 프로세스)로 실행
  → 세션 시작이 블로킹되지 않음 (1초 내 리턴)

이중화 안전망:
  09:00 KST GitHub Actions + Windows Task Scheduler가 둘 다 실패한 경우의 fallback.
"""
import sys
import io
if not getattr(sys.stdout, "_glp1_utf8_wrapped", False):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stdout._glp1_utf8_wrapped = True
if not getattr(sys.stderr, "_glp1_utf8_wrapped", False):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    sys.stderr._glp1_utf8_wrapped = True

import json
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path

KST = timezone(timedelta(hours=9))
BASE = Path(__file__).parent
today_str = datetime.now(KST).strftime("%Y%m%d")
today_file = BASE / "data" / f"articles_{today_str}.json"

# 우선 원격에서 최신 상태 fetch (다른 자동화가 push했을 수 있음 — 충돌 없는 빠른 fetch만)
try:
    subprocess.run(
        ["git", "-C", str(BASE), "fetch", "origin", "main", "--quiet"],
        capture_output=True, timeout=10
    )
    # 로컬 작업트리 깨끗할 때만 pull
    status = subprocess.run(
        ["git", "-C", str(BASE), "status", "--porcelain"],
        capture_output=True, text=True, timeout=5
    )
    if not status.stdout.strip():
        subprocess.run(
            ["git", "-C", str(BASE), "pull", "--rebase", "origin", "main", "--quiet"],
            capture_output=True, timeout=20
        )
except Exception:
    pass  # 네트워크 문제 등 — 무시하고 로컬 상태로 판단

# 오늘 파일 있으면 스킵
if today_file.exists():
    print(f"[GLP-1 Trend] 오늘({today_str}) 이미 크롤됨 — 스킵")
    sys.exit(0)

# 없으면 백그라운드로 실행 (세션 시작 블로킹 방지)
print(f"[GLP-1 Trend] 오늘({today_str}) 미크롤 — 백그라운드 크롤 시작")
try:
    # Windows: DETACHED_PROCESS | CREATE_NO_WINDOW
    DETACHED = 0x00000008
    NO_WINDOW = 0x08000000
    subprocess.Popen(
        [sys.executable, str(BASE / "scheduler.py"), "--once"],
        cwd=str(BASE),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=DETACHED | NO_WINDOW,
        close_fds=True,
    )
    print("[GLP-1 Trend] 백그라운드 실행 시작 — 결과는 logs/ 폴더 확인")
except Exception as e:
    print(f"[GLP-1 Trend] 백그라운드 실행 실패: {e}", file=sys.stderr)
