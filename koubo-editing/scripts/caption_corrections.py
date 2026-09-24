"""Apply authored caption corrections across ASR token boundaries.
Does not choose corrections, touch source audio, or alter the raw transcript.
Every correction is bound to an exact source span and exact old text; mismatches
fail rather than reporting a successful correction that never reached subtitles.
"""
import copy


def apply(plan, corrections):
    p=copy.deepcopy(plan);log=[]
    for edit in corrections:
        found=[]
        for ci,c in enumerate(p['clips']):
            selected=[i for i,w in enumerate(c.get('words',[]))
                      if w['start']>=edit['start']-.0001 and w['end']<=edit['end']+.0001]
            if not selected: continue
            joined=''.join(c['words'][i]['text'] for i in selected)
            if joined==edit['old']: found.append((ci,selected))
        if len(found)!=1: raise ValueError(f"Correction must match once at source span: {edit}")
        ci,ix=found[0];c=p['clips'][ci]
        if ix!=list(range(ix[0],ix[-1]+1)): raise ValueError('Correction is not contiguous')
        if c.get('caption_events') or c.get('caption'): raise ValueError('Correct words before authoring captions/events')
        old=c['words'][ix[0]:ix[-1]+1]
        c['words'][ix[0]:ix[-1]+1]=[dict(text=edit['new'],start=old[0]['start'],end=old[-1]['end'])]
        log.append(dict(edit,applied=True,clip_id=c['id'],old_words=old))
    p['caption_corrections']=p.get('caption_corrections',[])+log
    return p
