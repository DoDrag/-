# -*- coding: utf-8 -*-
"""
GLP-1 Trend / research_crawler.py
키워드 그룹별 뉴스 크롤러 — Google News RSS + (선택) 네이버 검색 API

사용:
  python research_crawler.py                # 1회 크롤 + HTML 리포트 갱신
  python research_crawler.py --keywords-only  # 크롤만 (리포트 미생성)
  python research_crawler.py --report-only    # 기존 데이터로 리포트만 재생성

데이터 흐름:
  research_keywords.json  →  Google News RSS (그룹·키워드별)
                          →  data/articles_YYYYMMDD.json   (당일 누적)
                          →  data/articles_master.json     (전체 중복제거 누적)
                          →  reports/research_daily.html   (최신 리포트, 항상 같은 파일명)
                          →  reports/research_YYYYMMDD.html (날짜별 스냅샷)
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
import re
import time
import urllib.parse
import shutil
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from xml.etree import ElementTree as ET

import requests

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DB_DIR = BASE_DIR / "db"
LOG_DIR = BASE_DIR / "logs"
REPORTS_DIR = BASE_DIR / "reports"
KW_PATH = BASE_DIR / "research_keywords.json"
CFG_PATH = BASE_DIR / "config.json"

for d in (DATA_DIR, DB_DIR, LOG_DIR, REPORTS_DIR):
    d.mkdir(exist_ok=True)

# ─── 로깅 ─────────────────────────────────────────────────────────────────────
LOG_FILE = LOG_DIR / f"crawl_{datetime.now().strftime('%Y%m%d')}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("research_crawler")

KST = timezone(timedelta(hours=9))


# ─── 설정 로드 ────────────────────────────────────────────────────────────────
def load_keywords() -> dict:
    with open(KW_PATH, encoding="utf-8") as f:
        return json.load(f)


def load_config() -> dict:
    if not CFG_PATH.exists():
        return {}
    with open(CFG_PATH, encoding="utf-8") as f:
        return json.load(f)


# ─── Google News RSS 크롤러 ───────────────────────────────────────────────────
def google_news_rss(keyword: str, lang: str = "ko", max_items: int = 10) -> list[dict]:
    """
    Google News RSS로 키워드 검색.
    lang='ko': 한국어 결과 / 'en': 영어 결과
    """
    if lang == "ko":
        hl, gl, ceid = "ko", "KR", "KR:ko"
    else:
        hl, gl, ceid = "en-US", "US", "US:en"

    q = urllib.parse.quote(keyword)
    url = f"https://news.google.com/rss/search?q={q}&hl={hl}&gl={gl}&ceid={ceid}"

    try:
        resp = requests.get(url, timeout=15, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
        })
        resp.raise_for_status()
    except Exception as e:
        logger.warning(f"  RSS 요청 실패 [{keyword}]: {e}")
        return []

    items = []
    try:
        root = ET.fromstring(resp.content)
    except ET.ParseError as e:
        logger.warning(f"  RSS 파싱 실패 [{keyword}]: {e}")
        return []

    for it in root.findall(".//item")[:max_items]:
        title = (it.findtext("title") or "").strip()
        link = (it.findtext("link") or "").strip()
        pub = (it.findtext("pubDate") or "").strip()
        desc = (it.findtext("description") or "").strip()
        source_el = it.find("source")
        source_name = source_el.text.strip() if source_el is not None and source_el.text else ""

        # description의 HTML 태그 제거 → 본문 요약
        desc_text = re.sub(r"<[^>]+>", " ", desc)
        desc_text = re.sub(r"\s+", " ", desc_text).strip()

        # 제목에서 끝의 " - 매체명" 분리
        if " - " in title and not source_name:
            parts = title.rsplit(" - ", 1)
            if len(parts) == 2:
                title, source_name = parts[0].strip(), parts[1].strip()

        # 발행시각 ISO 변환
        try:
            dt = parsedate_to_datetime(pub).astimezone(KST)
            pub_iso = dt.isoformat()
            pub_display = dt.strftime("%Y-%m-%d %H:%M")
        except Exception:
            pub_iso = ""
            pub_display = pub

        items.append({
            "title": title,
            "link": link,
            "source": source_name or "Google News",
            "summary": desc_text[:300],
            "pub_iso": pub_iso,
            "pub_display": pub_display,
        })
    return items


# ─── 네이버 검색 API (선택, 키 있을 때만) ────────────────────────────────────
def naver_news_api(keyword: str, client_id: str, client_secret: str,
                   max_items: int = 10) -> list[dict]:
    url = "https://openapi.naver.com/v1/search/news.json"
    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
    }
    params = {"query": keyword, "display": max_items, "sort": "date"}
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.warning(f"  네이버 API 실패 [{keyword}]: {e}")
        return []

    items = []
    for it in data.get("items", []):
        title = re.sub(r"<[^>]+>", "", it.get("title", "")).strip()
        desc = re.sub(r"<[^>]+>", "", it.get("description", "")).strip()
        link = it.get("originallink") or it.get("link", "")
        pub = it.get("pubDate", "")
        try:
            dt = parsedate_to_datetime(pub).astimezone(KST)
            pub_iso = dt.isoformat()
            pub_display = dt.strftime("%Y-%m-%d %H:%M")
        except Exception:
            pub_iso, pub_display = "", pub
        items.append({
            "title": title,
            "link": link,
            "source": "Naver",
            "summary": desc[:300],
            "pub_iso": pub_iso,
            "pub_display": pub_display,
        })
    return items


# ─── 그룹 단위 크롤 ───────────────────────────────────────────────────────────
def crawl_group(group: dict, naver_id: str = "", naver_secret: str = "") -> list[dict]:
    """
    그룹의 모든 키워드를 돌며 기사 수집. 그룹 메타데이터 부착.
    """
    gid = group["group_id"]
    label = group["label"]
    badge = group.get("badge", "dom")
    lang = group.get("lang", "ko")
    max_per_kw = group.get("max_per_keyword", 10)
    keywords = group.get("keywords", [])

    logger.info(f"[그룹] {label} ({gid}) — 키워드 {len(keywords)}개, lang={lang}")

    collected: list[dict] = []
    for kw in keywords:
        items = google_news_rss(kw, lang=lang, max_items=max_per_kw)

        # 네이버 API 키가 있고 한국어이면 보완 (중복은 후단계에서 제거)
        if lang == "ko" and naver_id and naver_secret:
            items += naver_news_api(kw, naver_id, naver_secret, max_items=max_per_kw)

        for it in items:
            it["group_id"] = gid
            it["group_label"] = label
            it["badge"] = badge
            it["keyword"] = kw
        collected.extend(items)
        logger.info(f"  └ '{kw}': {len(items)}건")
        time.sleep(0.5)  # 부하 방지

    # 링크 기준 중복 제거 (같은 URL이 여러 키워드에 걸리면 1건만)
    seen_links = set()
    deduped = []
    for it in collected:
        key = it.get("link", "").split("?")[0]  # 쿼리 제거 후 비교
        if not key or key in seen_links:
            continue
        seen_links.add(key)
        deduped.append(it)

    logger.info(f"  → 그룹 수집 {len(collected)}건 → 중복제거 후 {len(deduped)}건")
    return deduped


# ─── diff 추적 (신규 기사 마킹) ──────────────────────────────────────────────
def _seen_path(group_id: str) -> Path:
    return DB_DIR / f"{group_id}_seen.json"


def _load_seen(group_id: str) -> set:
    p = _seen_path(group_id)
    if p.exists():
        try:
            return set(json.load(open(p, encoding="utf-8")))
        except Exception:
            pass
    return set()


def _save_seen(group_id: str, links: set):
    p = _seen_path(group_id)
    lst = sorted(links)[-3000:]  # 최근 3000개만 유지
    with open(p, "w", encoding="utf-8") as f:
        json.dump(lst, f, ensure_ascii=False)


def mark_new_items(items: list[dict]) -> list[dict]:
    """이전 실행에 없던 기사에 is_new=True 부착."""
    by_group: dict[str, list[dict]] = {}
    for it in items:
        by_group.setdefault(it["group_id"], []).append(it)

    for gid, lst in by_group.items():
        seen = _load_seen(gid)
        new_links = set()
        for it in lst:
            link = it.get("link", "").split("?")[0]
            it["is_new"] = link and link not in seen
            if link:
                new_links.add(link)
        _save_seen(gid, seen | new_links)

    return items


# ─── 데이터 저장 ──────────────────────────────────────────────────────────────
def save_articles(articles: list[dict]) -> tuple[Path, Path]:
    """당일 파일 + 마스터 파일 누적 저장."""
    today = datetime.now(KST).strftime("%Y%m%d")
    daily_path = DATA_DIR / f"articles_{today}.json"
    master_path = DATA_DIR / "articles_master.json"

    # 당일 파일 — 덮어쓰기 (같은 날 여러 번 돌 수 있음)
    with open(daily_path, "w", encoding="utf-8") as f:
        json.dump({
            "crawled_at": datetime.now(KST).isoformat(),
            "count": len(articles),
            "articles": articles,
        }, f, ensure_ascii=False, indent=2)

    # 마스터 — 누적 후 링크 기준 중복 제거 + 최신 1500건 유지
    master = []
    if master_path.exists():
        try:
            master = json.load(open(master_path, encoding="utf-8")).get("articles", [])
        except Exception:
            master = []

    combined = articles + master
    seen = set()
    deduped = []
    for it in combined:
        key = it.get("link", "").split("?")[0]
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(it)

    deduped.sort(key=lambda x: x.get("pub_iso", ""), reverse=True)
    deduped = deduped[:1500]

    with open(master_path, "w", encoding="utf-8") as f:
        json.dump({
            "updated_at": datetime.now(KST).isoformat(),
            "count": len(deduped),
            "articles": deduped,
        }, f, ensure_ascii=False, indent=2)

    return daily_path, master_path


# ─── 메인 크롤 ────────────────────────────────────────────────────────────────
def run_crawl() -> list[dict]:
    cfg = load_config()
    kw_data = load_keywords()
    groups = kw_data.get("groups", [])

    naver_id = cfg.get("naver_client_id", "")
    naver_secret = cfg.get("naver_client_secret", "")

    logger.info("=" * 60)
    logger.info(f"GLP-1 Trend 크롤 시작 — {datetime.now(KST):%Y-%m-%d %H:%M:%S}")
    logger.info(f"그룹 수: {len(groups)} / 네이버 API: {'사용' if naver_id else '미사용'}")
    logger.info("=" * 60)

    all_articles: list[dict] = []
    for grp in groups:
        try:
            items = crawl_group(grp, naver_id, naver_secret)
            all_articles.extend(items)
        except Exception as e:
            logger.exception(f"[그룹 실패] {grp.get('group_id')}: {e}")

    all_articles = mark_new_items(all_articles)
    daily_path, master_path = save_articles(all_articles)

    new_count = sum(1 for a in all_articles if a.get("is_new"))
    logger.info(f"저장: {daily_path.name} (신규 {new_count}건 / 전체 {len(all_articles)}건)")
    return all_articles


# ─── 외부 동기화 폴더 복사 ────────────────────────────────────────────────────
def sync_to_external(report_files: list[Path]) -> None:
    cfg = load_config().get("external_sync", {})
    if not cfg.get("enabled"):
        return
    target = cfg.get("target_folder", "").strip()
    if not target:
        return
    target_path = Path(target)
    target_path.mkdir(parents=True, exist_ok=True)
    for f in report_files:
        if f.exists():
            shutil.copy2(f, target_path / f.name)
            logger.info(f"외부 동기화 복사: {f.name} → {target_path}")


# ─── 엔트리 포인트 ────────────────────────────────────────────────────────────
def main():
    p = argparse.ArgumentParser()
    p.add_argument("--keywords-only", action="store_true", help="크롤만 수행, 리포트 생성 X")
    p.add_argument("--report-only", action="store_true", help="크롤 생략, 리포트만 재생성")
    args = p.parse_args()

    if not args.report_only:
        run_crawl()

    if not args.keywords_only:
        # 리포트 생성은 html_reporter 모듈에서 담당 (순환 import 방지를 위해 함수 내 import)
        from html_reporter import generate_report
        out_files = generate_report()
        sync_to_external(out_files)

    logger.info("완료.")


if __name__ == "__main__":
    main()
