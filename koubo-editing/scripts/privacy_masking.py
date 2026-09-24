"""Authored, output-clock privacy masks. No object detection or inferred tracking.

Boxes locate the sensitive CORE after camera/scene video transforms. Appearance is
procedural and always opaque over that core; human review of the encoded video is
still required before claiming that the detected target was located correctly.
"""
import math
from PIL import Image, ImageDraw, ImageFilter

STYLES = {
    'cloud': {'kinds': ('text', 'object', 'screen'), 'label': '柔边云团', 'color': '#E8E5DC', 'pad': .018},
    'paper-strip': {'kinds': ('text', 'screen', 'object'), 'label': '纸条', 'color': '#F3EEE1', 'pad': .014},
    'solid-card': {'kinds': ('text', 'screen', 'object', 'face'), 'label': '实色信息卡', 'color': '#26272E', 'pad': .016},
    'face-patch': {'kinds': ('face', 'object'), 'label': '面部实心贴', 'color': '#2B2D39', 'pad': .026},
    'face-oval': {'kinds': ('face',), 'label': '柔和实心椭圆', 'color': '#ECE1CF', 'pad': .032},
}
KINDS = {'text', 'screen', 'face', 'object'}


def finite(v):
    return isinstance(v, (float, int)) and not isinstance(v, bool) and math.isfinite(v)


def choose_style(kind, *, preferred=None, mood='neutral'):
    """Make a contextual recommendation; never silently change a user choice."""
    if preferred is not None:
        if preferred not in STYLES or kind not in STYLES[preferred]['kinds']:
            raise ValueError('Requested privacy style cannot cover this target kind')
        return preferred
    return ('face-patch' if kind == 'face' else 'solid-card' if kind == 'screen'
            else 'paper-strip' if mood in ('warm', 'editorial') else 'cloud')


def _box(box):
    if (not isinstance(box, list) or len(box) != 4 or not all(finite(x) for x in box)
            or box[2] <= 0 or box[3] <= 0 or box[0] < 0 or box[1] < 0
            or box[0]+box[2] > 1 or box[1]+box[3] > 1):
        raise ValueError('Privacy core box must be [x,y,width,height] inside the output frame')
    return box


def _interval(ev, clip, fps):
    a,b = ev.get('start'), ev.get('end')
    if (not finite(a) or not finite(b) or not clip['output_start'] <= a < b <= clip['output_end']
            or abs(round(a*fps)/fps-a)>1e-5 or abs(round(b*fps)/fps-b)>1e-5):
        raise ValueError('Privacy intervals must be frame-aligned and inside a named output clip')
    return (round(a*fps), round(b*fps))


def compile_privacy(plan):
    """Validate plan coverage per visible target instance, return safe rendering data."""
    fps=plan.get('fps',30); clips={c['id']:c for c in plan['clips']}
    targets=plan.get('privacy_targets',[]); events=plan.get('privacy_events',[])
    if not isinstance(targets,list) or not isinstance(events,list):
        raise ValueError('Privacy targets/events must be lists')
    ids=set(); tmap={}; visible={}
    for target in targets:
        tid=target.get('id')
        if not isinstance(tid,str) or not tid or tid in ids or target.get('kind') not in KINDS:
            raise ValueError('Unique privacy target id and known kind required')
        ids.add(tid); tmap[tid]=target
        if target.get('origin') not in ('user','ai') or target.get('status') not in ('confirmed','pending'):
            raise ValueError('Privacy target needs origin and confirmation status')
        modalities=target.get('modalities', ['video'])
        if not isinstance(modalities,list) or not modalities or not set(modalities)<= {'video','audio','text'}:
            raise ValueError('Unknown privacy modality')
        if not isinstance(target.get('reason'),str) or not target['reason'].strip():
            raise ValueError('Privacy target needs reason')
        segments=[]
        for v in target.get('visible',[]):
            clip=clips.get(v.get('clip_id'))
            if not clip: raise ValueError('Privacy visibility names an unknown clip')
            start,end=_interval(v,clip,fps)
            if 'video' not in modalities: raise ValueError('Visual interval needs video modality')
            segments.append((v['clip_id'],start,end))
        if 'video' in modalities and not segments:
            raise ValueError('Video target needs visible output intervals')
        visible[tid]=segments
    compiled=[]; seen=set()
    for ev in events:
        ident=ev.get('id'); tid=ev.get('target_id'); clip=clips.get(ev.get('clip_id'))
        if not isinstance(ident,str) or not ident or ident in seen or tid not in tmap or not clip:
            raise ValueError('Privacy event needs unique id, target and clip')
        seen.add(ident); start,end=_interval(ev,clip,fps)
        target=tmap[tid]; style=ev.get('style_id') or choose_style(target['kind'],preferred=target.get('preferred_style'),mood=plan.get('privacy_mood','neutral'))
        if style not in STYLES or target['kind'] not in STYLES[style]['kinds']:
            raise ValueError('Invalid privacy style for target')
        if target.get('preferred_style') and style!=target['preferred_style'] and not ev.get('style_override_confirmed'):
            raise ValueError('User-selected privacy style cannot be silently changed')
        motion=ev.get('motion','static'); keys=ev.get('keyframes')
        if motion not in ('static','keyframes') or (motion=='static') == (keys is not None):
            raise ValueError('Static mask needs box; moving mask needs keyframes')
        if motion=='static':
            boxes=[(start,_box(ev.get('box'))),(end,_box(ev.get('box')))]
        else:
            if not isinstance(keys,list) or len(keys)<2: raise ValueError('Moving mask needs keyframes')
            boxes=[]
            for key in keys:
                if not finite(key.get('time')):raise ValueError('Invalid privacy keyframe time')
                frame=round(key['time']*fps)
                if abs(frame/fps-key['time'])>1e-5 or not start<=frame<=end:
                    raise ValueError('Privacy keyframe must align to an event frame')
                boxes.append((frame,_box(key.get('box'))))
            if boxes[0][0]!=start or boxes[-1][0]!=end or any(b[0]<=a[0] for a,b in zip(boxes,boxes[1:])):
                raise ValueError('Privacy keyframes must be ordered and span the event')
            if any(b[0]-a[0]>max(1,round(.25*fps)) for a,b in zip(boxes,boxes[1:])):
                raise ValueError('Moving mask keyframe gap too large; add observed positions')
        if ev.get('occlusion') not in (None,'none'):
            raise ValueError('Automatic foreground occlusion is not supported; author visible intervals explicitly')
        compiled.append({'id':ident,'target_id':tid,'clip_id':clip['id'],'style_id':style,
                         'start_frame':start,'end_frame':end,'boxes':boxes,'motion':motion,
                         'reason':ev.get('reason') or target['reason']})
    for tid,target in tmap.items():
        for cid,start,end in visible[tid]:
            for frame in range(start,end):
                if not any(ev['target_id']==tid and ev['clip_id']==cid and ev['start_frame']<=frame<ev['end_frame'] for ev in compiled):
                    raise ValueError('Privacy target has uncovered visible output frames')
    audio=plan.get('audio_redactions',[])
    if not isinstance(audio,list):raise ValueError('audio_redactions must be a list')
    for r in audio:
        if r.get('target_id') not in tmap or r.get('clip_id') not in clips:
            raise ValueError('Unknown audio redaction target or clip')
        c=clips[r['clip_id']]; a,b=r.get('source_start'),r.get('source_end')
        if not finite(a) or not finite(b) or not c['source_start']<=a<b<=c['source_end']:
            raise ValueError('Audio redaction must be within a named source clip')
    for target in targets:
        modalities=target.get('modalities',['video'])
        if target['status']=='confirmed' and 'audio' in modalities:
            audible=target.get('audible',[])
            if not isinstance(audible,list) or not audible:
                raise ValueError('Confirmed audio target requires audible intervals and audio redaction')
            for interval in audible:
                clip=clips.get(interval.get('clip_id'))
                if not clip:raise ValueError('Unknown audible clip instance')
                start,end=interval.get('source_start'),interval.get('source_end')
                if not finite(start) or not finite(end) or not clip['source_start']<=start<end<=clip['source_end']:
                    raise ValueError('Audible interval outside its source clip')
                coverage=sorted((r['source_start'],r['source_end']) for r in audio
                                if r['target_id']==target['id'] and r['clip_id']==clip['id'])
                cursor=start
                for a,b in coverage:
                    if a<=cursor+1e-6:cursor=max(cursor,b)
                if cursor<end-1e-6:
                    raise ValueError('Confirmed audio target requires audio redaction in every audible clip instance')
        if target['status']=='confirmed' and 'text' in modalities:
            if target.get('text_review')!='redacted' or not isinstance(target.get('match_terms'),list) or not all(isinstance(x,str) and x.strip() for x in target['match_terms']) or not target['match_terms']:
                raise ValueError('Confirmed text target requires reviewed redaction and private match terms')
    return {'targets':targets,'events':compiled,'audio_redactions':audio,
            'confirmation':'pending' if any(t['status']=='pending' for t in targets) else 'confirmed'}


def box_at(ev,frame):
    boxes=ev['boxes']
    for (fa,a),(fb,b) in zip(boxes,boxes[1:]):
        if fa<=frame<=fb:
            q=(frame-fa)/(fb-fa) if fb>fa else 0
            # Conservative envelope: never narrower than either observed box.
            return [min(a[0],b[0]),min(a[1],b[1]),max(a[0]+a[2],b[0]+b[2])-min(a[0],b[0]),
                    max(a[1]+a[3],b[1]+b[3])-min(a[1],b[1])]
    return boxes[-1][1]


def paint(canvas,compiled,t,fps):
    frame=round(t*fps); result=canvas.convert('RGBA')
    for ev in compiled['events']:
        if not ev['start_frame']<=frame<ev['end_frame']:continue
        core=box_at(ev,frame); w,h=result.size; x,y,bw,bh=core
        x0=max(0,math.floor(x*w));y0=max(0,math.floor(y*h));x1=min(w,math.ceil((x+bw)*w));y1=min(h,math.ceil((y+bh)*h))
        style=STYLES[ev['style_id']]; pad=max(3,round(style['pad']*w)); outer=(max(0,x0-pad),max(0,y0-pad),min(w,x1+pad),min(h,y1+pad))
        layer=Image.new('RGBA',result.size,(0,0,0,0)); draw=ImageDraw.Draw(layer)
        if ev['style_id']=='cloud':
            m=Image.new('L',result.size); d=ImageDraw.Draw(m)
            d.rounded_rectangle(outer,radius=min(pad*2,(outer[3]-outer[1])//2),fill=255)
            # Deterministic small lobes break the rectangle silhouette; the private
            # core below remains fully opaque regardless of antialiasing/feather.
            for frac,size in ((.12,.8),(.38,1.15),(.7,.9),(.91,.65)):
                cx=outer[0]+(outer[2]-outer[0])*frac; r=pad*size
                for cy in (outer[1]+pad*.35,outer[3]-pad*.35):
                    d.ellipse((cx-r,cy-r,cx+r,cy+r),fill=255)
            m=m.filter(ImageFilter.GaussianBlur(max(1,pad//3)))
            d=ImageDraw.Draw(m);d.rectangle((x0,y0,x1,y1),fill=255)
            fill=Image.new('RGBA',result.size,style['color']);fill.putalpha(m);result.alpha_composite(fill)
        else:
            if ev['style_id']=='face-oval':
                draw.ellipse(outer,fill=style['color'])
            else:
                radius=pad//2 if ev['style_id']!='paper-strip' else 1
                draw.rounded_rectangle(outer,radius=radius,fill=style['color'])
            # Drawing the sensitive core last makes coverage independent of edge antialiasing.
            draw.rectangle((x0,y0,x1,y1),fill=style['color'])
            result.alpha_composite(layer)
    return result


def audit(compiled,plan):
    targets=compiled['targets'];fps=plan['fps']
    risk=set()
    for ev in compiled['events']:
        risk.update((ev['start_frame'],max(ev['start_frame'],ev['end_frame']-1)))
        risk.update(k[0] for k in ev['boxes'])
    for c in plan['clips']:
        risk.update((c['output_frame_start'],max(0,c['output_frame_end']-1)))
    for ev in plan.get('boundary_events',[]):
        if 'cut_frame' in ev:risk.update((ev['cut_frame']-1,ev['cut_frame']))
    for key in plan.get('camera_motion',{}).get('keyframes',[]):
        f=round(key['time']*fps);risk.update((f-1,f,f+1))
    for ev in plan.get('scene_canvas',[]):
        for t in (ev.get('start'),ev.get('end')):
            if finite(t):
                f=round(t*fps);risk.update((f-1,f))
    risk.update((0,max(0,plan['frame_count']-2),plan['frame_count']-1))
    audio_ranges=[]
    clips={c['id']:c for c in plan['clips']}
    for r in compiled['audio_redactions']:
        c=clips[r['clip_id']]
        audio_ranges.append({'target_id':r['target_id'],'clip_id':r['clip_id'],
                             'start':c['output_start']+r['source_start']-c['source_start'],
                             'end':c['output_start']+r['source_end']-c['source_start']})
    return {'coverage':'pending_encoded_visual_review' if targets else 'not_applicable',
            'composition':'pending' if targets else 'not_applicable','style':'pending' if targets else 'not_applicable',
            'confirmation':compiled['confirmation'],'risk_frames':sorted(f for f in risk if 0<=f<plan['frame_count']),
            'targets':[{'id':t['id'],'kind':t['kind'],'status':t['status']} for t in targets],
            'review_ranges':[{'target_id':t['id'],'clip_id':cid,'start':a/fps,'end':b/fps}
                             for t in targets for cid,a,b in [(v['clip_id'],round(v['start']*fps),round(v['end']*fps)) for v in t.get('visible',[])]],
            'events':[{'id':e['id'],'target_id':e['target_id'],'clip_id':e['clip_id'],
                       'style_id':e['style_id'],'start_frame':e['start_frame'],'end_frame':e['end_frame'],
                       'reason':e['reason']} for e in compiled['events']],
            'audio_redactions':len(compiled['audio_redactions']),
            'audio_review_ranges':audio_ranges,
            'public_delivery_allowed':not targets}


def scan_text(plan,output_dir):
    """Check declared sensitive strings in delivered text; never echo them in QA."""
    from pathlib import Path
    terms=[]
    for target in plan.get('privacy_targets',[]):
        if 'text' in target.get('modalities',['video']):
            terms.extend(target.get('match_terms',[]))
    outputs=[Path(output_dir)/name for name in ('captions.srt','captions.en.srt','translations.json')]
    strings=[(path.name,path.read_text(encoding='utf8')) for path in outputs if path.is_file()]
    strings.extend([(key,str(plan.get(key,''))) for key in ('title','subtitle')])
    leak_files=sorted({file for file,text in strings for term in terms if term.casefold() in text.casefold()})
    return {'status':'failed' if leak_files else 'requires_visual_and_audio_review' if terms else 'not_machine_checkable',
            'leak_files':leak_files,'checked_files':[file for file,_ in strings]}


def redact_compiled_text(plan):
    """Redact declared strings in a compiled plan, including template scene layers."""
    terms=[term for t in plan.get('privacy_targets',[]) if 'text' in t.get('modalities',['video'])
           for term in t.get('match_terms',[])]
    if not terms:return
    def replace(text):
        for term in sorted(terms,key=len,reverse=True):
            text=text.replace(term,'[已隐藏]')
        return text
    def walk(obj):
        if isinstance(obj,list):
            for item in obj:walk(item)
        elif isinstance(obj,dict):
            for key,value in obj.items():
                if key in ('text','caption','label','value') and isinstance(value,str):obj[key]=replace(value)
                elif isinstance(value,(dict,list)):walk(value)
    for field in ('clips','scene_captions','scene_tags','scene_translations','caption_events'):
        walk(plan.get(field,[]))
    for field in ('title','subtitle'):
        if isinstance(plan.get(field),str):plan[field]=replace(plan[field])
    for field in ('scene_title_lines',):
        if isinstance(plan.get(field),list):plan[field]=[replace(s) if isinstance(s,str) else s for s in plan[field]]
