<p align="center"><img src="assets/job-scout-icon.png" alt="Job Scout" width="160"></p>

<h1 align="center">Job Scout</h1>

<p align="center"><strong>Describe your goal → Discover official jobs → Match evidence → Verify links</strong></p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-orange" alt="MIT license"></a>
  <img src="https://img.shields.io/badge/platform-Windows-blue" alt="Windows tested">
  <a href="https://github.com/muggeotruslow-afk/job-scout/releases/tag/v0.1.0"><img src="https://img.shields.io/badge/release-v0.1.0-blue" alt="v0.1.0"></a>
  <img src="https://img.shields.io/badge/type-AI%20Skill-teal" alt="AI Skill">
</p>

<p align="center"><a href="README.md">简体中文</a> · <strong>English</strong></p>

---

Find internships with a natural-language request. Job Scout reads complete official job descriptions, checks eligibility, ranks fit against your candidate evidence, and verifies official links. It searches responsibilities and capabilities as well as job titles, helping discover relevant roles with unexpected names.

This is an **AI Skill plus collection and verification scripts**. The AI understands candidate evidence and explains scores; scripts collect structured jobs and inspect pages. Scores measure evidence coverage, not hiring probability. No applications are submitted automatically.

## Demo

### Search and ranking (45 seconds)

https://github.com/user-attachments/assets/19e9ab97-dff8-4127-ad09-2e77daa500b1

### Open official job links (15 seconds)

https://github.com/user-attachments/assets/9e721f27-a07c-4068-85d4-3b7c0f197d82


The demos use a previously confirmed fictional candidate. The search recording is accelerated; the actual run took approximately five minutes. Downloads contain no confirmed candidate profile.

## Capabilities and coverage

- 11 built-in official entries: Baidu, Tencent, Alibaba, NetEase, ByteDance, Kuaishou, Xiaohongshu, JD, PDD, Huawei, Xiaomi.
- 16 additional current entries use optional intern-scout adapters. The [dated coverage report](references/company-coverage.md) covers 31 companies, including four that were only checked at portal level. An entry does not guarantee complete or permanent coverage.
- Pagination, deduplication, complete descriptions, internship campaigns and optional application-history matching.
- Browser verification: `active`, `uncertain`, `expired`, `unverified`. Active means a matching title and a visible enabled application control, not guaranteed availability or successful submission.
- Local onboarding: import a resume, fill only missing conditions, confirm the summary, save locally, and continue the original request.

## Installation

Download the [v0.1.0 source archive](https://github.com/muggeotruslow-afk/job-scout/releases/tag/v0.1.0) and extract it into a directory. Explicitly ask your AI client to use that directory's `SKILL.md`. If an older global skill has the same name, specify this directory to avoid selecting the old copy.

Python 3.10+ is required. Browser collection and verification need Node.js 20+ and Playwright. Windows has been tested; macOS/Linux have not completed end-to-end acceptance.

Run from the project directory:

```powershell
npm ci
npx playwright install chromium
```

Baidu, Tencent, NetEase, Xiaohongshu, Kuaishou, JD, PDD and Huawei collection use Python's standard library. Alibaba, ByteDance and Xiaomi collection require the browser dependencies above.

For optional intern-scout adapters, install Git and then:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-intern-scout.txt
.venv\Scripts\intern-scout --list
```

Career Ops is optional. Standalone operation uses this project's browser and liveness modules. See the [Chinese README](README.md) for the pinned optional Career Ops setup and proxy troubleshooting.

## First use

Ask your AI client:

> Use the Job Scout skill in this project directory. Find Baidu AI product daily internships suitable for me, rank them by fit, and explain the scores with official links.

With no saved profile, the skill asks for your resume and missing eligibility conditions, such as acceptable cities, weekly attendance, earliest start, duration, education and graduation date. It shows a summary before saving and then continues the search. Later sessions reuse the confirmed candidate. Portfolio links and application history are optional; unknown conditions remain unknown.

Candidate profiles default to `local/user/profile.json`, excluded from Git. Use `JOB_SCOUT_DATA_DIR` or `onboarding.py --data-dir <path>` for another private directory. The built-in importer handles Markdown, UTF-8 text and DOCX. PDFs/images require your AI client's extraction or OCR.

```powershell
python scripts/onboarding.py status
python scripts/onboarding.py doctor
python scripts/onboarding.py import-resume --resume <resume.docx>
```

Doctor checks installation, not network access or browser launch. Do not upload private profiles, resumes or application histories to the repository.

## Script examples

```powershell
python scripts/scan_jobs.py --company baidu --baidu-category product --output output/baidu.json
python scripts/scan_jobs.py --company baidu --baidu-category product --verify --verify-limit 10 --output output/baidu-verified.json
python scripts/scan_jobs.py --company bytedance --page-size 50 --max-pages 100 --output output/bytedance.json
```

For semantic discovery, collect a sufficiently broad official scope first, then have the AI read descriptions and requirements. A narrow keyword or category may omit related roles. Scripts do not independently calculate fit scores.

`--max-pages` defaults to 50. Baidu uses fixed pages of 10; other effective sizes appear in `pagination.page_size`. `--limit` caps output after collection and does not replace pagination. Use positive `--verify-limit` values. Extra history files require explicit `--history <path>`; a Career Ops dependency directory alone does not authorize history loading.

## Result boundaries

- `complete`: scoped pagination collected and JD fields present; `partial`: cap, repeated pages, missing JD fields or interruption; `failed`: unsuccessful collection with no jobs; `empty_query`: this query returned no jobs, not proof a company has no openings.
- `completion_basis=raw_rows` uses official raw row totals. Report duplicate and unique-job counts separately.
- Preserve publication, update and scan times separately. Old dates alone do not prove expiration.
- Only selected jobs are browser-verified; others remain unverified. Xiaomi is a campus-internship source. Some Kuaishou controls require users to handle platform terms themselves.
- No fixed BOSS adapter. User-provided JD evidence can be assessed without inventing recruiter activity.
- No automatic login, terms acceptance, resume upload, recruiter contact or application submission.

## Verification and release packaging

```powershell
python -m unittest discover -s tests -v
npm test
python scripts/build_release.py
```

The latest code acceptance passed 44 Python and 9 Node tests. Baidu's dated full scan returned 197 jobs in 20 pages; these numbers are not guarantees for future runs. Company-specific limits are recorded in the coverage report.

`release-files.json` is the public source manifest. The packaging script includes only listed files and excludes private profiles, recordings, dependencies and local results. Do not zip the entire development directory. Report issues through [GitHub Issues](https://github.com/muggeotruslow-afk/job-scout/issues) with sanitized commands, environment and errors.

MIT license. Dependency attribution and licenses: [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
