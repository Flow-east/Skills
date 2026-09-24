"""Output-clock raster sticker overlay with asset integrity and safe layout checks."""
import hashlib
import math
from pathlib import Path
from PIL import Image


def _finite(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _intersects(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def load(painter):
    p = painter.p
    items = p.get('illustrations', [])
    if not isinstance(items, list) or len(items) > 8:
        raise ValueError('Illustrations must be a short authored list')
    seen, result = set(), []
    for ev in items:
        if not isinstance(ev, dict) or not isinstance(ev.get('id'), str) or not ev['id'] or ev['id'] in seen:
            raise ValueError('Illustration needs unique id')
        seen.add(ev['id'])
        a, b = ev.get('start'), ev.get('end')
        if not _finite(a) or not _finite(b) or not 0 <= a < b <= p['duration']:
            raise ValueError('Illustration requires output-clock interval')
        if ev.get('time_space') != 'output' or not str(ev.get('reason', '')).strip():
            raise ValueError('Illustration requires semantic reason and output clock')
        x, y, width = ev.get('x'), ev.get('y'), ev.get('width')
        if not all(_finite(q) for q in (x, y, width)) or not 0 <= x < 1 or not 0 <= y < 1 or not 0.04 <= width <= .45:
            raise ValueError('Illustration size/placement outside supported range')
        path = Path(ev.get('path', ''))
        if not path.is_absolute() or not path.is_file():
            raise ValueError('Illustration file must exist at absolute path')
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if ev.get('sha256') != digest:
            raise ValueError('Illustration asset hash mismatch')
        source = ev.get('source')
        if not isinstance(source, dict) or source.get('kind') not in ('generated', 'local'):
            raise ValueError('Illustration needs generated or local provenance')
        if source['kind'] == 'generated' and not all(str(source.get(key, '')).strip() for key in ('skill', 'service', 'grant_id')):
            raise ValueError('Generated illustration needs skill/service/consent provenance')
        with Image.open(path) as raw:
            if raw.mode not in ('RGBA', 'LA', 'P') or 'A' not in raw.convert('RGBA').getbands() or ('transparency' not in raw.info and raw.mode == 'P'):
                raise ValueError('Illustration must have real transparency')
            sprite = raw.convert('RGBA')
        alpha = sprite.getchannel('A')
        low, high = alpha.getextrema()
        if low != 0 or high == 0 or high < 120:
            raise ValueError('Illustration must be visible with transparent background')
        if sprite.width < 16 or sprite.height < 16:
            raise ValueError('Illustration resolution too small')
        sw = round(painter.w*width); sh = round(sw*sprite.height/sprite.width)
        px = round(painter.w*x); py = round(painter.h*y)
        margin = round(8*painter.unit)
        box = (px-margin, py-margin, px+sw+margin, py+sh+margin)
        if box[0] < 0 or box[1] < 0 or box[2] > painter.w or box[3] > painter.h:
            raise ValueError('Illustration exceeds frame safe area')
        for other in result:
            if a < other['end'] and other['start'] < b and _intersects(box, other['box']):
                raise ValueError('Illustrations overlap')
        for region in p.get('protected_regions', []):
            if a < region.get('end', p['duration']) and region.get('start', 0) < b:
                r = region['box']; protected = (r[0]*painter.w, r[1]*painter.h, r[2]*painter.w, r[3]*painter.h)
                if _intersects(box, protected):
                    raise ValueError('Illustration overlaps protected region')
        if painter.variant.get('scene_system'):
            from template_scenes import layout
            for layer in layout(painter):
                if layer['role'] not in ('caption', 'title', 'tag', 'translation', 'subtitle'):
                    continue
                if a < layer['end'] and layer['start'] < b and _intersects(box, layer['box']):
                    raise ValueError('Illustration overlaps text or tag')
        result.append({'id': ev['id'], 'start': a, 'end': b, 'box': box,
                       'position': (px, py), 'image': sprite.resize((sw, sh), Image.Resampling.LANCZOS),
                       'source': source, 'sha256': digest})
    return result


def paint(canvas, items, t):
    if not items:
        return canvas.convert('RGB')
    canvas = canvas.convert('RGBA')
    for ev in items:
        if ev['start'] <= t < ev['end']:
            canvas.alpha_composite(ev['image'], ev['position'])
    return canvas.convert('RGB')


def audit(items):
    return [{'id': item['id'], 'sha256': item['sha256'], 'source': item['source'],
             'start': item['start'], 'end': item['end'], 'box': item['box']} for item in items]
