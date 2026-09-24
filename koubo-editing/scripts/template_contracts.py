"""Versioned whole-template contracts; offline validation, no font fallback."""
import hashlib
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
CAPABILITIES={'phrase_clocks','layered_type','protected_regions','camera_motion','vignette','circle','swipe','staggered_backplate','inset','persistent_notes','paper_strip','scale_entry','bilingual_clocks','mixed_size_type','brush_highlights','cursor_ornament','heart_ornament','ink_write','phrase_takeover'}
KINDS={'pink','gold','grid','white','redyellow','variety','ink','latte','bired','biluxe','biblue','biyellow','luxury','brightyellow','navy','news','crispred','vividblue','shine','green','tech','science','neon','purple','warm','mono','elegantpink','promo','browngold','hotpink','orangeline','colorful','mint','tornred','deepbrown','ginger','blackyellow','verdant','ins','nostalgia','transyellow','tornedge','cleanwhite','waxcute','qqcute','energycartoon','floraltravel','magenta','lightbulb','redfestive','comicred','romance','emojiwhite','contrastpop'}
ROLES=('title','body','keyword','sticker')

def _asset(root,relative):
    if not isinstance(relative,str) or Path(relative).is_absolute():raise ValueError('Contract asset must be relative')
    path=(root/relative).resolve()
    if not path.is_relative_to(root.resolve()):raise ValueError('Contract asset escapes skill root')
    if not path.is_file():raise ValueError(f'Missing contract asset: {relative}')
    return path

def _finite(v): return isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v)

def validate(contract,root=ROOT,verify_assets=False):
    if contract.get('version')!=1:raise ValueError('Unsupported contract version')
    for key in ('target_id','variant_id','display_name','identity_features','typography','layout','annotation','timing','motion','composition','capabilities','render','reference','limitations'):
        if key not in contract:raise ValueError(f'Missing contract field: {key}')
    if not contract['identity_features'] or not all(isinstance(s,str) and s.strip() for s in contract['identity_features']):raise ValueError('Core design features required')
    ids=json.loads((root/'assets/template_targets.json').read_text())['targets']
    target=next((r for r in ids if r['id']==contract['target_id']),None)
    if target is None or target['name']!=contract['reference'].get('name') or target['reference_sha256']!=contract['reference'].get('sha256'):
        raise ValueError('Contract/reference identity mismatch')
    if not isinstance(contract['capabilities'],list) or not set(contract['capabilities'])<=CAPABILITIES:
        raise ValueError('Unimplemented capability dependency')
    for key in ('layout','annotation','timing','motion','composition'):
        if not isinstance(contract[key],dict) or not contract[key]:raise ValueError(f'Empty {key} rules')
    ratios=contract['layout'].get('supported_aspects')
    if not isinstance(ratios,list) or not ratios or any(not isinstance(x,list) or len(x)!=2 or not all(isinstance(a,int) and not isinstance(a,bool) and a>0 for a in x) for x in ratios):
        raise ValueError('Explicit positive aspect pairs required')
    if contract['timing'].get('time_space')!='output':raise ValueError('Contract needs output clock')
    if contract['composition'].get('order')!=['video','canvas','title','captions','tags']:
        raise ValueError('Unsupported layer graph; subject segmentation is not implemented')
    r=contract['render'];sc=r.get('scene_system',{})
    if sc.get('version')!=1 or sc.get('kind') not in KINDS:raise ValueError('Unimplemented renderer kind')
    for key in ('title_size','body_size','keyword_size','tag_size','title_duration'):
        if not _finite(sc.get(key)) or sc[key]<=0:raise ValueError(f'Invalid scene metric: {key}')
    for key in ('title_y','caption_y','tag_y','tag_x'):
        if not _finite(sc.get(key)) or not 0<sc[key]<1:raise ValueError(f'Invalid scene coordinate: {key}')
    if not isinstance(sc.get('allowed_canvas'),list) or not set(sc['allowed_canvas'])<=set(contract['capabilities']) & {'circle','swipe','vignette','inset'}:
        raise ValueError('Canvas capability not declared/implemented')
    if not 1<=contract['layout'].get('max_phrases',0)<=(4 if sc['kind']=='elegantpink' else 3 if sc['kind'] in ('navy','neon','warm') else 2):raise ValueError('Unsupported phrase count')
    manifest=json.loads((root/'assets/fonts/manifest.json').read_text())
    fonts={x['file']:x for x in manifest}
    bilingual=sc['kind'] in ('bired','biluxe','biblue','biyellow','brightyellow','green','purple','elegantpink')
    if bilingual:
        if 'bilingual_clocks' not in contract['capabilities']:raise ValueError('Bilingual capability required')
        for metric in ('translation_size','subtitle_size','display_size'):
            if not _finite(sc.get(metric)) or sc[metric]<=0:raise ValueError('Invalid bilingual metric')
        if contract['timing'].get('translation_clock')!='independent_output':raise ValueError('Independent translation clock required')
    elif 'bilingual_clocks' in contract['capabilities']:raise ValueError('Bilingual capability requires implemented bilingual renderer')
    for role in ROLES + (('translation',) if bilingual else ()):
        spec=contract['typography'].get(role)
        if not isinstance(spec,dict) or not all(k in spec for k in ('file','index','weight')):raise ValueError(f'Missing font role {role}')
        path=_asset(root,spec['file']);m=fonts.get(path.name)
        if not m or not m.get('source') or not m.get('license') or not m.get('sha256'):raise ValueError('Font lacks source/license/hash')
        license_path=_asset(root,'assets/fonts/'+m['license'])
        if not license_path.read_text(encoding='utf8').strip():raise ValueError('Empty font license')
        if not isinstance(spec['index'],int) or isinstance(spec['index'],bool) or spec['index']<0:raise ValueError('Invalid font index')
        if spec['weight'] is not None and (not _finite(spec['weight']) or not 1<=spec['weight']<=1000):raise ValueError('Invalid font weight')
        if verify_assets and hashlib.sha256(path.read_bytes()).hexdigest()!=m['sha256']:raise ValueError('Font digest mismatch')
    return contract


def bind(variant,root=ROOT):
    if not variant.get('contract_file'):return variant
    path=_asset(root,variant['contract_file']);c=validate(json.loads(path.read_text()),root)
    if c['variant_id']!=variant['id']:raise ValueError('Wrong template contract identity')
    # Contract controls the entire rendering recipe; catalogue remains discovery metadata.
    result=dict(variant);result.update({k:v for k,v in c['render'].items() if k not in ('design_status','display_name','verified_from')})
    for role,font in c['typography'].items():
        result[role+'_font']=font['file'];result[role+'_font_index']=font['index'];result[role+'_font_weight']=font['weight']
    result['_contract']=c
    result['contract_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def validate_plan(painter):
    c=painter.variant.get('_contract')
    if not c:return
    if not any(painter.w*b==painter.h*a for a,b in c['layout']['supported_aspects']):raise ValueError('Aspect ratio not verified by this template contract')
    for group in painter.p.get('scene_captions',[]):
        if len(group.get('phrases',[]))>c['layout']['max_phrases']:raise ValueError('Phrase count outside template contract')
    if painter.p.get('scene_tags') and not c['annotation'].get('tags_enabled',True):raise ValueError('This template does not use independent tags')
    track=painter.p.get('camera_motion')
    recipe=c['render'].get('camera_recipe',{})
    if track and recipe and track.get('max_zoom',1.15)>recipe.get('max_zoom',1.15):
        raise ValueError('Camera track exceeds selected template recipe; do not silently override whole-template rules')
    if painter.p.get('template_delivery') not in (None,'preview','accepted'):raise ValueError('Unknown delivery mode')
    if painter.p.get('template_delivery')=='accepted':
        from template_library import read,completed
        if c['target_id'] not in {r['id'] for r in read(ROOT/'assets/template_progress.json')['targets'] if completed(r)}:
            raise ValueError('Template has not passed formal acceptance; explicit preview only')
