"""Semantic clip-boundary transitions on the unchanged frame/audio clock.

An explicit dip uses the actual outgoing/incoming clip frames, not an overlap or a
pre-emptive peek into the next clip. This avoids duplicated speech, unmasked next
frames, caption drift and source-handle assumptions. Match cut is an editorial
QA declaration; its framing must be visually checked, not synthesized here.
"""
import math
from PIL import Image, ImageColor

KINDS={'cut','match_cut','dip_to_dark'}


def _smooth(u):
    u=min(1.,max(0.,u));return u*u*(3-2*u)


def compile_transitions(p):
    raw=p.get('boundary_transitions',[])
    if not isinstance(raw,list):raise ValueError('boundary_transitions must be a list')
    if not raw:return []
    clips=p['clips'];by_id={c['id']:i for i,c in enumerate(clips)};fps=p.get('fps',30)
    seen=set();events=[]
    for e in raw:
        if not isinstance(e,dict):raise ValueError('Invalid boundary transition')
        a,b=e.get('after_clip_id'),e.get('before_clip_id');kind=e.get('kind')
        if a not in by_id or b not in by_id or by_id[b]!=by_id[a]+1:
            raise ValueError('Boundary transition requires adjacent clips in output order')
        if a in seen:raise ValueError('Only one transition per clip boundary')
        seen.add(a)
        if kind not in KINDS or not str(e.get('reason','')).strip():
            raise ValueError('Transition requires known kind and editorial reason')
        left,right=clips[by_id[a]],clips[by_id[b]]
        cut=left['output_frame_end']
        if cut!=right['output_frame_start']:
            raise ValueError('Boundary transition requires an unmodified continuous timeline')
        ev=dict(after_clip_id=a,before_clip_id=b,kind=kind,reason=e['reason'],cut_frame=cut,output_time=cut/fps)
        if kind=='match_cut':
            if not str(e.get('match_basis','')).strip():
                raise ValueError('match_cut needs a visible framing/action match_basis')
            ev['match_basis']=e['match_basis']
        if kind=='dip_to_dark':
            n=e.get('frames',8)
            if type(n)!=int or not 4<=n<=18 or n/fps>.65:
                raise ValueError('dip_to_dark frames must be 4..18 and no longer than .65s')
            if e.get('speech_clearance_verified') is not True:
                raise ValueError('dip_to_dark requires confirmed speech clearance at both sides')
            out_n=n//2;in_n=n-out_n
            if out_n>=left['output_frame_end']-left['output_frame_start'] or in_n>=right['output_frame_end']-right['output_frame_start']:
                raise ValueError('Transition does not fit available clip frames')
            lo=(cut-out_n)/fps;hi=(cut+in_n)/fps
            for c in (left,right):
                if any(w['start']<hi-1e-4 and w['end']>lo+1e-4 for w in c.get('words',[])):
                    raise ValueError('dip_to_dark crosses speech; use a clean cut or reserve silent frames')
                if not c.get('words') and c.get('caption'):
                    raise ValueError('dip_to_dark cannot verify clearance from caption-only clips')
            color=e.get('color','#101018')
            try: rgb=ImageColor.getrgb(color)
            except Exception as ex: raise ValueError('Invalid transition color') from ex
            if len(rgb)!=3 or max(rgb)>100:raise ValueError('Transition color must be dark and non-flashing')
            ev.update(frames=n,out_frames=out_n,in_frames=in_n,start_frame=cut-out_n,end_frame=cut+in_n,
                      color=color,speech_clearance_verified=True,visual_effect='outgoing_to_dark_to_incoming')
        events.append(ev)
    events.sort(key=lambda x:x['cut_frame'])
    dips=[x for x in events if x['kind']=='dip_to_dark']
    for a,b in zip(dips,dips[1:]):
        if a['end_frame']>b['start_frame']:
            raise ValueError('Overlapping boundary transitions')
    return events


def apply(image,frame,events):
    for e in events:
        if e['kind']!='dip_to_dark' or not e['start_frame']<=frame<e['end_frame']:continue
        cut=e['cut_frame'];out_n=e['out_frames'];in_n=e['in_frames']
        if frame<cut:
            alpha=.95*_smooth((frame-(cut-out_n)+1)/(out_n+1))
        else:
            alpha=.95*(1-_smooth((frame-cut)/max(1,in_n-1)))
        return Image.blend(image,Image.new(image.mode,image.size,e['color']),alpha)
    return image


def audit(events):
    return {'clock_policy':'no_frame_or_audio_overlap; no duration change',
            'effect_policy':'dip on fully composed current frame; never reveal incoming source early',
            'events':events,'requires_final_listening_and_cut_frame_review':bool(events)}
