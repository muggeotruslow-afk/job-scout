"""Baidu official daily internships, using the public website's search API."""
from datetime import datetime, timezone
import json
import urllib.parse
import urllib.request

API = "https://talent.baidu.com/httservice/getPostListNew"
SEARCH = "https://talent.baidu.com/jobs/list?recruitType=INTERN"


def fetch_baidu(keyword, max_pages, category="all", proxy=None, request_page=None):
    # The live API rejects pageSize=100; its web UI uses 10.
    size = 10
    if proxy == "direct":
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    elif proxy:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({"http": proxy, "https": proxy}))
    else:
        opener = urllib.request.build_opener()

    def search(params):
        request = urllib.request.Request(API, data=urllib.parse.urlencode(params).encode(),
            headers={"Content-Type": "application/x-www-form-urlencoded", "Referer": SEARCH})
        try:
            with opener.open(request, timeout=25) as response:
                return json.load(response)
        except (OSError, ValueError) as error:
            raise RuntimeError(f"Baidu request failed: {error}. Check network/proxy; --http-proxy direct is available.") from error

    request_page = request_page or search
    positions, seen = [], set()
    total = None
    stop = "max_pages"
    pages = 0
    errors = []
    observed = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for page in range(1, max(1, max_pages) + 1):
        try:
            params = {"recruitType": "INTERN", "projectType": "-1", "curPage": page,
                      "pageSize": size, "keyWord": keyword}
            if category == "product":
                params["postType[0]"] = "2"
            response = request_page(params)
            if response.get("status") != "ok":
                raise RuntimeError("Baidu API failed: " + str(response.get("message", "unknown response")))
            data = response.get("data") or {}
            rows = data.get("list")
            if (not isinstance(rows, list) or not isinstance(data.get("total"), (int, str))
                    or str(data.get("pageNum")) != str(page)):
                raise RuntimeError("Baidu API schema/page changed; refusing to claim a complete scan")
            reported = int(data["total"])
            if reported < 0:
                raise RuntimeError("Baidu returned a negative total")
            total = max(total or 0, reported)
            before = len(positions)
            for row in rows:
                if not row.get("postId") or not row.get("name"):
                    raise RuntimeError("Baidu returned a row without postId/name")
                if row.get("projectTypeCode") != "-1" and row.get("projectType") != "日常实习项目":
                    raise RuntimeError("Baidu daily-internship filter no longer matches returned rows")
                if row["postId"] in seen:
                    continue
                seen.add(row["postId"])
                positions.append({"company": "百度", "title": row["name"], "post_id": row["postId"],
                    "source_url": "https://talent.baidu.com/jobs/detail/INTERN/" + urllib.parse.quote(row["postId"], safe=""),
                    "description": row.get("workContent", ""), "requirements": row.get("serviceCondition", ""),
                    "location": row.get("workPlace", ""), "posted_date": row.get("publishDate"),
                    "updated_date": row.get("updateDate"), "recruit_type": row.get("projectType"),
                    "department": row.get("bgShortName", ""), "crawled_at": observed})
            pages = page
            if len(positions) >= total:
                stop = "authoritative_total_reached"
                break
            if not rows:
                stop = "empty_page_before_total"
                break
            if len(positions) == before:
                stop = "repeated_page"
                break
        except (OSError, ValueError, TypeError, AttributeError, RuntimeError) as error:
            if not positions:
                raise RuntimeError(str(error)) from error
            errors.append({'stage': 'fetch', 'page': page, 'reason': str(error)[:500]})
            stop = 'upstream_error'
            break
    return {"ok": not errors, "errors": errors, "source": "baidu_official_api", "total": total or 0,
            "fetched": len(positions), "positions": positions,
            "pagination": {"complete": stop == "authoritative_total_reached", "stop_reason": stop,
                "page_size": size, "max_pages": max_pages, "pages_fetched": pages,
                "authoritative_total": total},
            "scope": {"recruit_type": "daily_internship", "category": category, "keyword": keyword}}
