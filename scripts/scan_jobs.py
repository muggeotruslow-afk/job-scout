#!/usr/bin/env python3
"""Fetch complete official-ATS results and enrich them for job-scout.

The public intern-scout CLI currently forces ``max_pages=1``.  This wrapper
re-enters itself with intern-scout's own Python environment and calls the
adapter directly, so page-size limits do not silently truncate a scan.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from difflib import SequenceMatcher
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Iterable
import importlib.util


SKILL_DIR = Path(__file__).resolve().parents[1]
BUILTIN_HTTP = {'baidu', 'tencent', 'netease', 'xiaohongshu', 'kuaishou', 'jd', 'pdd','huawei'}
BUILTIN_BROWSER = {'alibaba', 'bytedance','xiaomi'}

def company_slug(value):
    name=value.strip().casefold()
    registry=json.loads((SKILL_DIR/'references/company-registry.json').read_text(encoding='utf-8'))
    return next((slug for slug, aliases in registry.items() if name in [slug.casefold(), *(a.casefold() for a in aliases)]), name)

def load_helper(name):
    spec=importlib.util.spec_from_file_location(name,SKILL_DIR/'scripts'/f'{name}.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--company", required=True)
    parser.add_argument("--keyword", default="")
    parser.add_argument("--page-size", type=int, default=100)
    parser.add_argument("--max-pages", type=int, default=50)
    parser.add_argument("--baidu-category", choices=("all", "product"), default="all",
                        help="Baidu daily internships: all categories or product only.")
    parser.add_argument("--http-proxy", default=os.environ.get("JOB_SCOUT_HTTP_PROXY") or None,
                        help="Official HTTP API proxy URL, or direct; otherwise use system proxy settings.")
    parser.add_argument("--browser-proxy", default=os.environ.get("JOB_SCOUT_BROWSER_PROXY") or None,
                        help="Browser proxy URL, or direct; otherwise use system proxy settings.")
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Output cap after a complete scan; 0 keeps every result.",
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--career-ops-root", type=Path,
        default=os.environ.get("CAREER_OPS_ROOT") or None,
        help="Career Ops directory; defaults to CAREER_OPS_ROOT when set.",
    )
    parser.add_argument("--history", type=Path, action="append", default=[])
    parser.add_argument('--use-career-ops-history',action='store_true',help='Explicitly read configured Career Ops data/applications.md; browser configuration alone does not load history.')
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--verify-limit", type=int, default=30)
    parser.add_argument("--_direct", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    for field in ('page_size', 'max_pages', 'verify_limit'):
        if getattr(args, field) < 1:
            parser.error('--' + field.replace('_', '-') + ' must be positive')
    if args.limit < 0:
        parser.error('--limit must be zero (all results) or positive')
    args.company = company_slug(args.company)
    if args.career_ops_root is not None:
        args.career_ops_root = args.career_ops_root.expanduser().resolve()
        if not args.career_ops_root.is_dir():
            parser.error("Career Ops directory does not exist: " + str(args.career_ops_root))
    if args.verify:
        if args.career_ops_root is not None:
            for name in ("package.json", "liveness-browser.mjs"):
                if not (args.career_ops_root / name).is_file():
                    parser.error("Career Ops directory is missing " + name)
    return args


def intern_scout_python() -> Path | None:
    candidates: list[Path] = []
    appdata = os.environ.get("APPDATA")
    if appdata:
        candidates.append(Path(appdata) / "uv/tools/intern-scout/Scripts/python.exe")
    candidates.extend(
        [
            Path.home() / ".local/share/uv/tools/intern-scout/bin/python",
            Path.home() / ".local/share/uv/tools/intern-scout/Scripts/python.exe",
        ]
    )
    return next((path for path in candidates if path.exists()), None)


def reexec_with_tool_python() -> int | None:
    """Run inside intern-scout's venv when the package is not importable here."""
    try:
        import intern_scout  # noqa: F401
        return None
    except ImportError:
        tool_python = intern_scout_python()
        if not tool_python:
            raise SystemExit("Cannot find intern-scout's Python environment")
        command = [str(tool_python), str(Path(__file__).resolve()), *sys.argv[1:], "--_direct"]
        return subprocess.run(command, check=False).returncode


def normalize_url(company: str, url: str) -> str:
    config = portal_config(company)
    for replacement in config.get("url_replacements", []):
        url = url.replace(replacement["from"], replacement["to"])
    return url


def portal_config(company: str) -> dict:
    config_path = SKILL_DIR / "references" / "portal-adapters.json"
    if not config_path.exists():
        return {}
    configs = json.loads(config_path.read_text(encoding="utf-8"))
    return configs.get(company.lower(), {})


def normalized_text(value: object) -> str:
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", str(value or "").lower())


def stable_key(item: dict) -> str:
    post_id = normalized_text(item.get("post_id"))
    if post_id:
        return f"id:{post_id}"
    url = str(item.get("source_url") or "").split("?", 1)[0].rstrip("/").lower()
    if url:
        return f"url:{url}"
    return f"title:{normalized_text(item.get('company'))}:{normalized_text(item.get('title'))}"


def is_authoritative_total(reported_total: int, row_count: int, page_size: int) -> bool:
    """Reject adapters that merely echo the current page length as total."""
    return reported_total > row_count or reported_total > page_size


def campaign_classification(item: dict) -> dict:
    title = str(item.get("title") or "")
    campaign_text = " ".join(
        str(item.get(field) or "")
        for field in ("title", "recruit_type", "department")
    )

    rules = [
        ("sales_service", "销售/门店/顾问", ("销售实习", "销售顾问", "门店实习", "产品顾问", "交付顾问")),
        ("conversion", "转正/留用实习", ("转正", "留用", "储备", "人才计划")),
        ("autumn", "秋招", ("秋招", "秋季校园招聘")),
        ("summer", "暑期实习", ("暑期", "暑假实习", "summer intern")),
        (
            "campus",
            "校招/校园项目",
            ("校招", "校园招聘", "应届", "毕业生", "管培生", "提前批", "超星计划", "精英计划"),
        ),
        ("daily", "日常实习", ("日常实习", "普通实习", "长期实习", "滚动实习")),
    ]
    lowered = campaign_text.lower()
    for code, label, markers in rules:
        marker = next((m for m in markers if m.lower() in lowered), None)
        if marker:
            return {"code": code, "label": label, "confidence": "high", "reason": f"命中“{marker}”"}

    full_text = " ".join(str(item.get(field) or "") for field in ("title", "recruit_type", "description", "requirements"))
    if "实习" in full_text or "intern" in full_text.lower():
        return {
            "code": "daily",
            "label": "日常实习（待官网确认批次）",
            "confidence": "medium",
            "reason": "岗位含实习且未发现校招、暑期、秋招或留用标记",
        }
    return {
        "code": "other",
        "label": "其他招聘",
        "confidence": "medium",
        "reason": f"“{title}”未发现明确实习或招聘批次标记",
    }


def markdown_rows(path: Path) -> Iterable[dict]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    header: list[str] | None = None
    rows: list[dict] = []
    for line in lines:
        if not line.strip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if not header:
            header = cells
            continue
        if all(re.fullmatch(r":?-{2,}:?", cell) for cell in cells):
            continue
        if len(cells) == len(header):
            rows.append(dict(zip(header, cells)))
    return rows


def load_history(paths: list[Path]) -> list[dict]:
    entries: list[dict] = []
    for path in paths:
        for row in markdown_rows(path):
            lowered = {str(key).lower(): value for key, value in row.items()}
            company = lowered.get("company") or lowered.get("公司") or ""
            role = lowered.get("role") or lowered.get("岗位") or ""
            status = lowered.get("status") or lowered.get("状态") or ""
            if company or role:
                entries.append(
                    {
                        "company": company,
                        "role": role,
                        "status": status,
                        "date": lowered.get("date") or lowered.get("日期") or "",
                        "source_file": str(path),
                    }
                )
    return entries


def history_match(item: dict, entries: list[dict]) -> dict | None:
    company = normalized_text(item.get("company"))
    title = normalized_text(item.get("title"))
    best: tuple[float, dict] | None = None
    for entry in entries:
        old_company = normalized_text(entry.get("company"))
        old_title = normalized_text(entry.get("role"))
        if company and old_company and company not in old_company and old_company not in company:
            continue
        ratio = SequenceMatcher(None, title, old_title).ratio()
        containment = min(len(title), len(old_title)) >= 6 and (title in old_title or old_title in title)
        score = 1.0 if containment else ratio
        if score >= 0.86 and (best is None or score > best[0]):
            best = (score, entry)
    if not best:
        return None
    entry = best[1]
    return {**entry, "similarity": round(best[0], 3)}


def recommendation_state(match: dict | None) -> str:
    if not match:
        return "new"
    status = normalized_text(match.get("status"))
    if any(word in status for word in ("reject", "拒绝", "未通过", "失败")):
        return "previously_rejected"
    if any(word in status for word in ("applied", "投递", "面试", "offer", "入职")):
        return "already_in_pipeline"
    if any(word in status for word in ("ignored", "无回复", "不理", "放弃")):
        return "previously_contacted_or_skipped"
    return "known_history"


def ranking_key(item: dict) -> tuple[int, int, str]:
    state_order = {"new": 0, "known_history": 1, "already_in_pipeline": 2,
                   "previously_contacted_or_skipped": 3, "previously_rejected": 4}
    campaign_order = {"daily": 0, "other": 1, "conversion": 2, "summer": 3,
                      "autumn": 4, "campus": 5, "sales_service": 6}
    return (
        state_order.get(str(item.get("recommendation_state")), 9),
        campaign_order.get(str((item.get("campaign") or {}).get("code")), 9),
        normalized_text(item.get("title")),
    )


def fetch_complete(company: str, keyword: str, page_size: int, max_pages: int,
                   *, baidu_category="all", http_proxy=None, browser_proxy=None, career_ops_root=None) -> dict:
    if company == "baidu":
        spec = importlib.util.spec_from_file_location("baidu_adapter", SKILL_DIR / "scripts/baidu_adapter.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.fetch_baidu(keyword, max_pages, baidu_category, http_proxy)
    if company in BUILTIN_HTTP:
        return load_helper('official_adapters').fetch_official(company,keyword,max_pages,http_proxy)
    if company in BUILTIN_BROWSER:
        output=Path.cwd()/f'.job-scout-fetch-{os.getpid()}-{time_token()}.json'
        command=['node',str(SKILL_DIR/'scripts/browser_adapters.mjs'),'--company',company,'--keyword',keyword,
                 '--max-pages',str(max_pages),'--page-size',str(page_size),'--output',str(output)]
        if career_ops_root:command.extend(['--career-ops-root',str(career_ops_root)])
        if browser_proxy:command.extend(['--browser-proxy',browser_proxy])
        try:
            completed=subprocess.run(command,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=max(90,max_pages*45))
            if output.exists():return json.loads(output.read_text(encoding='utf-8'))
            raise RuntimeError('Browser adapter did not return a result: '+completed.stderr[-400:])
        finally:output.unlink(missing_ok=True)
    from intern_scout.crawler import ADAPTERS

    factory = ADAPTERS.get(company)
    if not factory:
        raise SystemExit(f"Unsupported company: {company}. Supported: {', '.join(ADAPTERS)}")
    adapter = factory()
    # Beisen returns both a numeric JobAdId and a portal UUID Id. The
    # current portal detail route expects the UUID, unlike the listing API.
    if adapter.__class__.__name__=='BeisenAdapter':
        original_parse=adapter._parse_row
        def parse_portal_row(row):
            parsed=original_parse(row)
            if str(parsed.posted_date).startswith('0001-'):parsed.posted_date=''
            if row.get('Id'):
                parsed.source_url=parsed.source_url.replace('jobAdId='+str(row.get('JobAdId') or ''),'jobAdId='+str(row['Id']))
            return parsed
        adapter._parse_row=parse_portal_row
    if company=='minimax':
        original_parse=adapter._parse_row
        def parse_minimax_row(row):
            parsed=original_parse(row);parsed.source_url=parsed.source_url.replace('/saas-career/position/','/379481/position/');return parsed
        adapter._parse_row=parse_minimax_row
    if company=='oppo':
        original_parse=adapter._parse_row
        def parse_oppo_row(row):
            parsed=original_parse(row)
            parsed.source_url=parsed.source_url.replace('/campus/post?','/campus/post/'+parsed.post_id+'?')
            return parsed
        adapter._parse_row=parse_oppo_row
    if http_proxy and hasattr(adapter,'_session'):
        adapter._session.trust_env=False
        if http_proxy!='direct':adapter._session.proxies={'http':http_proxy,'https':http_proxy}
    size = max(1, min(100, page_size))
    if adapter.__class__.__name__=='BeisenAdapter':size=min(size,50)
    bucket: list[dict] = []
    seen: set[str] = set()
    authoritative_total: int | None = None
    stop_reason = "max_pages"
    last_source = company

    errors=[]
    for page in range(1, max(1, max_pages) + 1):
        result = adapter.search(keyword=keyword, page=page, page_size=size)
        if not result.ok:
            errors.append({'stage':'fetch','page':page,'reason':result.message})
            stop_reason='upstream_error';break
        last_source = result.source
        rows = [position.to_dict() for position in result.positions]

        # Some adapters (notably JD) incorrectly report the current page length
        # as `total`. Only trust a total that is larger than one full page.
        reported_total = int(result.total or 0)
        if is_authoritative_total(reported_total, len(rows), size):
            authoritative_total = max(authoritative_total or 0, reported_total)

        new_rows = 0
        for row in rows:
            key = stable_key(row)
            if key in seen:
                continue
            seen.add(key)
            bucket.append(row)
            new_rows += 1

        if not rows:
            stop_reason = 'empty_page_before_total' if authoritative_total is not None and len(bucket)<authoritative_total else "empty_page"
            break
        if len(rows) < size:
            stop_reason = 'short_page_before_total' if authoritative_total is not None and len(bucket)<authoritative_total else "short_page"
            break
        if authoritative_total is not None and len(bucket) >= authoritative_total:
            stop_reason = "authoritative_total_reached"
            break
        if new_rows == 0:
            stop_reason = "repeated_page"
            break

    complete = stop_reason not in ("max_pages", "repeated_page", "upstream_error",'empty_page_before_total','short_page_before_total')
    total = authoritative_total if authoritative_total is not None else len(bucket)
    return {
        "ok": not errors,
        'errors':errors,
        "source": last_source,
        "total": total,
        "fetched": len(bucket),
        "positions": bucket,
        "pagination": {
            "complete": complete,
            "stop_reason": stop_reason,
            "page_size": size,
            "max_pages": max_pages,
            "authoritative_total": authoritative_total,
        },
    }


def run_verifier(payload_path: Path, output_path: Path, root: Path, limit: int, browser_proxy=None) -> None:
    verifier = SKILL_DIR / "scripts" / "verify_jobs.mjs"
    command = [
        "node",
        str(verifier),
        "--input",
        str(payload_path),
        "--output",
        str(output_path),
        "--limit",
        str(max(1, limit)),
    ]
    if root:command.extend(['--career-ops-root',str(root)])
    if browser_proxy:
        command.extend(["--browser-proxy", browser_proxy])
    completed = subprocess.run(command, text=True, encoding="utf-8", errors="replace", check=False)
    if completed.returncode != 0:
        raise SystemExit(f"Browser verification failed with exit code {completed.returncode}")


def main() -> int:
    args = parse_args()
    if not args._direct and args.company not in BUILTIN_HTTP | BUILTIN_BROWSER:
        status = reexec_with_tool_python()
        if status is not None:
            return status

    try:
        raw = fetch_complete(args.company, args.keyword, args.page_size, args.max_pages,
                             baidu_category=args.baidu_category, http_proxy=args.http_proxy,
                             browser_proxy=args.browser_proxy,career_ops_root=args.career_ops_root)
    except (RuntimeError, OSError, ValueError, subprocess.TimeoutExpired, SystemExit) as error:
        raw={'ok':False,'source':args.company,'total':None,'fetched':0,'positions':[],
             'pagination':{'complete':False,'stop_reason':'upstream_error'},
             'errors':[{'stage':'fetch','reason':str(error)[:600]}]}
    company_portal = portal_config(args.company)
    history_paths = list(args.history)
    if args.career_ops_root is not None and args.use_career_ops_history:
        default_history = args.career_ops_root / "data" / "applications.md"
        if default_history.exists() and default_history not in history_paths:
            history_paths.append(default_history)
    history = load_history(history_paths)

    positions: list[dict] = []
    seen: set[str] = set()
    duplicate_count = 0
    for position in raw.get("positions", []):
        item = dict(position)
        raw_url = str(item.get("source_url") or "")
        item["source_url_raw"] = raw_url
        item["source_url"] = normalize_url(args.company, raw_url)
        item["official_search_url"] = item.get('official_search_url') or company_portal.get("fallback_search_url") or ""
        key = stable_key(item)
        if key in seen:
            duplicate_count += 1
            continue
        seen.add(key)
        item["campaign"] = campaign_classification(item)
        match = history_match(item, history)
        item["history_match"] = match
        item["recommendation_state"] = recommendation_state(match)
        item["source_active_signal"] = {
            "active": True,
            "method": "current_official_ats_query",
            "observed_at": item.get("crawled_at"),
        }
        item["liveness_status"] = "unverified"
        positions.append(item)

    positions.sort(key=ranking_key)

    total = int(raw['total']) if raw.get('total') is not None else None
    fetched = int(raw.get("fetched", len(positions)))
    pagination = raw.get("pagination") or {}
    complete = bool(pagination.get("complete", total is not None and fetched >= total))
    incomplete_jds=sum(not p.get('description') or not p.get('requirements') for p in positions)
    truncated_by_max_pages = pagination.get("stop_reason") == "max_pages"
    counts: dict[str, int] = {}
    for item in positions:
        code = item["campaign"]["code"]
        counts[code] = counts.get(code, 0) + 1
    unique_count = len(positions)
    if args.limit > 0:
        positions = positions[: args.limit]

    normalized = {
        'ok':raw.get('ok',True),
        'status':'failed' if not raw.get('ok',True) and not positions else 'partial' if not complete or incomplete_jds else 'empty_query' if not positions else 'complete',
        'empty_result_note':'No rows returned for this query; this does not prove the company has no openings.' if not positions else None,
        'errors':raw.get('errors',[]),
        'incomplete_jds':incomplete_jds,
        "company": args.company,
        "keyword": args.keyword,
        "source": raw.get("source"),
        "crawled_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "total_reported": total,
        "fetched_reported": fetched,
        "complete": complete,
        "truncated_by_max_pages": truncated_by_max_pages,
        "pagination": pagination,
        "scope": raw.get("scope"),
        'source_fetched':raw.get('source_fetched',fetched),
        "output_limited": args.limit > 0 and fetched > args.limit,
        "unique_positions": unique_count,
        "returned_positions": len(positions),
        "duplicates_removed": duplicate_count,
        "campaign_counts": counts,
        "history_sources": [str(path) for path in history_paths],
        "history_entries_loaded": len(history),
        "positions": positions,
    }

    rendered = json.dumps(normalized, ensure_ascii=False, indent=2)
    output_path = args.output
    if args.verify and positions:
        verify_dir = (output_path.parent if output_path else Path.cwd()).resolve()
        verify_dir.mkdir(parents=True, exist_ok=True)
        token = f"{os.getpid()}-{int(datetime.now().timestamp())}"
        input_path = verify_dir / f".job-scout-verify-{token}-input.json"
        verified_path = verify_dir / f".job-scout-verify-{token}-output.json"
        try:
            input_path.write_text(rendered, encoding="utf-8")
            try:
                run_verifier(input_path, verified_path, args.career_ops_root, args.verify_limit, args.browser_proxy)
                verified = json.loads(verified_path.read_text(encoding="utf-8"))
                if not isinstance(verified, dict) or not isinstance(verified.get('positions'), list):
                    raise ValueError('Verifier returned an invalid result schema')
                rendered = json.dumps(verified, ensure_ascii=False, indent=2)
            except (SystemExit,OSError,ValueError) as error:
                normalized['ok']=False;normalized['status']='partial'
                normalized['errors'].append({'stage':'verification','reason':str(error)[:600]})
                rendered=json.dumps(normalized,ensure_ascii=False,indent=2)
        finally:
            input_path.unlink(missing_ok=True)
            verified_path.unlink(missing_ok=True)

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.reconfigure(encoding="utf-8")
        print(rendered)
    return 0 if normalized['ok'] else 2

def time_token():
    return int(datetime.now().timestamp()*1000)


if __name__ == "__main__":
    raise SystemExit(main())
