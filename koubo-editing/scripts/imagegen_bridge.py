#!/usr/bin/env python3
"""Discover available image skills and manage scoped local image-generation consent.

This module never generates images, sends data, installs skills or grants host permissions.
Only record a choice AFTER a human has explicitly made it in this conversation.
"""
import argparse
import hashlib
import json
import os
import re
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

CATEGORIES = frozenset({'prompt', 'transcript', 'video_frame', 'person_reference', 'sensitive'})
DEFAULT_STORE = Path(os.environ.get('XDG_CONFIG_HOME', Path.home()/'.config'))/'koubo-editing'/'imagegen-consent.json'


def video_id(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as source:
        for chunk in iter(lambda: source.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


def discover(roots):
    """Return candidates, not a claim that they are suitable or authorized."""
    rows, seen = [], set()
    for root in roots:
        root = Path(root).expanduser()
        if not root.is_dir():
            continue
        for path in root.rglob('SKILL.md'):
            path = path.resolve()
            if path in seen:
                continue
            seen.add(path)
            text = path.read_text(encoding='utf8')
            front = text.split('---', 2)
            if len(front) < 3 or front[0].strip():
                continue
            fields = dict(re.findall(r'^([\w-]+):\s*(.+)$', front[1], re.M))
            name = fields.get('name', path.parent.name).strip(' "\'')
            desc = fields.get('description', '').strip(' "\'')
            if re.search(r'imagegen|image generation|image generat|生图|生成.{0,6}(?:图片|图像|插图)|raster', name+' '+desc, re.I):
                rows.append({'name': name, 'description': desc, 'skill_file': str(path)})
    return sorted(rows, key=lambda row: row['name'])


def _read(path):
    path = Path(path)
    if not path.exists():
        return {'version': 1, 'grants': []}
    if path.is_symlink():
        raise ValueError('Consent store cannot be a symlink')
    obj = json.loads(path.read_text(encoding='utf8'))
    if obj.get('version') != 1 or not isinstance(obj.get('grants'), list):
        raise ValueError('Unsupported consent store')
    return obj


def _write(path, obj):
    path = Path(path).expanduser()
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.is_symlink():
        raise ValueError('Consent store cannot be a symlink')
    fd, name = tempfile.mkstemp(prefix='.consent-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf8') as output:
            json.dump(obj, output, ensure_ascii=False, indent=2)
            output.write('\n')
        os.chmod(name, 0o600)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def _categories(categories):
    values = set(categories)
    if not values or not values <= CATEGORIES:
        raise ValueError('Unknown or empty data categories')
    return sorted(values)


def grant(store, *, skill, service, categories, scope, video=None,
          max_per_call_minor=0, max_total_minor=0, currency=None):
    if not skill or not service or scope not in ('video', 'permanent'):
        raise ValueError('Named skill/service and video or permanent scope required')
    if scope == 'video' and not re.fullmatch(r'[0-9a-f]{64}', video or ''):
        raise ValueError('Current-video grant needs source video SHA256')
    if scope == 'permanent' and video is not None:
        raise ValueError('Permanent grant cannot contain a video identifier')
    if not all(isinstance(x, int) and not isinstance(x, bool) and x >= 0 for x in (max_per_call_minor, max_total_minor)):
        raise ValueError('Costs must be nonnegative integer minor units')
    if max_total_minor and (not currency or not re.fullmatch(r'[A-Z]{3}', currency)):
        raise ValueError('Paid authorization requires ISO currency')
    if not max_total_minor and currency is not None:
        raise ValueError('Free authorization cannot declare currency')
    if max_per_call_minor > max_total_minor:
        raise ValueError('Per-call budget exceeds total budget')
    obj = _read(store)
    row = {'id': str(uuid.uuid4()), 'scope': scope, 'skill': skill, 'service': service,
           'categories': _categories(categories), 'video': video if scope == 'video' else None,
           'max_per_call_minor': max_per_call_minor, 'max_total_minor': max_total_minor,
           'used_minor': 0, 'currency': currency, 'created_at': datetime.now(timezone.utc).isoformat(), 'revoked': False}
    obj['grants'].append(row)
    _write(store, obj)
    return row


def check(store, *, skill, service, categories, video=None, estimated_minor=None, currency=None):
    if not isinstance(estimated_minor, int) or isinstance(estimated_minor, bool) or estimated_minor < 0:
        raise ValueError('Known nonnegative cost estimate required')
    if estimated_minor and (not currency or not re.fullmatch(r'[A-Z]{3}', currency)):
        raise ValueError('Paid check requires ISO currency')
    wanted = set(_categories(categories))
    for row in reversed(_read(store)['grants']):
        if row['revoked'] or row['skill'] != skill or row['service'] != service:
            continue
        if row['scope'] == 'video' and row['video'] != video:
            continue
        if not wanted <= set(row['categories']) or (estimated_minor and row.get('currency') != currency):
            continue
        if estimated_minor > row['max_per_call_minor'] or row['used_minor'] + estimated_minor > row['max_total_minor']:
            continue
        return row
    return None


def revoke(store, grant_id, *, categories=None):
    obj = _read(store)
    row = next((g for g in obj['grants'] if g['id'] == grant_id), None)
    if row is None:
        raise ValueError('Unknown grant')
    if categories is None:
        row['revoked'] = True
    else:
        subset = set(_categories(categories))
        if not subset <= set(row['categories']):
            raise ValueError('Can only narrow existing scope')
        row['categories'] = sorted(subset)
    _write(store, obj)
    return row


def record_cost(store, grant_id, actual_minor):
    if not isinstance(actual_minor, int) or isinstance(actual_minor, bool) or actual_minor < 0:
        raise ValueError('Actual cost must be known nonnegative minor units')
    obj = _read(store)
    row = next((g for g in obj['grants'] if g['id'] == grant_id), None)
    if row is None:
        raise ValueError('Unknown grant; record the actual charge separately and stop generation')
    # An already-incurred charge must not disappear from the ledger merely because it
    # exceeded the estimate. Record it, revoke the grant and require fresh consent.
    over_limit = (row['revoked'] or actual_minor > row['max_per_call_minor']
                  or row['used_minor'] + actual_minor > row['max_total_minor'])
    row['used_minor'] += actual_minor
    if over_limit:
        row['revoked'] = True
    _write(store, obj)
    if over_limit:
        raise ValueError('Charge outside authorization was recorded; stop further generation')
    return row


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('action', choices=['discover', 'video-id', 'list', 'grant', 'check', 'revoke', 'record-cost'])
    ap.add_argument('--store', type=Path, default=DEFAULT_STORE)
    ap.add_argument('--root', type=Path, action='append')
    ap.add_argument('--file', type=Path)
    ap.add_argument('--skill')
    ap.add_argument('--service')
    ap.add_argument('--categories')
    ap.add_argument('--scope', choices=['video', 'permanent'])
    ap.add_argument('--video')
    ap.add_argument('--id')
    ap.add_argument('--estimated-minor', type=int)
    ap.add_argument('--max-per-call-minor', type=int, default=0)
    ap.add_argument('--max-total-minor', type=int, default=0)
    ap.add_argument('--actual-minor', type=int)
    ap.add_argument('--currency')
    args = ap.parse_args()
    cats = (args.categories or 'prompt').split(',')
    if args.action == 'discover':
        roots = args.root or [Path(os.environ.get('CODEX_HOME', Path.home()/'.codex'))/'skills', Path.cwd()/'.agents/skills', Path.cwd()/'.codex/skills']
        result = discover(roots)
    elif args.action == 'video-id':
        if not args.file: ap.error('video-id requires --file')
        result = video_id(args.file)
    elif args.action == 'list':
        result = _read(args.store)['grants']
    elif args.action == 'grant':
        result = grant(args.store, skill=args.skill, service=args.service, categories=cats,
                       scope=args.scope, video=args.video, max_per_call_minor=args.max_per_call_minor,
                       max_total_minor=args.max_total_minor, currency=args.currency)
    elif args.action == 'check':
        if args.estimated_minor is None: ap.error('check requires --estimated-minor (0 if free)')
        result = check(args.store, skill=args.skill, service=args.service, categories=cats,
                       video=args.video, estimated_minor=args.estimated_minor, currency=args.currency)
    elif args.action == 'revoke':
        if not args.id: ap.error('revoke requires --id')
        result = revoke(args.store, args.id, categories=cats if args.categories is not None else None)
    else:
        if not args.id or args.actual_minor is None: ap.error('record-cost requires --id and --actual-minor')
        result = record_cost(args.store, args.id, args.actual_minor)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
