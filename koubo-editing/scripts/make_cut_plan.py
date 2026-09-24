#!/usr/bin/env python3
"""Compile explicit editorial decisions, never treat regex as semantic understanding."""
import argparse, json, copy
from pathlib import Path
from timeline import load_plan, probe



def infer_semantic_marks(words):
    """Conservative lexical candidates; Codex/editor may review or override before render."""
    text=''.join(w['text'] for w in words)
    rules=[
      ('negative', ['不要','别','不买','避开','错误','千万别'], '#E84B4B'),
      ('warning', ['注意','小心','风险','坑','警惕'], '#FF8A3D'),
      ('number', ['第一个','第二个','第三个','第一','第二','第三','%','百分之','块钱','个月'], '#55DFC3'),
      ('recommendation', ['推荐','适合','可以选','建议','首选','选择'], '#FFD52F'),
      ('conclusion', ['所以','记住','关键是','结论','一定要','才是','最重要'], '#55DFC3'),
      ('transition', ['但是','不过','最后','接下来','然后','另外'], '#F2B8C6')]
    marks=[]
    # Recommendation pattern: emit one short scenario→choice unit for each “选”.
    search=0
    while True:
        at=text.find('选',search)
        if at<0: break
        start=max(0,at-6); end=min(len(text),at+7); search=at+1
        pos=0; selected=[]
        for w in words:
            e=pos+len(w['text'])
            if pos<end and e>start: selected.append(w)
            pos=e
        if selected:
            marks.append({'kind':'recommendation','start':selected[0]['start'],'end':selected[-1]['end'],
                          'value':text[at+1:end],'accent':'#FFD52F','position':'lower_center'})
    for kind, needles, accent in rules:
        for needle in needles:
            at=text.find(needle)
            if at<0: continue
            pos=0; selected=[]
            for w in words:
                end=pos+len(w['text'])
                if pos<at+len(needle) and end>at: selected.append(w)
                pos=end
            if selected:
                marks.append({'kind':kind,'start':selected[0]['start'],'end':selected[-1]['end'],
                              'value':needle,'accent':accent,'position':'lower_center'})
            break
    return marks

def make_plan(raw, decisions):
    source=raw.get('source',raw.get('video'))
    if not source: raise ValueError('Transcript missing source path')
    p=copy.deepcopy(decisions); p['version']=2; p['source']=source
    p.setdefault('source_duration',raw.get('source_duration'))
    words=[dict(text=w.get('word',w.get('text','')),start=w['start'],end=w['end']) for s in raw['segments'] for w in s.get('words',[])]
    if not words: raise ValueError('No word timestamps: obtain alignment before word-level edits')
    for c in p['clips']:
        if 'words' not in c:
            c['words']=[dict(w,start=max(w['start'],c['start']),end=min(w['end'],c['end'])) for w in words if w['end']>c['start'] and w['start']<c['end'] and w['text'].strip()]
        if not c['words']: raise ValueError(f'Clip {c["id"]} contains no speech')
        if p.get('auto_semantics') and not c.get('semantic_marks'):
            c['semantic_marks']=infer_semantic_marks(c['words'])
        # Convert authored semantic marks into rich-text events after word alignment is available.
        marks=c.get('semantic_marks') or p.get('semantic_marks',[])
        generated=[]
        for mark in marks:
            a=mark.get('start',mark.get('at')); b=mark.get('end')
            if a is None or b is None or b<=a or b<=c['start'] or a>=c['end']: continue
            selected=[w for w in c['words'] if w['end']>a and w['start']<b]
            if not selected: continue
            label=mark.get('label'); value=mark.get('value')
            kind=mark.get('kind','emphasis')
            defaults={'recommendation':('#FFD52F','burst'),'negative':('#E84B4B','rays'),'warning':('#FF8A3D','rays'),'number':('#55DFC3','sparkle'),'conclusion':('#55DFC3','burst'),'transition':('#F2B8C6','sparkle')}
            default_accent,default_effect=defaults.get(kind,('#FFD52F',None))
            accent=mark.get('accent',default_accent)
            effect=mark.get('effect',default_effect)
            default_enter={'recommendation':'pop','negative':'pop','warning':'rise','number':'scale','conclusion':'pop','transition':'rise'}.get(kind,'pop')
            runs=[]
            joined=''.join(w['text'] for w in selected); cursor=0; ranges=[]
            for needle in (value,label):
                if needle:
                    at=joined.find(str(needle))
                    if at>=0: ranges.append((at,at+len(str(needle))))
            for w in selected:
                txt=w['text']; span=(cursor,cursor+len(txt)); cursor=span[1]
                hit=bool(w.get('emphasis')) or any(span[0]<e and span[1]>a for a,e in ranges)
                runs.append({'text':txt,'style':'keyword' if hit else 'base', 'size':mark.get('keyword_size',52) if hit else mark.get('base_size',40), 'fill':accent if hit else '#FFFFFF', 'extrude':bool(hit and mark.get('extrude',False))})
            event={'start':a,'end':b,'position':mark.get('position',c.get('caption_position','lower_center')), 'runs':runs, 'enter':mark.get('enter',default_enter), 'effect':effect, 'layout':'scenario_choice' if kind=='recommendation' else mark.get('layout')}
            if mark.get('sticker'):
                event['sticker_candidate']={'kind':mark['sticker'],'reason':mark.get('sticker_reason','语义标记明确要求辅助符号；需检查已有素材后再生成')}
            generated.append(event)
        if generated and not c.get('caption_events'): c['caption_events']=generated
        if p.get('auto_viewport') and not c.get('viewport_events'):
            c['viewport_events']=[]
            for mark in marks:
                kind=mark.get('kind'); a=mark.get('start',mark.get('at')); b=mark.get('end')
                if kind not in ('conclusion','number') or a is None or b is None: continue
                if kind=='number' and p.get('shot_type','wide') in ('wide','full'): continue
                # Keep the change short and subtle; avoid turning every sentence into a scene transition.
                c['viewport_events'].append({'kind':'dim' if kind=='conclusion' else 'circle', 'start':a, 'end':min(b,a+.85),
                    'alpha':.16 if kind=='conclusion' else None, 'center':[.5,.42], 'radius':.34, 'background':'#F8F0DF'})
            c['viewport_events']=[{k:v for k,v in e.items() if v is not None} for e in c['viewport_events']]
    return p

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('transcript'); ap.add_argument('--decisions',required=True); ap.add_argument('--out',required=True); a=ap.parse_args()
    out=Path(a.out)
    if out.exists(): ap.error('Output exists; choose a new version')
    raw=json.loads(Path(a.transcript).read_text()); d=json.loads(Path(a.decisions).read_text()); p=make_plan(raw,d)
    if not p.get('source_duration'): p['source_duration']=float(probe(p['source'])['format']['duration'])
    out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(p,ensure_ascii=False,indent=2),encoding='utf8')
    load_plan(out); print(out.resolve())
