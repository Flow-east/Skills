"""Fail closed on unsupported text using the SAME Pillow/FreeType font as rendering.
A file-existence check isn't glyph coverage. Compare visible glyph masks to the
font's missing-glyph mask at two sizes. No network, fallback or text rewriting.
This checks missing-glyph/invalid-text failures, NOT ASR correctness or OCR quality.
"""
import hashlib, unicodedata
from pathlib import Path
from PIL import ImageFont


def sha256(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024), b''): h.update(chunk)
    return h.hexdigest()


def fingerprint(font, text):
    mask=font.getmask(text,mode='L')
    return mask.size, bytes(mask)


def configure_weight(font, weight=None):
    if weight is None:return font
    if not isinstance(weight,(int,float)) or isinstance(weight,bool):raise ValueError('Invalid font weight')
    axes=font.get_variation_axes()
    if len(axes)!=1 or axes[0]['name']!=b'Weight' or not axes[0]['minimum']<=weight<=axes[0]['maximum']:
        raise ValueError('Font weight requires a supported single Weight axis')
    font.set_variation_by_axes([weight]);return font


def inspect_font(path, text, index=0, weight=None):
    chars=sorted(set(text)-set('\n\r\t '))
    invalid=[ch for ch in chars if ch=='\ufffd' or unicodedata.category(ch) in ('Cc','Cs')]
    fonts=[configure_weight(ImageFont.truetype(str(path), size, index=index),weight) for size in (48,64)]
    notdef=[{fingerprint(f,'\U0010FFFF'),fingerprint(f,'\uFFFF')} for f in fonts]
    missing=[]
    for ch in chars:
        if ch in invalid: continue
        glyphs=[fingerprint(f,ch) for f in fonts]
        if all(g in nd for g,nd in zip(glyphs,notdef)) or all(not any(g[1]) for g in glyphs):
            missing.append(ch)
    return {'font':str(Path(path).resolve()),'sha256':sha256(path),'face_index':index,
            'weight':weight,'checked_characters':len(chars),'missing':missing,'invalid':invalid,
            'passed':not missing and not invalid}


def display_text(plan):
    texts=[str(plan.get(k,'')) for k in ('title','subtitle','eyebrow')]
    def event(e):
        texts.append(str(e.get('text','')))
        texts.extend(str(r.get('text','')) for r in e.get('runs',[]))
        if e.get('english'): texts.append(str(e['english'].get('text','')))
    for e in plan.get('keyword_stickers',[]): texts.append(str(e.get('text','')))
    for e in plan.get('caption_events',[]): event(e)
    for c in plan['clips']:
        texts.extend(str(w.get('text','')) for w in c.get('words',[]))
        texts.append(str(c.get('caption','')))
        for e in c.get('caption_events',[]): event(e)
        if c.get('card'): texts.extend([str(c['card'].get('label','')),str(c['card'].get('value','')),'0123456789'])
    texts.extend(plan.get('scene_title_lines',[]))
    for group in plan.get('scene_captions',[]):
        for phrase in group.get('phrases',[]):event(phrase)
    for note in plan.get('scene_notes',[]):texts.append(str(note.get('text','')))
    for tag in plan.get('scene_tags',[]):texts.append(str(tag.get('text','')))
    for e in plan.get('scene_translations',[]):texts.append(str(e.get('text','')))
    for e in plan.get('scene_highlights',[]):texts.append(str(e.get('text','')))
    for e in plan.get('scene_callouts',[]):texts.append(str(e.get('text','')))
    for e in plan.get('scene_identity',[]):texts.extend([str(e.get('name','')),str(e.get('detail',''))])
    texts.extend(str(v) for v in plan.get('english_map',{}).values())
    return '\n'.join(texts)


def audit(painter):
    text=display_text(painter.p)
    roles={role:painter.font_path(role) for role in ('title','body','keyword','sticker')}
    if painter.p.get('scene_translations'):roles['translation']=painter.font_path('translation')
    indices={role:painter.font_index(role) for role in roles}
    weights={role:painter.font_weight(role) if hasattr(painter,'font_weight') else None for role in roles}
    unique={(path,indices[role],weights[role]) for role,path in roles.items()}
    reports=[inspect_font(path,text,index,weight) for path,index,weight in sorted(unique,key=str)]
    role_metadata=[]
    metadata_ok=True
    planned=painter.p.get('font_roles',{})
    for role,path in roles.items():
        actual=Path(path).resolve()
        meta=planned.get(role)
        row={'role':role,'actual_path':str(actual),'metadata_present':bool(meta)}
        if meta:
            actual_hash=sha256(actual)
            row.update(metadata_path=meta.get('path'),metadata_index=meta.get('index'),metadata_weight=meta.get('weight'),
                       actual_index=indices[role],actual_weight=weights[role],actual_sha256=actual_hash,metadata_sha256=meta.get('sha256'))
            ok=(Path(meta.get('path','')).resolve()==actual and meta.get('index',0)==indices[role] and
                meta.get('weight')==weights[role] and meta.get('sha256')==actual_hash)
        else:
            ok=True
        row['passed']=ok; metadata_ok=metadata_ok and ok; role_metadata.append(row)
    result={'passed':all(r['passed'] for r in reports) and metadata_ok,'roles':roles,'face_indices':indices,'weights':weights,'fonts':reports,
            'font_role_metadata':role_metadata,'font_roles_consistent':metadata_ok,
            'method':'Pillow/FreeType missing-glyph mask comparison, two sizes; all planned displayed characters',
            'scope':'font coverage, invalid Unicode and portable role metadata; not speech/content/visual-quality approval'}
    if hasattr(painter,'scene_media_assets'):result['scene_media_assets']=painter.scene_media_assets
    return result
