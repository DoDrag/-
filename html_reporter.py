# -*- coding: utf-8 -*-
"""
GLP-1 Trend / html_reporter.py
data/articles_master.json + research_keywords.json 으로 HTML 리포트 생성.
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import html
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
REPORTS_DIR = BASE_DIR / "reports"
KW_PATH = BASE_DIR / "research_keywords.json"
CFG_PATH = BASE_DIR / "config.json"

KST = timezone(timedelta(hours=9))
logger = logging.getLogger("html_reporter")


def _esc(s: str) -> str:
    return html.escape(s or "", quote=True)


def _load(path: Path, default):
    if not path.exists():
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def generate_report() -> list[Path]:
    cfg = _load(CFG_PATH, {})
    kw_data = _load(KW_PATH, {"groups": []})
    master = _load(DATA_DIR / "articles_master.json", {"articles": []})
    articles = master.get("articles", [])

    title = cfg.get("report", {}).get("title", "이슈 리서치 리포트")
    days_window = cfg.get("report", {}).get("default_days_window", 7)

    # 그룹별로 분류 + 최근 N일 필터링
    cutoff = datetime.now(KST) - timedelta(days=days_window)
    by_group: dict[str, list[dict]] = {}
    for a in articles:
        gid = a.get("group_id", "_unknown")
        # 발행일 필터
        pub_iso = a.get("pub_iso", "")
        if pub_iso:
            try:
                dt = datetime.fromisoformat(pub_iso)
                if dt < cutoff:
                    continue
            except Exception:
                pass
        by_group.setdefault(gid, []).append(a)

    # 각 그룹 내 최신순 정렬
    for lst in by_group.values():
        lst.sort(key=lambda x: x.get("pub_iso", ""), reverse=True)

    now_kst = datetime.now(KST)

    # ─── HTML 생성 ─────────────────────────────────────────────────────────
    html_parts = []
    html_parts.append(f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>{_esc(title)} — {now_kst:%Y-%m-%d %H:%M}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;600;700&display=swap" rel="stylesheet">
  <style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: 'Noto Sans KR', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  background: #f0f2f5; color: #222; font-size: 14px; line-height: 1.6; }}
.top-bar {{ background: linear-gradient(135deg, #1a237e, #283593); color: #fff;
  padding: 24px 32px; display: flex; align-items: center; gap: 14px; flex-wrap: wrap; }}
.top-bar h1 {{ font-size: 22px; font-weight: 700; }}
.top-bar .meta {{ font-size: 12px; opacity: .85; margin-left: auto; }}
.container {{ max-width: 1280px; margin: 0 auto; padding: 24px; }}

/* TOC */
.toc {{ background: #fff; border-radius: 10px; padding: 18px 24px; margin-bottom: 18px;
  box-shadow: 0 2px 6px rgba(0,0,0,.07); }}
.toc h3 {{ font-size: 14px; margin-bottom: 10px; color: #444; }}
.toc ul {{ list-style: none; display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 6px; }}
.toc li a {{ display: block; padding: 8px 12px; background: #f5f5f5; border-radius: 6px;
  text-decoration: none; color: #333; font-size: 13px; font-weight: 600; transition: .15s; }}
.toc li a:hover {{ background: #1a237e; color: #fff; }}
.toc li a .cnt {{ float: right; background: #1a237e; color: #fff; font-size: 11px;
  padding: 1px 7px; border-radius: 8px; }}
.toc li a:hover .cnt {{ background: #fff; color: #1a237e; }}

/* KPI */
.summary-row {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px; margin-bottom: 18px; }}
.kpi-card {{ background: #fff; border-radius: 10px; padding: 16px;
  box-shadow: 0 2px 6px rgba(0,0,0,.07); border-left: 4px solid #1a237e; }}
.kpi-card.red {{ border-left-color: #e53935; }}
.kpi-card.green {{ border-left-color: #43a047; }}
.kpi-card.amber {{ border-left-color: #fb8c00; }}
.kpi-num {{ font-size: 22px; font-weight: 700; color: #1a237e; }}
.kpi-card.red .kpi-num {{ color: #e53935; }}
.kpi-card.green .kpi-num {{ color: #43a047; }}
.kpi-card.amber .kpi-num {{ color: #fb8c00; }}
.kpi-label {{ font-size: 12px; color: #666; margin-top: 4px; }}

/* Section */
.section {{ background: #fff; border-radius: 10px; margin-bottom: 16px;
  box-shadow: 0 2px 6px rgba(0,0,0,.06); overflow: hidden; }}
.section-header {{ padding: 14px 22px; font-size: 16px; font-weight: 700;
  background: linear-gradient(90deg, #f5f7ff, #fff); border-bottom: 1px solid #e8eaed;
  display: flex; align-items: center; gap: 8px; }}
.section-header .badge {{ background: #1a237e; color: #fff; font-size: 11px;
  padding: 3px 9px; border-radius: 10px; font-weight: 600; }}
.badge.intl {{ background: #1565c0; }}
.badge.dom {{ background: #e53935; }}
.badge.policy {{ background: #fb8c00; }}
.section-header .meta {{ font-size: 11px; color: #666; margin-left: auto; font-weight: 400; }}
.section-body {{ padding: 18px 22px; }}

/* Article cards */
.articles {{ display: grid; grid-template-columns: 1fr; gap: 10px; }}
.article-card {{ border: 1px solid #e8eaed; border-radius: 8px; padding: 12px 16px;
  background: #fafbfc; transition: .15s; position: relative; }}
.article-card:hover {{ background: #f5f7ff; border-color: #c5cae9; }}
.article-card.new {{ border-left: 3px solid #e53935; background: #fff8f8; }}
.article-card.new::before {{ content: 'NEW'; position: absolute; top: 8px; right: 12px;
  background: #e53935; color: #fff; font-size: 10px; padding: 2px 8px; border-radius: 4px;
  font-weight: 700; }}
.article-title {{ font-size: 14px; font-weight: 700; margin-bottom: 5px; line-height: 1.4;
  padding-right: 50px; }}
.article-title a {{ color: #1a237e; text-decoration: none; }}
.article-title a:hover {{ text-decoration: underline; }}
.article-meta {{ font-size: 11px; color: #777; margin-bottom: 6px;
  display: flex; gap: 10px; flex-wrap: wrap; }}
.article-meta .src {{ font-weight: 600; color: #1565c0; }}
.article-meta .kw {{ background: #e8eaf6; color: #1a237e; padding: 1px 7px;
  border-radius: 4px; font-weight: 600; font-size: 10px; }}
.article-summary {{ font-size: 13px; color: #444; }}

.empty {{ padding: 20px; text-align: center; color: #888; font-size: 13px; }}

.footer {{ text-align: center; color: #888; font-size: 11px; padding: 24px; margin-top: 20px; }}

/* ─── Keyword Editor ─── */
.edit-fab {{ position: fixed; bottom: 24px; right: 24px; z-index: 100;
  background: #1a237e; color: #fff; border: none; border-radius: 50px;
  padding: 14px 22px; font-size: 14px; font-weight: 700; cursor: pointer;
  box-shadow: 0 4px 12px rgba(26,35,126,.4); transition: .2s;
  font-family: 'Noto Sans KR', sans-serif; }}
.edit-fab:hover {{ background: #283593; transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(26,35,126,.5); }}

.modal-backdrop {{ display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,.5); z-index: 200; align-items: center; justify-content: center;
  padding: 20px; }}
.modal-backdrop.show {{ display: flex; }}
.modal {{ background: #fff; border-radius: 12px; max-width: 900px; width: 100%;
  max-height: 90vh; display: flex; flex-direction: column; overflow: hidden;
  box-shadow: 0 10px 40px rgba(0,0,0,.3); }}
.modal-header {{ padding: 18px 24px; background: linear-gradient(135deg, #1a237e, #283593);
  color: #fff; display: flex; align-items: center; gap: 12px; }}
.modal-header h2 {{ font-size: 18px; font-weight: 700; flex: 1; }}
.modal-close {{ background: rgba(255,255,255,.2); color: #fff; border: none;
  width: 32px; height: 32px; border-radius: 50%; cursor: pointer; font-size: 16px; }}
.modal-close:hover {{ background: rgba(255,255,255,.35); }}
.modal-body {{ padding: 20px 24px; overflow-y: auto; flex: 1; background: #f8f9fa; }}
.modal-footer {{ padding: 16px 24px; background: #fff; border-top: 1px solid #e8eaed;
  display: flex; gap: 10px; justify-content: flex-end; align-items: center; flex-wrap: wrap; }}

.notice {{ background: #fff8e1; border-left: 4px solid #fbc02d; padding: 12px 16px;
  border-radius: 6px; font-size: 12px; color: #6d4c1c; margin-bottom: 14px; line-height: 1.6; }}
.notice strong {{ color: #f57f17; }}
.notice code {{ background: #fff; padding: 1px 5px; border-radius: 3px; font-family: monospace; }}

.group-card {{ background: #fff; border: 1px solid #e8eaed; border-radius: 8px;
  margin-bottom: 12px; overflow: hidden; }}
.group-head {{ padding: 12px 16px; background: linear-gradient(90deg, #f5f7ff, #fff);
  display: flex; align-items: center; gap: 8px; cursor: pointer;
  border-bottom: 1px solid #e8eaed; }}
.group-head .toggle {{ font-size: 12px; transition: .2s; }}
.group-head.open .toggle {{ transform: rotate(90deg); }}
.group-head .gname {{ flex: 1; font-weight: 700; font-size: 14px; color: #1a237e; }}
.group-head .gmeta {{ font-size: 11px; color: #666; }}
.group-body {{ padding: 14px 16px; display: none; }}
.group-card.open .group-body {{ display: block; }}

.field-row {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 10px; margin-bottom: 12px; }}
.field {{ display: flex; flex-direction: column; gap: 4px; }}
.field label {{ font-size: 11px; font-weight: 600; color: #666; }}
.field input, .field select {{ padding: 6px 10px; border: 1px solid #ccc; border-radius: 5px;
  font-size: 13px; font-family: inherit; }}
.field input:focus, .field select:focus {{ outline: none; border-color: #1a237e; }}

.kw-list {{ display: flex; flex-direction: column; gap: 5px; margin-bottom: 8px; }}
.kw-item {{ display: flex; gap: 6px; align-items: center; }}
.kw-item input {{ flex: 1; padding: 5px 9px; border: 1px solid #ddd; border-radius: 5px;
  font-size: 12px; font-family: inherit; }}
.kw-item button {{ background: #ffebee; color: #c62828; border: none; border-radius: 4px;
  padding: 5px 9px; cursor: pointer; font-size: 11px; font-weight: 700; }}
.kw-item button:hover {{ background: #ffcdd2; }}

.btn {{ padding: 8px 14px; border: 1px solid #ddd; border-radius: 6px; background: #fff;
  cursor: pointer; font-size: 12px; font-weight: 600; font-family: inherit; transition: .15s; }}
.btn:hover {{ background: #f5f5f5; }}
.btn.primary {{ background: #1a237e; color: #fff; border-color: #1a237e; }}
.btn.primary:hover {{ background: #283593; }}
.btn.danger {{ background: #fff; color: #c62828; border-color: #ef9a9a; }}
.btn.danger:hover {{ background: #ffebee; }}
.btn.small {{ padding: 4px 10px; font-size: 11px; }}

@media (max-width: 600px) {{
  .modal {{ max-height: 95vh; }}
  .modal-header h2 {{ font-size: 15px; }}
}}
  </style>
</head>
<body>
<div class="top-bar">
  <h1>📊 {_esc(title)}</h1>
  <span class="meta">최근 {days_window}일 · 갱신 {now_kst:%Y-%m-%d %H:%M} KST</span>
</div>
<div class="container">
""")

    # ─── KPI ───
    total = sum(len(by_group.get(g["group_id"], [])) for g in kw_data.get("groups", []))
    new_total = sum(
        sum(1 for a in by_group.get(g["group_id"], []) if a.get("is_new"))
        for g in kw_data.get("groups", [])
    )
    group_count = len(kw_data.get("groups", []))

    html_parts.append('<div class="summary-row">')
    html_parts.append(f'<div class="kpi-card"><div class="kpi-num">{total}</div><div class="kpi-label">최근 {days_window}일 수집 기사</div></div>')
    html_parts.append(f'<div class="kpi-card red"><div class="kpi-num">{new_total}</div><div class="kpi-label">신규 (직전 실행 대비)</div></div>')
    html_parts.append(f'<div class="kpi-card amber"><div class="kpi-num">{group_count}</div><div class="kpi-label">키워드 그룹</div></div>')
    html_parts.append(f'<div class="kpi-card green"><div class="kpi-num">{now_kst:%H:%M}</div><div class="kpi-label">갱신 시각 (KST)</div></div>')
    html_parts.append('</div>')

    # ─── TOC ───
    html_parts.append('<div class="toc"><h3>📑 그룹 목차</h3><ul>')
    for grp in kw_data.get("groups", []):
        gid = grp["group_id"]
        cnt = len(by_group.get(gid, []))
        html_parts.append(
            f'<li><a href="#sec-{_esc(gid)}">{_esc(grp["label"])}<span class="cnt">{cnt}</span></a></li>'
        )
    html_parts.append('</ul></div>')

    # ─── 그룹별 섹션 ───
    for grp in kw_data.get("groups", []):
        gid = grp["group_id"]
        label = grp["label"]
        badge = grp.get("badge", "dom")
        items = by_group.get(gid, [])
        new_in_group = sum(1 for a in items if a.get("is_new"))

        html_parts.append(f'<div class="section" id="sec-{_esc(gid)}">')
        html_parts.append(
            f'<div class="section-header">'
            f'<span class="badge {_esc(badge)}">{_esc(badge.upper())}</span>'
            f'{_esc(label)}'
            f'<span class="meta">{len(items)}건 · 신규 {new_in_group}건</span>'
            f'</div>'
        )
        html_parts.append('<div class="section-body">')

        if not items:
            html_parts.append('<div class="empty">최근 기간 내 수집된 기사가 없습니다.</div>')
        else:
            html_parts.append('<div class="articles">')
            for a in items:
                cls = "article-card" + (" new" if a.get("is_new") else "")
                html_parts.append(f'<div class="{cls}">')
                html_parts.append(
                    f'<div class="article-title"><a href="{_esc(a.get("link",""))}" target="_blank" rel="noopener">'
                    f'{_esc(a.get("title",""))}</a></div>'
                )
                meta_bits = []
                if a.get("source"):
                    meta_bits.append(f'<span class="src">{_esc(a["source"])}</span>')
                if a.get("pub_display"):
                    meta_bits.append(f'<span>{_esc(a["pub_display"])}</span>')
                if a.get("keyword"):
                    meta_bits.append(f'<span class="kw">{_esc(a["keyword"])}</span>')
                html_parts.append(f'<div class="article-meta">{" ".join(meta_bits)}</div>')
                if a.get("summary"):
                    html_parts.append(f'<div class="article-summary">{_esc(a["summary"])}</div>')
                html_parts.append('</div>')
            html_parts.append('</div>')

        html_parts.append('</div></div>')

    # ─── 푸터 ───
    html_parts.append(f"""
<div class="footer">
  GLP-1 Trend · 자동 생성 {now_kst:%Y-%m-%d %H:%M:%S KST}<br>
  키워드 편집: 우측 하단 ⚙️ 버튼 클릭 · 설정: <code>config.json</code>
</div>
</div>

<!-- 키워드 편집 FAB -->
<button class="edit-fab" id="editFab">⚙️ 키워드 편집</button>

<!-- 키워드 편집 모달 -->
<div class="modal-backdrop" id="editModal">
  <div class="modal">
    <div class="modal-header">
      <h2>⚙️ 키워드 편집</h2>
      <button class="modal-close" id="modalClose">×</button>
    </div>
    <div class="modal-body">
      <div class="notice">
        <strong>적용 방법:</strong> 편집 후 <strong>"💾 JSON 다운로드"</strong> 클릭 →
        브라우저가 <code>research_keywords.json</code>을 받음 →
        그 파일을 <code>GLP-1 Trend</code> 폴더에 덮어쓰기 →
        다음 크롤(또는 <code>run_once.bat</code> 재실행)부터 새 키워드로 수집됩니다.<br>
        <small style="opacity:.8;">※ HTML만으로는 PC 파일을 직접 수정할 수 없어 이 방식을 씁니다.</small>
      </div>
      <div id="groupsContainer"></div>
      <button class="btn primary" id="addGroupBtn" style="margin-top:8px;">+ 새 그룹 추가</button>
    </div>
    <div class="modal-footer">
      <span id="changeStatus" style="font-size:11px; color:#888; margin-right:auto;"></span>
      <button class="btn" id="resetBtn">처음 상태로</button>
      <button class="btn primary" id="downloadBtn">💾 JSON 다운로드</button>
    </div>
  </div>
</div>

<!-- 임베디드 키워드 데이터 -->
<script type="application/json" id="kwData">{json.dumps(kw_data, ensure_ascii=False)}</script>

<script>
// ─── TOC 스무스 스크롤 ───
document.querySelectorAll('.toc a[href^="#"]').forEach(a => {{
  a.addEventListener('click', function(e) {{
    e.preventDefault();
    const t = document.querySelector(this.getAttribute('href'));
    if (t) t.scrollIntoView({{behavior:'smooth', block:'start'}});
  }});
}});

// ─── 키워드 편집기 ───
const KW_INITIAL = JSON.parse(document.getElementById('kwData').textContent);
let kwState = JSON.parse(JSON.stringify(KW_INITIAL));  // deep clone

const fab = document.getElementById('editFab');
const modal = document.getElementById('editModal');
const closeBtn = document.getElementById('modalClose');
const container = document.getElementById('groupsContainer');
const addGroupBtn = document.getElementById('addGroupBtn');
const downloadBtn = document.getElementById('downloadBtn');
const resetBtn = document.getElementById('resetBtn');
const statusEl = document.getElementById('changeStatus');

const BADGES = [
  {{value:'dom', label:'국내(빨강)'}},
  {{value:'intl', label:'해외(파랑)'}},
  {{value:'policy', label:'정책(주황)'}}
];
const LANGS = [{{value:'ko', label:'한국어'}}, {{value:'en', label:'영어'}}];

function escapeHtml(s) {{
  return String(s||'').replace(/[&<>"']/g, c => (
    {{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]
  ));
}}

function render() {{
  container.innerHTML = '';
  (kwState.groups || []).forEach((g, gi) => {{
    const card = document.createElement('div');
    card.className = 'group-card open';
    const totalKw = (g.keywords || []).length;
    card.innerHTML = `
      <div class="group-head open" data-toggle="${{gi}}">
        <span class="toggle">▶</span>
        <span class="gname">${{escapeHtml(g.label || g.group_id || '(이름 없음)')}}</span>
        <span class="gmeta">${{escapeHtml(g.badge||'dom')}} · ${{escapeHtml(g.lang||'ko')}} · ${{totalKw}}개 키워드</span>
        <button class="btn small danger" data-del-group="${{gi}}">🗑 삭제</button>
      </div>
      <div class="group-body">
        <div class="field-row">
          <div class="field">
            <label>그룹 ID (영문/숫자/_)</label>
            <input type="text" data-gi="${{gi}}" data-field="group_id" value="${{escapeHtml(g.group_id||'')}}">
          </div>
          <div class="field">
            <label>표시 라벨</label>
            <input type="text" data-gi="${{gi}}" data-field="label" value="${{escapeHtml(g.label||'')}}">
          </div>
          <div class="field">
            <label>뱃지 색상</label>
            <select data-gi="${{gi}}" data-field="badge">
              ${{BADGES.map(b=>`<option value="${{b.value}}" ${{g.badge===b.value?'selected':''}}>${{b.label}}</option>`).join('')}}
            </select>
          </div>
          <div class="field">
            <label>언어</label>
            <select data-gi="${{gi}}" data-field="lang">
              ${{LANGS.map(l=>`<option value="${{l.value}}" ${{g.lang===l.value?'selected':''}}>${{l.label}}</option>`).join('')}}
            </select>
          </div>
          <div class="field">
            <label>키워드당 최대 수집</label>
            <input type="number" min="1" max="50" data-gi="${{gi}}" data-field="max_per_keyword" value="${{g.max_per_keyword||10}}">
          </div>
        </div>
        <div class="field">
          <label>키워드 목록</label>
          <div class="kw-list">
            ${{(g.keywords||[]).map((k,ki)=>`
              <div class="kw-item">
                <input type="text" data-gi="${{gi}}" data-ki="${{ki}}" data-field="keyword" value="${{escapeHtml(k)}}">
                <button data-del-kw="${{gi}}_${{ki}}">×</button>
              </div>
            `).join('')}}
          </div>
          <button class="btn small" data-add-kw="${{gi}}">+ 키워드 추가</button>
        </div>
      </div>
    `;
    container.appendChild(card);
  }});
  bindEvents();
  updateStatus();
}}

function bindEvents() {{
  // 그룹 헤더 토글
  container.querySelectorAll('[data-toggle]').forEach(el => {{
    el.addEventListener('click', e => {{
      if (e.target.tagName === 'BUTTON') return;
      el.parentElement.classList.toggle('open');
      el.classList.toggle('open');
    }});
  }});
  // 필드 변경
  container.querySelectorAll('input[data-field], select[data-field]').forEach(el => {{
    el.addEventListener('input', e => {{
      const gi = parseInt(el.dataset.gi);
      const field = el.dataset.field;
      if (field === 'keyword') {{
        const ki = parseInt(el.dataset.ki);
        kwState.groups[gi].keywords[ki] = el.value;
      }} else if (field === 'max_per_keyword') {{
        kwState.groups[gi][field] = parseInt(el.value) || 10;
      }} else {{
        kwState.groups[gi][field] = el.value;
      }}
      updateStatus();
    }});
  }});
  // 키워드 추가
  container.querySelectorAll('[data-add-kw]').forEach(btn => {{
    btn.addEventListener('click', () => {{
      const gi = parseInt(btn.dataset.addKw);
      kwState.groups[gi].keywords.push('');
      render();
    }});
  }});
  // 키워드 삭제
  container.querySelectorAll('[data-del-kw]').forEach(btn => {{
    btn.addEventListener('click', () => {{
      const [gi, ki] = btn.dataset.delKw.split('_').map(Number);
      kwState.groups[gi].keywords.splice(ki, 1);
      render();
    }});
  }});
  // 그룹 삭제
  container.querySelectorAll('[data-del-group]').forEach(btn => {{
    btn.addEventListener('click', e => {{
      e.stopPropagation();
      const gi = parseInt(btn.dataset.delGroup);
      const name = kwState.groups[gi].label || kwState.groups[gi].group_id;
      if (confirm(`그룹 "${{name}}" 을 삭제하시겠습니까?`)) {{
        kwState.groups.splice(gi, 1);
        render();
      }}
    }});
  }});
}}

function updateStatus() {{
  const changed = JSON.stringify(kwState) !== JSON.stringify(KW_INITIAL);
  statusEl.textContent = changed ? '● 변경사항 있음 — 다운로드 필요' : '저장된 상태와 동일';
  statusEl.style.color = changed ? '#e53935' : '#888';
}}

addGroupBtn.addEventListener('click', () => {{
  const id = prompt('새 그룹 ID (영문/숫자/_만):', 'new_group');
  if (!id || !/^[a-zA-Z0-9_]+$/.test(id)) {{
    if (id !== null) alert('영문/숫자/_ 만 사용 가능합니다.');
    return;
  }}
  if (kwState.groups.some(g => g.group_id === id)) {{
    alert('이미 존재하는 ID 입니다.');
    return;
  }}
  kwState.groups.push({{
    group_id: id,
    label: id,
    badge: 'dom',
    lang: 'ko',
    max_per_keyword: 10,
    keywords: ['']
  }});
  render();
}});

resetBtn.addEventListener('click', () => {{
  if (confirm('모든 변경사항을 버리고 처음 상태로 되돌릴까요?')) {{
    kwState = JSON.parse(JSON.stringify(KW_INITIAL));
    render();
  }}
}});

downloadBtn.addEventListener('click', () => {{
  // 빈 키워드 자동 정리
  kwState.groups.forEach(g => {{
    g.keywords = (g.keywords||[]).map(k => k.trim()).filter(k => k.length > 0);
  }});
  // 검증
  const ids = kwState.groups.map(g => g.group_id);
  const dupId = ids.find((id, i) => ids.indexOf(id) !== i);
  if (dupId) {{
    alert('중복된 그룹 ID: ' + dupId);
    return;
  }}
  for (const g of kwState.groups) {{
    if (!/^[a-zA-Z0-9_]+$/.test(g.group_id)) {{
      alert('그룹 ID는 영문/숫자/_만 가능: ' + g.group_id);
      return;
    }}
    if (g.keywords.length === 0) {{
      if (!confirm(`그룹 "${{g.label}}"에 키워드가 없습니다. 그래도 다운로드할까요?`)) return;
    }}
  }}
  // 메타 보존
  const out = Object.assign({{}}, KW_INITIAL, {{groups: kwState.groups}});
  const json = JSON.stringify(out, null, 2);
  const blob = new Blob([json], {{type: 'application/json;charset=utf-8'}});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'research_keywords.json';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  alert('다운로드 완료!\\n\\nGLP-1 Trend 폴더의 research_keywords.json 을 방금 받은 파일로 교체하세요.\\n그 다음 run_once.bat 을 실행하면 새 키워드로 수집됩니다.');
}});

fab.addEventListener('click', () => {{
  modal.classList.add('show');
  if (container.children.length === 0) render();
}});
closeBtn.addEventListener('click', () => modal.classList.remove('show'));
modal.addEventListener('click', e => {{
  if (e.target === modal) modal.classList.remove('show');
}});
document.addEventListener('keydown', e => {{
  if (e.key === 'Escape') modal.classList.remove('show');
}});
</script>
</body>
</html>
""")

    output = "\n".join(html_parts)

    # 두 곳에 저장: research_daily.html (고정) + 날짜 스냅샷
    daily_path = REPORTS_DIR / "research_daily.html"
    snapshot_path = REPORTS_DIR / f"research_{now_kst:%Y%m%d}.html"
    daily_path.write_text(output, encoding="utf-8")
    snapshot_path.write_text(output, encoding="utf-8")
    logger.info(f"리포트 생성: {daily_path.name} + {snapshot_path.name}")

    return [daily_path, snapshot_path]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    generate_report()
