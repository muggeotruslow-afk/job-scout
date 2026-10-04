"""Build a source-only release from the reviewed public-file manifest."""
import argparse
import json
from pathlib import Path, PurePosixPath
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = {'SKILL.md', 'README.md', 'LICENSE', 'THIRD_PARTY_NOTICES.md',
            'package.json', 'package-lock.json', 'requirements-intern-scout.txt',
            'scripts/scan_jobs.py', 'scripts/verify_jobs.mjs', 'scripts/onboarding.py'}
PRIVATE = {'local', 'data', 'output', 'node_modules', '.git', '.venv', '__pycache__'}


def public_files(root):
    root = Path(root).resolve()
    names = json.loads((root / 'release-files.json').read_text(encoding='utf-8'))
    if not isinstance(names, list) or not all(isinstance(n, str) for n in names):
        raise ValueError('Release manifest must be a list of relative paths')
    if len(names) != len(set(names)) or not REQUIRED.issubset(names):
        raise ValueError('Release manifest has duplicates or missing required files')
    result = []
    for name in names:
        relative = PurePosixPath(name)
        if relative.is_absolute() or any(p in ('..', '.') for p in relative.parts) or '\\' in name or ':' in name:
            raise ValueError('Invalid release path: ' + name)
        if any(p in PRIVATE or p.startswith('.env') or p.startswith('tmp') for p in relative.parts):
            raise ValueError('Private/temporary file cannot be released: ' + name)
        if relative.parts[0] not in {'scripts', 'references', 'tests', 'examples', 'agents'} and len(relative.parts) > 1:
            raise ValueError('Unapproved release directory: ' + name)
        if relative.name == 'profile.json' or name.endswith(('.mp4', '.pyc', '.docx')):
            raise ValueError('Candidate/media/cache file cannot be released: ' + name)
        file = root / name
        if not file.resolve().is_relative_to(root) or not file.is_file() or file.is_symlink():
            raise ValueError('Missing or unsafe release file: ' + name)
        result.append((name, file))
    return result


def build_release(root, output):
    root = Path(root).resolve()
    files = public_files(root)
    version = json.loads((root / 'package.json').read_text(encoding='utf-8'))['version']
    if not isinstance(version, str) or any(c not in '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ.-' for c in version) or not version:
        raise ValueError('Invalid release version')
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError('Existing release is preserved; choose a new --output path')
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, 'x', compression=ZIP_DEFLATED) as archive:
        for name, file in files:
            archive.write(file, f'job-scout-{version}/{name}')
    with ZipFile(output) as archive:
        if archive.testzip() is not None:
            raise RuntimeError('Release archive integrity check failed')
    return {'archive': str(output), 'version': version, 'public_files': len(files)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    version = json.loads((ROOT / 'package.json').read_text(encoding='utf-8'))['version']
    output = args.output or ROOT / 'local/releases' / f'job-scout-{version}.zip'
    print(json.dumps(build_release(ROOT, output), ensure_ascii=True))


if __name__ == '__main__':
    main()
