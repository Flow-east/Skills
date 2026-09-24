#!/usr/bin/env python3
"""Apply explicitly accepted review candidates to a plan; never auto-accepts anything."""
import argparse,json,copy
from pathlib import Path

def apply(plan, review):
    p=copy.deepcopy(plan); candidates=p.get('review',{}).get('review_candidates',[])
    accepted=review.get('accept',[])
    if not all(isinstance(i,int) and 1<=i<=len(candidates) for i in accepted): raise ValueError('accept must contain valid 1-based candidate numbers')
    removed=[dict(candidates[i-1],reason='用户确认：'+candidates[i-1]['reason']) for i in accepted]
    p['removed']=p.get('removed',[])+removed
    # Split kept clips around accepted removals so timeline validation cannot reintroduce deleted speech.
    new=[]
    for c in p['clips']:
        pieces=[(c['start'],c['end'])]
        for r in removed:
            next=[]
            for a,b in pieces:
                if r['end']<=a or r['start']>=b: next.append((a,b)); continue
                if a<r['start']: next.append((a,min(b,r['start'])))
                if r['end']<b: next.append((max(a,r['end']),b))
            pieces=next
        for j,(a,b) in enumerate(pieces):
            q=copy.deepcopy(c); q['id']=c['id']+('_p'+str(j+1) if len(pieces)>1 else '') ;q['start']=a;q['end']=b
            q['words']=[w for w in c.get('words',[]) if w['end']>a and w['start']<b]
            if not q['words']: continue
            for field in ('caption_events','viewport_events'):
                q[field]=[e for e in c.get(field,[]) if e['end']>a and e['start']<b]
            new.append(q)
    p['clips']=new;p['review']['status']='review-applied';p['review']['accepted_candidates']=accepted
    return p
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('plan');ap.add_argument('--review',required=True);ap.add_argument('--out',required=True);a=ap.parse_args(); out=Path(a.out)
 if out.exists():ap.error('output exists; choose a new version')
 p=apply(json.loads(Path(a.plan).read_text()),json.loads(Path(a.review).read_text()));out.write_text(json.dumps(p,ensure_ascii=False,indent=2));print(out.resolve())
