# -*- coding: utf-8 -*-
"""
GLP-1 Trend / scheduler.py
APScheduler 기반 매일 자동 크롤 데몬.

실행:
  python scheduler.py            # 포그라운드 데몬 실행 (매일 정해진 시각에 자동 실행)
  python scheduler.py --once     # 즉시 1회 실행 후 종료
  python scheduler.py --status   # 다음 예정 시각 확인 후 종료

설정은 config.json의 schedule 항목에서 변경:
  schedule.main_hour / main_minute       — 메인 실행 시각 (기본 09:00)
  schedule.fallback_hour / fallback_minute — 보조 실행 시각 (기본 14:00, 메인 실패 시)
"""

import sys
import io
if not getattr(sys.stdout, "_glp1_utf8_wrapped", False):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stdout._glp1_utf8_wrapped = True
if not getattr(sys.stderr, "_glp1_utf8_wrapped", False):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    sys.stderr._glp1_utf8_wrapped = True

import argparse
import json
import logging
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from research_crawler import run_crawl, sync_to_external, load_config
from html_reporter import generate_report

BASE_DIR = Path(__file__).parent
LOG_DIR = BASE_DIR / "logs"
SCHED_STATE = BASE_DIR / "schedule_state.json"
LOG_DIR.mkdir(exist_ok=True)

KST = timezone(timedelta(hours=9))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "scheduler.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("scheduler")


def _save_state(date_str: str, ok: bool):
    state = {}
    if SCHED_STATE.exists():
        try:
            state = json.load(open(SCHED_STATE, encoding="utf-8"))
        except Exception:
            pass
    state[date_str] = {"success": ok, "ran_at": datetime.now(KST).isoformat()}
    # 최근 60일만 유지
    if len(state) > 60:
        keep = sorted(state.keys())[-60:]
        state = {k: state[k] for k in keep}
    with open(SCHED_STATE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def _today_str() -> str:
    return datetime.now(KST).strftime("%Y-%m-%d")


def _today_succeeded() -> bool:
    if not SCHED_STATE.exists():
        return False
    try:
        state = json.load(open(SCHED_STATE, encoding="utf-8"))
        return state.get(_today_str(), {}).get("success", False)
    except Exception:
        return False


def git_push_results():
    """크롤 결과를 GitHub에 자동 push. 충돌 시 pull --rebase 후 재시도(최대 3회).
    config.json schedule.auto_push=false 면 건너뜀.
    .git 폴더가 없으면(=git repo가 아니면) 조용히 건너뜀."""
    if not (BASE_DIR / ".git").exists():
        logger.info("[push] git repo 아님 — 건너뜀")
        return
    cfg = load_config()
    if not cfg.get("schedule", {}).get("auto_push", True):
        logger.info("[push] auto_push=false — 건너뜀")
        return
    try:
        check = subprocess.run(
            ["git", "status", "--porcelain", "data", "db", "reports"],
            cwd=BASE_DIR, capture_output=True, text=True, encoding="utf-8",
        )
        if not check.stdout.strip():
            logger.info("[push] 변경사항 없음 — 건너뜀")
            return

        subprocess.run(["git", "add", "data", "db", "reports"], cwd=BASE_DIR, check=True)
        msg = f"daily update: {datetime.now(KST):%Y-%m-%d %H:%M KST} (local scheduler)"
        commit = subprocess.run(
            ["git", "commit", "-m", msg], cwd=BASE_DIR, capture_output=True, text=True, encoding="utf-8",
        )
        if commit.returncode != 0:
            logger.info(f"[push] 커밋할 변경 없음: {commit.stdout.strip()}")
            return

        for attempt in range(1, 4):
            push = subprocess.run(["git", "push", "origin", "main"], cwd=BASE_DIR)
            if push.returncode == 0:
                logger.info(f"[push] 성공 (시도 {attempt}/3)")
                return
            logger.warning(f"[push] 실패 — pull --rebase 후 재시도 ({attempt}/3)")
            subprocess.run(["git", "pull", "--rebase", "origin", "main"], cwd=BASE_DIR)
        logger.error("[push] 3회 재시도 실패 — 다음 실행 때 다시 시도됩니다")
    except Exception as e:
        logger.exception(f"[push] 예외: {e}")


def job_main():
    logger.info("─" * 50)
    logger.info("[메인 잡] 시작")
    try:
        run_crawl()
        out_files = generate_report()
        sync_to_external(out_files)
        _save_state(_today_str(), True)
        logger.info("[메인 잡] 크롤 성공")
        git_push_results()
        logger.info("[메인 잡] 종료")
    except Exception as e:
        logger.exception(f"[메인 잡] 실패: {e}")
        _save_state(_today_str(), False)


def job_fallback():
    """오늘 메인이 성공했으면 건너뜀, 아니면 재시도."""
    if _today_succeeded():
        logger.info("[보조 잡] 오늘 메인 성공 — 건너뜀")
        return
    logger.info("[보조 잡] 오늘 메인 미성공 — 재시도 시작")
    job_main()


def run_status():
    cfg = load_config()
    sch = cfg.get("schedule", {})
    mh = sch.get("main_hour", 9)
    mm = sch.get("main_minute", 0)
    fh = sch.get("fallback_hour", 14)
    fm = sch.get("fallback_minute", 0)
    print("─" * 60)
    print(f"GLP-1 Trend 스케줄 현황")
    print("─" * 60)
    print(f"  메인 실행:   매일 {mh:02d}:{mm:02d} (KST)")
    print(f"  보조 실행:   매일 {fh:02d}:{fm:02d} (메인 실패 시)")
    print(f"  현재 시각:   {datetime.now(KST):%Y-%m-%d %H:%M:%S} KST")
    print(f"  오늘 상태:   {'✓ 성공' if _today_succeeded() else '× 미실행/실패'}")
    if SCHED_STATE.exists():
        try:
            state = json.load(open(SCHED_STATE, encoding="utf-8"))
            recent = sorted(state.keys())[-7:]
            print(f"  최근 7일:")
            for d in recent:
                mark = "✓" if state[d].get("success") else "×"
                print(f"    {d}  {mark}")
        except Exception:
            pass
    print("─" * 60)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--once", action="store_true", help="즉시 1회 실행 후 종료")
    p.add_argument("--status", action="store_true", help="스케줄 현황 출력 후 종료")
    args = p.parse_args()

    if args.status:
        run_status()
        return

    if args.once:
        job_main()
        return

    cfg = load_config()
    sch = cfg.get("schedule", {})
    mh = sch.get("main_hour", 9)
    mm = sch.get("main_minute", 0)
    fh = sch.get("fallback_hour", 14)
    fm = sch.get("fallback_minute", 0)

    scheduler = BlockingScheduler(timezone="Asia/Seoul")
    scheduler.add_job(job_main, CronTrigger(hour=mh, minute=mm),
                      id="main", name="메인 크롤링")
    scheduler.add_job(job_fallback, CronTrigger(hour=fh, minute=fm),
                      id="fallback", name="보조 크롤링")

    logger.info("=" * 60)
    logger.info(f"GLP-1 Trend 스케줄러 시작")
    logger.info(f"  메인 실행: 매일 {mh:02d}:{mm:02d} KST")
    logger.info(f"  보조 실행: 매일 {fh:02d}:{fm:02d} KST")
    logger.info(f"  중지하려면 Ctrl+C")
    logger.info("=" * 60)

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("스케줄러 중지")


if __name__ == "__main__":
    main()
