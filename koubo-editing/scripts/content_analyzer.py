#!/usr/bin/env python3
"""Content-level editorial analysis for spoken videos.
Identifies recommendation sentences, structural fillers, chatter and likely retakes.
It produces candidates and reasons; it never silently changes the source transcript.
"""
import re

def _text(words): return ''.join(w['text'] for w in words)
def _clean(s): return s.strip('，。！？,.!? 、 ')

def analyze(words):
    words=[dict(w,text=str(w.get('text',w.get('word','')))) for w in words]
    units=[]; candidates=[]; keep=[]
    # Pause-separated content units, intentionally shorter threshold than clip grouping.
    groups=[]; cur=[]
    for w in words:
        if cur and w['start']-cur[-1]['end']>.72: groups.append(cur); cur=[]
        cur.append(w)
    if cur: groups.append(cur)
    for i,g in enumerate(groups):
        text=_text(g)
        kind='other'
        if '选' in text and len(text)>=4: kind='recommendation'
        elif any(x in text for x in ('OK','没事','切吧','没错')): kind='production_chatter'
        elif text in ('好的','好','对'): kind='confirmation'
        units.append({'index':i+1,'start':g[0]['start'],'end':g[-1]['end'],'text':text,'type':kind})
        if kind=='production_chatter':
            candidates.append({'start':g[0]['start'],'end':g[-1]['end'],'text':text,'category':'production_chatter','confidence':'high','reason':'现场确认、纠错或催剪，不向观众提供信息'})
        elif kind=='confirmation':
            candidates.append({'start':g[0]['start'],'end':g[-1]['end'],'text':text,'category':'confirmation','confidence':'high','reason':'口播后的录制确认，不承担主题信息'})
    # Structural words inside recommendation units.
    for g in groups:
        text=_text(g)
        if '选' not in text: continue
        for i,w in enumerate(g):
            t=_clean(w['text'])
            if t=='那个' and i+1<len(g) and _clean(g[i+1]['text']) in {'调研','代码','产品','功能','方案','问题'}:
                candidates.append({'start':w['start'],'end':w['end'],'text':'那个','category':'structural_filler','confidence':'high','reason':'删除后仍保留“场景+选+模型”的完整推荐句式'})
    # Similar recommendation groups: preserve the later complete take when chatter sits between.
    rec=[u for u in units if u['type']=='recommendation']
    for a,b in zip(rec,rec[1:]):
        if a['text']==b['text'] and b['start']-a['end']<8:
            candidates.append({'start':a['start'],'end':a['end'],'text':a['text'],'category':'earlier_take','confidence':'high','reason':'后面存在相同且更完整的重录版本，前一遍不应重复保留'})
    for u in units:
        if u['type']=='recommendation': keep.append({'start':u['start'],'end':u['end'],'text':u['text'],'reason':'有效推荐主句，保留模型/场景信息'})
    return {'units':units,'deletion_candidates':candidates,'keep_reasons':keep}
