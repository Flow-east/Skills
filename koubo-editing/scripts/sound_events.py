"""Explicit, clip-instance-bound sound punctuation on the compiled output timeline."""
import hashlib, json, math, wave
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parent.parent
LIB=ROOT/'assets/sfx'
STYLES={
    'ref_gold_v1':'premium','ref_browngold_v1':'premium',
    'ref_neon_v1':'bright','ref_hotpink_v1':'bright',
    'ref_mono_v1':'minimal','ref_cleanwhite_v1':'minimal',
}

def finite(v): return type(v) in (int,float) and math.isfinite(v)

def library():
    catalog=LIB/'catalog.json'
    if not catalog.is_file(): raise ValueError(f'Missing sound catalog: {catalog}')
    data=json.loads(catalog.read_text())
    if data.get('version')!=1: raise ValueError('Unsupported sound library')
    assets=data['assets']
    if len({a['id'] for a in assets})!=len(assets): raise ValueError('Duplicate sound asset id')
    return {a['id']:a for a in assets}

def compile_events(plan):
    """Validate and map source time within a specific clip instance, never by source alone."""
    raw=plan.get('sound_events',[])
    if not isinstance(raw,list): raise ValueError('sound_events must be a list')
    if not raw: return []
    if plan.get('audio',{}).get('cues',True):
        raise ValueError('Set audio.cues=false when using explicit sound_events')
    sounds=library(); clips={c['id']:c for c in plan['clips']}
    style=plan.get('audio',{}).get('sound_style',STYLES.get(plan.get('template_variant'),'neutral'))
    if style not in ('neutral','premium','bright','minimal'): raise ValueError('Unknown sound_style')
    seen=set(); events=[]; sr=48000
    for ev in raw:
        ident=ev.get('id'); cid=ev.get('clip_id'); aid=ev.get('asset_id')
        if not isinstance(ident,str) or not ident or ident in seen: raise ValueError('Unique sound event id required')
        seen.add(ident)
        if cid not in clips or aid not in sounds: raise ValueError(f'Unknown clip/asset in sound event {ident}')
        a=sounds[aid]; c=clips[cid]
        if a.get('selection_status')!='approved':
            raise ValueError(f'Sound asset {aid} is not approved for use; reference-first audition required')
        if ev.get('role') not in a.get('roles',[a['role']]) or not str(ev.get('reason','')).strip():
            raise ValueError(f'Sound event {ident} requires matching role and semantic reason')
        if style not in a['styles']: raise ValueError(f'Sound {aid} not allowed in {style} style')
        if ('source_time' in ev)==('word_index' in ev): raise ValueError('Choose exactly one anchor type')
        if 'word_index' in ev:
            ix=ev['word_index']; edge=ev.get('edge','end')
            if type(ix)!=int or ix<0 or ix>=len(c.get('words',[])) or edge not in ('start','end'):
                raise ValueError(f'Invalid word anchor in {ident}')
            anchor=c['words'][ix][edge]
        else:
            src=ev['source_time']
            if not finite(src) or not c['source_start']<=src<=c['source_end']:
                raise ValueError(f'Source anchor outside clip {ident}')
            anchor=c['output_start']+src-c['source_start']
        gain=ev.get('gain',.12)
        if not finite(gain) or not 0<gain<=.20: raise ValueError('Event gain must be in (0, .20]')
        offset=ev.get('offset',0)
        if not finite(offset) or abs(offset)>.20: raise ValueError('Event offset exceeds .20s')
        hit=anchor+offset; start=hit-a['hit_seconds']; end=start+a['duration']
        if start<-.00001 or end>plan['duration']+.00001:
            raise ValueError(f'Sound event {ident} would clip lead/tail; move anchor or choose shorter asset')
        path=LIB/a['file']
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=a['sha256']:
            raise ValueError(f'Missing or modified sound asset: {aid}')
        with wave.open(str(path)) as f:
            if f.getnchannels()!=1 or f.getsampwidth()!=2 or f.getframerate()!=sr or abs(f.getnframes()/sr-a['duration'])>1/sr:
                raise ValueError(f'Invalid sound asset format: {aid}')
        events.append(dict(id=ident,clip_id=cid,asset_id=aid,asset_file=a['file'],asset_source=a.get('source_url'),asset_license=a.get('license'),role=ev['role'],reason=ev['reason'],
                           style=style,source_time=ev.get('source_time'),word_index=ev.get('word_index'),
                           anchor_output=round(anchor,6),hit_output=round(hit,6),
                           start_output=round(start,6),end_output=round(end,6),gain=gain,
                           sha256=a['sha256'],original_sound_review=plan.get('audio',{}).get('original_sound_review','pending')))
    events.sort(key=lambda x:x['start_output'])
    for left,right in zip(events,events[1:]):
        if right['start_output']<left['end_output']+.04:
            raise ValueError(f'Overlapping sound events: {left["id"]}, {right["id"]}; choose one semantic emphasis')
    return events

def add_events(mix,plan):
    events=compile_events(plan)
    for ev in events:
        with wave.open(str(LIB/ev['asset_file'])) as f:
            audio=np.frombuffer(f.readframes(f.getnframes()),dtype='<i2').astype(np.float32)/32768
        # Short edge ramps avoid discontinuity; never cut the authored tail.
        ramp=min(len(audio)//2,round(.008*48000))
        if ramp:
            audio[:ramp]*=np.linspace(0,1,ramp,dtype=np.float32)
            audio[-ramp:]*=np.linspace(1,0,ramp,dtype=np.float32)
        pos=round(ev['start_output']*48000)
        if pos<0 or pos+len(audio)>len(mix): raise ValueError(f'Sound event outside PCM duration: {ev["id"]}')
        mix[pos:pos+len(audio)]+=ev['gain']*audio
        ev['pcm_start_sample']=pos; ev['pcm_samples']=len(audio)
    return events
