"""Independent authored translation clock. Never translates or changes Chinese ASR."""
from pathlib import Path

KINDS = {'bired', 'biluxe', 'biblue', 'biyellow', 'brightyellow', 'green', 'purple', 'elegantpink'}


def validate(p):
    from template_scenes import interval, texts
    events = p.p.get('scene_translations', [])
    kind = p.variant.get('scene_system', {}).get('kind')
    if kind not in KINDS:
        if events or p.p.get('scene_highlights'):
            raise ValueError('Bilingual/highlight layers need a declared bilingual template')
        return
    green_compact=kind=='green'
    purple=kind in ('purple','elegantpink')
    default_mode='bilingual' if kind=='elegantpink' else 'normal'
    needs_events=not green_compact or any(e.get('mode','compact')=='compact' for g in p.p['scene_captions'] for e in g['phrases'])
    if purple:needs_events=any(e.get('mode',default_mode)=='bilingual' for g in p.p['scene_captions'] for e in g['phrases'])
    if not isinstance(events, list) or needs_events and not events:
        raise ValueError('Bilingual template needs separately authored scene_translations')
    phrases = {}
    for group in p.p['scene_captions']:
        for e in group['phrases']:
            if purple and e.get('mode',default_mode)!='bilingual':continue
            if green_compact and e.get('mode','compact')!='compact':continue
            ident = e.get('id')
            if not isinstance(ident, str) or not ident or ident in phrases:
                raise ValueError('Bilingual phrases need unique nonempty ids')
            phrases[ident] = e
    seen = set()
    for e in events:
        a, b = interval(e, p.p['duration'])
        ident = e.get('phrase_id')
        if not isinstance(ident, str) or ident not in phrases or ident in seen:
            raise ValueError('Translation needs exactly one unique known phrase_id')
        seen.add(ident)
        phrase = phrases[ident]
        if e.get('source_text') != texts(phrase):
            raise ValueError('Translation source changed; review translation again')
        if not phrase['start'] <= a < b <= phrase['end']:
            raise ValueError('Translation clock must stay inside its own Chinese phrase')
        if e.get('language') != 'en' or not isinstance(e.get('text'), str) or not e['text'].strip():
            raise ValueError('Author nonempty English translation text and language=en')
        if e.get('review_status') not in ('draft', 'reviewed'):
            raise ValueError('Translation review_status must be explicit')
        if e['review_status'] == 'reviewed' and not str(e.get('reviewer', '')).strip():
            raise ValueError('Reviewed translation needs reviewer provenance')
        if e['review_status'] == 'draft' and p.p.get('template_delivery') != 'preview':
            raise ValueError('Draft translations require explicit preview mode')
    if seen != set(phrases):
        raise ValueError('Every bilingual phrase needs its own translation; no silent omission')


def wrap_text(p, text, size, max_width, max_lines=2):
    """Word wrapping with bounded fitting; never ellipsizes or splits a word."""
    normalized = ' '.join(text.split())
    if not normalized:
        raise ValueError('Empty translation')
    for scale in (1., .96, .92, .88, .84, .80, .76, .72):
        font = p.font(size * scale, 'translation')
        rows = ['']
        for word in normalized.split(' '):
            candidate = (rows[-1] + ' ' + word).strip()
            if font.getlength(candidate) <= max_width:
                rows[-1] = candidate
            elif not rows[-1] or font.getlength(word) > max_width:
                break
            else:
                rows.append(word)
        else:
            if len(rows) <= max_lines:
                return rows, size * scale
    raise ValueError('Translation too long: rewrite/resegment faithfully, not below 72%')


def write_srt(plan, path):
    """English only; visible overlap is retained, separate from Chinese SRT."""
    from timeline import srt_time
    events = plan.get('scene_translations', [])
    points = sorted({x for e in events for x in (e['start'], e['end'])})
    rows = []
    for a, b in zip(points, points[1:]):
        value = '\n'.join(e['text'] for e in events if e['start'] <= a < e['end'])
        if not value:
            continue
        if rows and rows[-1][2] == value and abs(rows[-1][1] - a) < 1e-7:
            rows[-1][1] = b
        else:
            rows.append([a, b, value])
    Path(path).write_text('\n'.join(f'{i}\n{srt_time(a)} --> {srt_time(b)}\n{text}\n'
                                   for i, (a, b, text) in enumerate(rows, 1)), encoding='utf8')
