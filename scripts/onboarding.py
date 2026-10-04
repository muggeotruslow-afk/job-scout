"""Local first-use state and checks. Does not search jobs or call a model."""
import argparse
from datetime import datetime, timezone
import importlib.util
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
from zipfile import ZipFile, BadZipFile
from xml.etree import ElementTree

ROOT=Path(__file__).resolve().parents[1]
CONDITIONS=('target_roles','recruitment_type','locations','weekly_days','earliest_start','duration_months','education','graduation')

def data_dir(value=None):
    return Path(value or os.environ.get('JOB_SCOUT_DATA_DIR') or ROOT/'local/user').expanduser().resolve()

def read_profile(directory):
    file=directory/'profile.json'
    if not file.exists():return None
    value=json.loads(file.read_text(encoding='utf-8'))
    if not isinstance(value,dict):raise ValueError('Profile must be a JSON object; preserve the file and import again.')
    if value.get('schema_version')!=1:raise ValueError('Unsupported profile schema; preserve the file and migrate explicitly.')
    if not str(value.get('evidence_text') or '').strip():raise ValueError('Saved profile has no candidate evidence; import a resume before scoring.')
    return value

def profile_status(directory):
    profile=read_profile(directory)
    if profile is None:return {'state':'first_use','profile_path':str(directory/'profile.json'),'missing':list(CONDITIONS)}
    missing=[key for key in CONDITIONS if profile.get(key) in (None,'',[])]
    state='needs_confirmation' if not profile.get('confirmed_at') else 'ready_with_unknowns' if missing else 'ready'
    return {'state':state,'profile_path':str(directory/'profile.json'),'missing':missing,'profile':profile}

def extract_resume(path):
    if path.suffix.lower() in ('.md','.txt'):
        return path.read_text(encoding='utf-8-sig')
    if path.suffix.lower()=='.docx':
        ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        with ZipFile(path) as archive:
            info=archive.getinfo('word/document.xml')
            if info.file_size>20_000_000:raise ValueError('Resume XML is too large to import')
            root=ElementTree.fromstring(archive.read(info))
        lines=[]
        for paragraph in root.findall('.//w:p',ns):
            if paragraph.find('.//w:p',ns) is not None:continue
            text=''.join(t.text or '' for t in paragraph.findall('.//w:t',ns)).strip()
            if text and (not lines or lines[-1]!=text):lines.append(text)
        return '\n'.join(lines)
    raise ValueError('Use Markdown, UTF-8 text or DOCX; PDFs/images need the AI client to read/OCR them first. Do not guess unreadable content.')

def save_profile(directory,value,confirmed=False):
    if not isinstance(value,dict):raise ValueError('Draft must be a JSON object')
    if not str(value.get('evidence_text') or '').strip():raise ValueError('Candidate evidence_text is required')
    for key in ('target_roles','locations'):
        if value.get(key) is not None and not isinstance(value[key],list):raise ValueError(key+' must be a list or null')
    days=value.get('weekly_days')
    if days is not None and (isinstance(days,bool) or not isinstance(days,(int,float)) or not 1<=days<=7):raise ValueError('weekly_days must be 1..7 or null')
    months=value.get('duration_months')
    if months is not None and (isinstance(months,bool) or not isinstance(months,(int,float)) or months<=0):raise ValueError('duration_months must be positive or null')
    # Unknown conditions remain null; confirmation means the displayed summary
    # was accepted, not that every condition is known or every claim verified.
    fields=('evidence_text','resume_source',*CONDITIONS,'portfolio_links','history_paths','pending_request')
    profile={key:value.get(key) for key in fields}
    profile['evidence_text']=re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b','[邮箱省略]',str(profile['evidence_text']))
    profile['evidence_text']=re.sub(r'(?<!\d)(?:\+?86[- ]?)?1[3-9]\d{9}(?!\d)','[手机号省略]',profile['evidence_text'])
    profile.update(schema_version=1,confirmed_at=datetime.now(timezone.utc).isoformat() if confirmed else None)
    directory.mkdir(parents=True,exist_ok=True)
    temporary=directory/'profile.json.tmp'
    temporary.write_text(json.dumps(profile,ensure_ascii=False,indent=2),encoding='utf-8')
    temporary.replace(directory/'profile.json')
    return profile_status(directory)

def doctor(browser_root=None):
    node=shutil.which('node');npm=shutil.which('npm.cmd') or shutil.which('npm')
    playwright=False;browser=False;issue=None;node_version=None;node_supported=False
    if node:
        script="const{createRequire}=require('node:module');const fs=require('node:fs');const r=createRequire(require('node:path').resolve(process.argv[1],'package.json'));try{const{chromium}=r('playwright');console.log(JSON.stringify({playwright:true,downloadedBrowser:fs.existsSync(chromium.executablePath())}));}catch{console.log(JSON.stringify({playwright:false,downloadedBrowser:false}));}"
        try:
            node_version=subprocess.run([node,'--version'],capture_output=True,text=True,timeout=10).stdout.strip()
            node_supported=int(node_version.lstrip('v').split('.')[0])>=20
            result=subprocess.run([node,'-e',script,str(browser_root or ROOT)],capture_output=True,text=True,timeout=15)
            check=json.loads(result.stdout);playwright=check['playwright'];browser=check['downloadedBrowser']
        except (OSError,ValueError,subprocess.TimeoutExpired) as error:issue=str(error)[:200]
    installed=[]
    for key,tail in [('LOCALAPPDATA','Google/Chrome/Application/chrome.exe'),('PROGRAMFILES','Google/Chrome/Application/chrome.exe'),('PROGRAMFILES(X86)','Microsoft/Edge/Application/msedge.exe'),('PROGRAMFILES','Microsoft/Edge/Application/msedge.exe')]:
        if os.environ.get(key) and (Path(os.environ[key])/tail).is_file():installed.append(str(Path(os.environ[key])/tail))
    return {'python':{'available':True,'version':__import__('sys').version.split()[0]},
      'node':node,'node_version':node_version,'node_supported':node_supported,'npm':npm,'playwright':playwright,'browser_available':browser or bool(installed),
      'installed_browsers':installed,'intern_scout':importlib.util.find_spec('intern_scout') is not None,
      'checks_network':False,'checks_browser_launch':False,'issue':issue,
      'actions':([] if __import__('sys').version_info>=(3,10) else ['Install Python 3.10+'])+([] if node_supported and npm else ['Install Node.js 20+ with npm for browser features'])+([] if playwright or not node_supported or not npm else ['Run npm ci in the Job Scout directory'])+([] if browser or installed else ['Run npx playwright install chromium after npm ci']),
      'note':'HTTP-only company scans can proceed without Node. Doctor checks installation; the first real verification tests launch and network.'}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir')
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('status')
    check=sub.add_parser('doctor');check.add_argument('--browser-root',type=Path)
    read=sub.add_parser('import-resume');read.add_argument('--resume',type=Path,required=True)
    save=sub.add_parser('save-profile');save.add_argument('--input',type=Path,required=True);save.add_argument('--confirmed',action='store_true')
    args=parser.parse_args();directory=data_dir(args.data_dir)
    try:
        if args.command=='status':result=profile_status(directory)
        elif args.command=='doctor':result=doctor(args.browser_root)
        elif args.command=='import-resume':result={'resume_source':str(args.resume.resolve()),'evidence_text':extract_resume(args.resume)}
        else:result=save_profile(directory,json.loads(args.input.read_text(encoding='utf-8-sig')),args.confirmed)
    except (OSError,ValueError,KeyError,ElementTree.ParseError,BadZipFile) as error:
        print(json.dumps({'state':'error','reason':str(error)},ensure_ascii=False));return 2
    print(json.dumps(result,ensure_ascii=False,indent=2));return 0

if __name__=='__main__':raise SystemExit(main())
