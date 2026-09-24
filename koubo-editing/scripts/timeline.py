"""Frame-accurate edit plan shared by audio, video, captions and effects (stdlib)."""
import json, math, subprocess
from pathlib import Path


def probe(path):
    r = subprocess.run(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(path)],capture_output=True,text=True,check=True)
    return json.loads(r.stdout)


def number(x):
    return isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x)


def load_plan(path, check_files=True):
    path=Path(path).resolve(); p=json.loads(path.read_text(encoding='utf8'))
    if p.get('version')!=2: raise ValueError('Expected plan version 2')
    for field in ['source','font']:
        if not isinstance(p.get(field),str) or not Path(p[field]).is_absolute(): raise ValueError(f'{field} must be absolute')
        if check_files and not Path(p[field]).is_file(): raise ValueError(f'Missing {field}: {p[field]}')
    if not number(p.get('source_duration')) or p['source_duration']<=0: raise ValueError('source_duration required')
    fps=p.get('fps',30); w=p.get('width',720); h=p.get('height',1280)
    if fps not in (24,25,30,50,60) or any(not isinstance(n,int) or n<128 or n%2 for n in (w,h)): raise ValueError('Invalid fps/dimensions')
    if not p.get('clips'): raise ValueError('No clips')
    if p.get('template') not in ('list-cards','knowledge','service'): raise ValueError('Unknown template')
    if p.get('frame_fit','contain') not in ('contain','cover','native'):
        raise ValueError('frame_fit must be contain, cover or native')
    last=0.; seen=set()
    for c in p['clips']:
        if not c.get('id') or c['id'] in seen: raise ValueError('Unique clip id required')
        seen.add(c['id']); a=c.get('start'); b=c.get('end')
        if not number(a) or not number(b) or not 0<=a<b<=p['source_duration']+.001: raise ValueError(f'Invalid bounds: {c["id"]}')
        if round(b*fps)<=round(a*fps): raise ValueError('Clip shorter than one frame')
        if not c.get('reason'): raise ValueError('An editorial reason is required')
        if a<last and not p.get('allow_reorder',False): raise ValueError('Overlapping or reordered clips require allow_reorder')
        last=b
        toks=c.get('words',[]); prev=a
        for t in toks:
            if not str(t.get('text','')).strip(): raise ValueError('Empty word')
            x=t.get('start'); y=t.get('end')
            if not number(x) or not number(y) or not a-.035<=x<=y<=b+.035 or x<prev-.035: raise ValueError(f'Invalid word timing: {t}')
            prev=x
        if not toks and not c.get('caption'): raise ValueError('Each clip needs timed words or an explicit caption')
        for st in c.get('stickers',[]):
            q=Path(st.get('path',''))
            if not q.is_absolute() or (check_files and not q.is_file()): raise ValueError('Sticker path must exist and be absolute')
            if not a<=st['start']<st['end']<=b: raise ValueError('Sticker time outside clip')
            if not all(number(st.get(k)) and 0<=st[k]<=1 for k in ('x','y','width')) or st['width']<=0 or st['x']+st['width']>1: raise ValueError('Invalid sticker placement')
        focus=c.get('focus',[.5,.5]); zoom=c.get('zoom',1.)
        if not number(zoom) or not 1<=zoom<=1.15 or len(focus)!=2 or not all(number(x) and 0<=x<=1 for x in focus): raise ValueError('Invalid zoom/focus')
        if c.get('card'):
            card=c['card']
            if not all(isinstance(card.get(k),str) and card[k] for k in ('label','value')): raise ValueError('Card needs label/value')
            if not a<=card.get('at',a)<=b: raise ValueError('Card anchor outside clip')
        for ev in c.get('caption_events',[]):
            if not number(ev.get('start')) or not number(ev.get('end')) or not a<=ev['start']<ev['end']<=b:
                raise ValueError('Caption event time outside clip')
            if not ev.get('text') and not ev.get('runs'): raise ValueError('Caption event needs text or runs')
            if ev.get('runs'):
                for run in ev['runs']:
                    if not str(run.get('text','')).strip(): raise ValueError('Empty caption run')
        for ev in c.get('viewport_events',[]):
            if not number(ev.get('start')) or not number(ev.get('end')) or not a<=ev['start']<ev['end']<=b:
                raise ValueError('Viewport event time outside clip')
            if ev.get('kind') not in ('dim','circle','blur_band'): raise ValueError('Unknown viewport event kind')
    for r in p.get('removed',[]):
        if not number(r.get('start')) or not number(r.get('end')) or not 0<=r['start']<r['end']<=p['source_duration']+.001:
            raise ValueError('Invalid removed interval')
        for c in p['clips']:
            if min(c['end'],r['end'])-max(c['start'],r['start'])>0.001:
                raise ValueError('Kept clip overlaps an explicitly deleted interval')
    return p


def compile_plan(p):
    """Output timing is integer frame based. Never estimate frame indices from r_frame_rate."""
    p=dict(p)
    if p.get('template_variant'):
        from template_catalog import get
        selected=get(p['template_variant'])
        if 'caption_chars' not in p:
            cfg=selected.get('design_system',{}).get('caption',{})
            if cfg: p['caption_chars']=cfg['chars']
        # The source plan may contain a machine-local placeholder font. Once a
        # template contract is selected, make the contract's bundled font the
        # authoritative, portable metadata and keep every role traceable.
        root=Path(__file__).resolve().parent.parent
        contract=selected.get('_contract',{})
        roles=contract.get('typography',{})
        if roles:
            import hashlib
            font_roles={}
            for role,spec in roles.items():
                raw=Path(spec['file'])
                path=raw if raw.is_absolute() else root/raw
                entry={'path':str(path.resolve()),'index':spec.get('index',0),'weight':spec.get('weight')}
                if path.is_file():
                    entry['sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
                font_roles[role]=entry
            p['font_roles']=font_roles
            body=font_roles.get('body') or next(iter(font_roles.values()))
            p['font']=body['path']
            p['font_source']='skill_bundle_contract'
            p['font_contract_sha256']=selected.get('contract_sha256')
    fps=p.get('fps',30); cursor=0; clips=[]
    for c in p['clips']:
        q=dict(c); sf=round(c['start']*fps); ef=round(c['end']*fps); n=ef-sf
        q.update(source_frame_start=sf,source_frame_end=ef,source_start=sf/fps,source_end=ef/fps,
                 output_frame_start=cursor,output_frame_end=cursor+n,output_start=cursor/fps,output_end=(cursor+n)/fps)
        q['words']=[dict(t,source_word_start=t['start'],source_word_end=t['end'],start=max(cursor/fps,cursor/fps+t['start']-sf/fps),end=min((cursor+n)/fps,cursor/fps+t['end']-sf/fps)) for t in c.get('words',[])]
        # Caption events are authored in source seconds inside a clip, then mapped to output seconds.
        q['caption_events']=[]
        for ev in c.get('caption_events',[]):
            z=dict(ev); z['start']=cursor/fps+ev['start']-sf/fps; z['end']=cursor/fps+ev['end']-sf/fps
            q['caption_events'].append(z)
        q['viewport_events']=[]
        for ev in c.get('viewport_events',[]):
            z=dict(ev); z['start']=cursor/fps+ev['start']-sf/fps; z['end']=cursor/fps+ev['end']-sf/fps
            q['viewport_events'].append(z)
        clips.append(q); cursor+=n
    compiled=dict(p,clips=clips,frame_count=cursor,duration=cursor/fps)
    if p.get('hook_design') is not None:
        from opening_hooks import verify as verify_hook
        compiled['hook_audit']=verify_hook(compiled)
    if p.get('boundary_transitions') is not None:
        from boundary_transitions import compile_transitions
        compiled['boundary_events']=compile_transitions(compiled)
    return compiled


def base_filter(p):
    n=len(p['clips']); fps=p.get('fps',30); w=p.get('width',720); h=p.get('height',1280)
    fit=p.get('frame_fit','contain')
    transform=(f'scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2'
               if fit=='contain' else f'scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}'
               if fit=='cover' else f'scale={w}:{h}')
    # Every video and audio branch has a unique label; no FFmpeg implicit input fallback.
    fs=[f'[0:v]setpts=PTS-STARTPTS,fps={fps},split={n}'+''.join(f'[vi{i}]' for i in range(n)),
        f'[0:a]asetpts=PTS-STARTPTS,asplit={n}'+''.join(f'[ai{i}]' for i in range(n))]
    for i,c in enumerate(p['clips']):
        fs.append(f'[vi{i}]trim=start_frame={c["source_frame_start"]}:end_frame={c["source_frame_end"]},setpts=PTS-STARTPTS,{transform},setsar=1[v{i}]')
        duration=c['source_end']-c['source_start']
        gain=c.get('audio_gain',1.)
        fs.append(f'[ai{i}]atrim=start={c["source_start"]:.9f}:end={c["source_end"]:.9f},asetpts=PTS-STARTPTS,aresample=48000,volume={gain:.6f},afade=t=in:d=0.005,afade=t=out:st={max(0,duration-.005):.9f}:d=0.005[a{i}]')
    fs.append(''.join(f'[v{i}][a{i}]' for i in range(n))+f'concat=n={n}:v=1:a=1[v][a]')
    return ';\n'.join(fs)


def caption_groups(c,max_chars=13):
    groups=[]; group=[]; count=0
    for word in c.get('words',[]):
        text=word['text']; size=len(text)
        if group and (count+size>max_chars or word['start']-group[-1]['end']>.45):
            groups.append(group); group=[]; count=0
        group.append(word); count+=size
        if word.get('caption_break_after') or text[-1:] in '，。！？,!?；;': groups.append(group); group=[]; count=0
    if group: groups.append(group)
    return groups


def srt_time(t):
    ms=round(t*1000); h,ms=divmod(ms,3600000); m,ms=divmod(ms,60000); s,ms=divmod(ms,1000)
    return f'{h:02}:{m:02}:{s:02},{ms:03}'


def write_srt(p,path):
    rows=[]
    for c in p['clips']:
        groups=caption_groups(c,p.get('caption_chars',13))
        if not groups: groups=[[dict(text=c['caption'],start=c['output_start'],end=c['output_end'])]]
        for j,g in enumerate(groups):
            end=groups[j+1][0]['start'] if j+1<len(groups) else c['output_end']
            rows.append(f'{len(rows)+1}\n{srt_time(g[0]["start"])} --> {srt_time(end)}\n'+''.join(w['text'] for w in g)+'\n')
    Path(path).write_text('\n'.join(rows),encoding='utf8')
