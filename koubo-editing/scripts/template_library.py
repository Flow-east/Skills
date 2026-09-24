#!/usr/bin/env python3
"""Portable 54-target identity, fail-closed status accounting and preview directory.
No network, no inferred aesthetic approval, and no automatic runtime registration.
"""
import argparse
import hashlib
import html
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATES = {
    'design': ('pending', 'draft', 'calibrated'),
    'implementation': ('pending', 'in_progress', 'calibration', 'implemented'),
    'technical': ('not_run', 'sample_passed', 'failed', 'passed'),
    'visual': ('pending', 'needs_revision', 'accepted'),
    'release': ('not_installed', 'installed_calibration', 'installed_verified'),
}
# Full acceptance and installed verification are separate from historical samples.
GATES = {'technical': ('passed', 'technical_package'),
         'visual': ('accepted', 'user_acceptance'),
         'release': ('installed_verified', 'installed_render')}


def read(path):
    return json.loads(Path(path).read_text(encoding='utf8'))


def validate(registry, identities=None):
    identities = identities or read(ROOT/'assets/template_targets.json')
    if registry.get('version') != 1 or identities.get('version') != 1:
        raise ValueError('Unsupported library version')
    rows = registry.get('targets', [])
    expected = {r['id']: r for r in identities['targets']}
    if len(expected) != 54 or len(rows) != 54 or len({r.get('id') for r in rows}) != 54:
        raise ValueError('Library needs exactly 54 unique target IDs')
    if set(expected) != {r.get('id') for r in rows}:
        raise ValueError('Missing or unknown reference target')
    variants = []
    for row in rows:
        base = expected[row['id']]
        for key in ('name', 'reference_sha256', 'reference_dimensions'):
            if row.get(key) != base[key]:
                raise ValueError(f'{row["id"]}: reference identity changed: {key}')
        if row.get('batch') not in ('B1','B2','B3','B4','B5','B6'):
            raise ValueError('Unknown rollout batch')
        if not isinstance(row.get('revision'), int) or isinstance(row['revision'], bool) or row['revision'] < 1:
            raise ValueError('Positive revision required')
        for field, allowed in STATES.items():
            if row.get(field) not in allowed:
                raise ValueError(f'Unknown {field} state')
        evidence = row.get('evidence')
        if not isinstance(evidence, dict) or not isinstance(row.get('blockers'), list):
            raise ValueError('Evidence and explicit blocker list required')
        for field, (state, key) in GATES.items():
            if row[field] == state:
                e = evidence.get(key, {})
                if not all(e.get(k) for k in ('path','sha256','reviewer','scope')) or e.get('revision') != row['revision']:
                    raise ValueError(f'{field}: current-revision evidence required')
                if len(e['sha256']) != 64 or any(c not in '0123456789abcdef' for c in e['sha256']):
                    raise ValueError('Invalid evidence digest')
        if row['technical'] == 'passed' and row['implementation'] != 'implemented':
            raise ValueError('Full QA cannot precede implementation')
        if row['visual'] == 'accepted' and (row['technical'] != 'passed' or row['blockers']):
            raise ValueError('Acceptance requires full QA and no unresolved blockers')
        if row['release'] == 'installed_verified' and row['visual'] != 'accepted':
            raise ValueError('Verified release requires explicit visual acceptance')
        if row.get('variant'):
            if not isinstance(row['variant'], str): raise ValueError('Variant must be a string')
            variants.append(row['variant'])
        elif row['implementation'] in ('calibration','implemented'):
            raise ValueError('Implemented target needs a variant')
    if len(variants) != len(set(variants)):
        raise ValueError('One variant cannot count as multiple reference targets')
    return registry


def completed(row):
    return (row['implementation'] == 'implemented' and row['technical'] == 'passed'
            and row['visual'] == 'accepted' and row['release'] == 'installed_verified'
            and not row['blockers'])


def summary(registry):
    validate(registry)
    rows=registry['targets']
    return {'target_count':len(rows),
            'implemented_including_calibrations':sum(r['implementation'] in ('calibration','implemented') for r in rows),
            'full_technical_passed':sum(r['technical']=='passed' for r in rows),
            'visual_accepted':sum(r['visual']=='accepted' for r in rows),
            'installed_calibrations':sum(r['release']=='installed_calibration' for r in rows),
            'completed':sum(completed(r) for r in rows),
            'batches':dict(sorted(Counter(r['batch'] for r in rows).items()))}


def eligible(registry, *, preview=False):
    validate(registry)
    return [r for r in registry['targets'] if completed(r) or
            (preview and r['implementation'] in ('calibration','implemented') and
             r['technical'] in ('sample_passed','passed') and not r['blockers'])]


def set_state(registry, target_id, field, state, evidence=None, evidence_root=None):
    """Pure update; require caller-supplied, existing hashed evidence for gates."""
    if field not in STATES: raise ValueError('Not a status field')
    result=json.loads(json.dumps(registry))
    row=next((r for r in result['targets'] if r['id']==target_id),None)
    if row is None: raise ValueError('Unknown target')
    if field in GATES and state==GATES[field][0]:
        if not evidence or evidence_root is None: raise ValueError('Evidence file and root required')
        path=Path(evidence_root)/evidence['path']
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=evidence.get('sha256'):
            raise ValueError('Evidence is missing or has changed')
        report=read(path)
        if report.get('target_id')!=target_id or report.get('revision')!=row['revision']:
            raise ValueError('Evidence report target/revision mismatch')
        if report.get('passed') is not True: raise ValueError('Evidence must record passing checks')
        if field=='visual' and (report.get('decision')!='accepted' or not report.get('user_quote')):
            raise ValueError('Explicit user acceptance required, not silence or a machine score')
        row['evidence'][GATES[field][1]]=evidence
    row[field]=state
    # A rejected/regressed revision cannot remain a completed installed release.
    if field=='technical' and state!='passed' and row['visual']=='accepted': row['visual']='needs_revision'
    if row['visual']!='accepted' and row['release']=='installed_verified': row['release']='installed_calibration'
    return validate(result)


def render_gallery(registry, output, media=None):
    """Local, escaped HTML. Media supplied explicitly, never reference-as-delivery."""
    stats=summary(registry);media=media or {};cards=[]
    esc=html.escape
    for r in registry['targets']:
        m=media.get(r['id'],{}); links=[]
        for key,label in [('reference','开拍参考（非本技能成片）'),('preview','本技能校准预览')]:
            if key not in m: continue
            file=Path(m[key]).resolve()
            if file.is_file():
                links.append(f'<details><summary>{label}</summary><video controls preload="none" src="{esc(file.as_uri(),quote=True)}"></video></details>')
        status='已完成' if completed(r) else '校准版·待验收' if r['implementation'] in ('calibration','implemented') else '待实现'
        cards.append(f'<article data-search="{esc(r["name"]+" "+r["batch"]+" "+status,quote=True)}"><h2>{esc(r["name"])}</h2><p>{r["id"]} · {r["batch"]} · {status}</p><p>技术：{esc(r["technical"])} / 视觉：{esc(r["visual"])}</p><p>{esc("；".join(r["blockers"]))}</p>{"".join(links)}</article>')
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text('''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>54套模板实施目录</title>
<style>body{margin:0;background:#10151c;color:#eaf0f7;font:16px system-ui}header{padding:32px;position:sticky;top:0;background:#10151cf5;z-index:1}h1{margin:0 0 12px}input{padding:12px;width:min(80vw,600px);font:inherit}main{padding:0 32px 32px;display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:16px}article{padding:20px;background:#1c2633;border-radius:14px}h2{font-size:20px}p{line-height:1.6;color:#b4c4d6}video{width:100%;max-height:480px}summary{cursor:pointer;padding:10px 0}article[hidden]{display:none}</style>
<header><h1>54套独立模板 · 实施目录</h1>'''+f'<p>目标54套｜已有实现（含校准）{stats["implemented_including_calibrations"]}｜正式完成{stats["completed"]}。参考、实现、验收分别统计。</p>'+'''<input id="search" aria-label="筛选模板" placeholder="搜索名称、批次或状态"></header><main>'''+''.join(cards)+'''</main><script>document.querySelector('#search').addEventListener('input',e=>{for(const c of document.querySelectorAll('article'))c.hidden=!c.dataset.search.includes(e.target.value.trim())});</script></html>''',encoding='utf8')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('action', choices=['validate','summary','eligible','gallery'])
    ap.add_argument('--registry',type=Path,default=ROOT/'assets/template_progress.json')
    ap.add_argument('--preview',action='store_true')
    ap.add_argument('--out',type=Path)
    ap.add_argument('--media',type=Path)
    args=ap.parse_args();reg=read(args.registry);validate(reg)
    if args.action=='gallery':
        if not args.out: ap.error('gallery requires --out')
        render_gallery(reg,args.out,read(args.media) if args.media else None)
    else: print(json.dumps(eligible(reg,preview=args.preview) if args.action=='eligible' else summary(reg),ensure_ascii=False,indent=2))

if __name__=='__main__':main()
