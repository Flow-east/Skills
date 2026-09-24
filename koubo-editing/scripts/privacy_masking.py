"""Authored, output-clock privacy masks. No object detection or inferred tracking.

Boxes locate the sensitive CORE after camera/scene video transforms. Privacy
styles (procedural or raster art) are always opaque over that core; human
review of the encoded video is still required before claiming that the detected target was located correctly.
"""
import json
import math
from functools import lru_cache
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter
from sticker_catalog import resolve

# Privacy-capable stickers are one part of the broader, portable sticker catalogue.
CATALOG = json.loads((Path(__file__).resolve().parents[1]/'assets/stickers/catalog.json').read_text(encoding='utf8'))
STYLES = {v['id']: {'kinds': tuple(v['targets']), 'label': v['name'], 'color': v['color'],
                    'pad': v['pad'], 'family': v['family'], 'asset': 'path' in v}
          for v in CATALOG['privacy']+CATALOG['decorative'] if v['privacy_safe']}

KINDS = {'text', 'screen', 'face', 'object'}


def finite(v):
    return isinstance(v, (float, int)) and not isinstance(v, bool) and math.isfinite(v)


def choose_style(kind, *, preferred=None, mood='neutral'):
    """Make a contextual recommendation; never silently change a user choice."""
    if preferred is not None:
        if preferred not in STYLES or kind not in STYLES[preferred]['kinds']:
            raise ValueError('Requested privacy style cannot cover this target kind')
        return preferred
    return ('cloud' if kind == 'text' and mood not in ('tech', 'serious')
            else 'mosaic-warm' if kind == 'screen' and mood in ('warm', 'calm', 'playful')
            else 'mosaic-charcoal' if kind in ('text', 'screen') and mood in ('tech', 'serious')
            else 'mosaic-neutral' if kind == 'screen' and mood == 'neutral'
            else 'mascot-cloud' if kind == 'face' and mood in ('warm', 'playful')
            else 'flower-doodle' if kind == 'face' and mood == 'editorial'
            else 'pixel-confetti' if kind == 'face'
            else 'brush-swipe' if kind == 'text' and mood in ('warm', 'editorial')
            else 'mosaic-neutral' if kind in ('text', 'screen') else 'cloud')


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
        if STYLES[style]['asset']:
            samples=[b for _,b in boxes]
            samples += [[min(a[0],b[0]),min(a[1],b[1]),max(a[0]+a[2],b[0]+b[2])-min(a[0],b[0]),
                         max(a[1]+a[3],b[1]+b[3])-min(a[1],b[1])]
                        for (_,a),(_,b) in zip(boxes,boxes[1:])]
            w,h=plan['width'],plan['height']
            for bx,by,bw,bh in samples:
                core=(max(0,math.floor(bx*w)),max(0,math.floor(by*h)),
                      min(w,math.ceil((bx+bw)*w)),min(h,math.ceil((by+bh)*h)))
                _asset_position(style,core,(w,h))
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



@lru_cache(maxsize=96)
def _fitted_asset(style_id, width, height):
    """Fit a complete sticker so every pixel of the sensitive box lies inside its opaque art."""
    path=resolve(style_id)['path']
    with Image.open(path) as source: art=source.convert('RGBA')
    scale=max(width*1.2/art.width,height*1.2/art.height)
    for step in range(28):
        factor=scale*1.10**step
        sw=max(1,round(art.width*factor));sh=max(1,round(art.height*factor))
        if sw>width*5+80 or sh>height*5+80:break
        sprite=art.resize((sw,sh),Image.Resampling.LANCZOS)
        xx=(sw-width)//2;yy=(sh-height)//2
        if xx<0 or yy<0:continue
        if sprite.getchannel('A').crop((xx,yy,xx+width,yy+height)).getextrema()==(255,255):
            return sprite
    raise ValueError('Sticker cannot reliably cover the entire privacy core')


def _asset_position(style_id,core,frame_size):
    x0,y0,x1,y1=core;w,h=frame_size
    sprite=_fitted_asset(style_id,x1-x0,y1-y0)
    x=round((x0+x1-sprite.width)/2);y=round((y0+y1-sprite.height)/2)
    if x<0 or y<0 or x+sprite.width>w or y+sprite.height>h:
        raise ValueError('Privacy sticker exceeds the frame; choose a smaller style or move target')
    return sprite,x,y


@lru_cache(maxsize=128)
def _cloud_alpha(width, height, pad):
    """Generate a soft, irregular silhouette for this box size, not a fixed PNG."""
    margin=max(3,min(pad,round(min(width,height)*.18)))
    halo=max(5,round(margin*2.4))
    mask=Image.new('L',(width+2*halo,height+2*halo),0)
    d=ImageDraw.Draw(mask)
    d.rounded_rectangle((halo-margin,halo-margin,halo+width+margin,
                         halo+height+margin),radius=max(2,round(margin*.9)),fill=255)
    # Scallops protrude beyond the rounded base; their spacing scales with
    # the target aspect ratio so a short name and a long nameplate differ.
    count=max(3,min(11,round(width/max(12,height*.6))))
    for n in range(count):
        frac=(n+.5)/count
        rx=max(margin*1.4,width/count*(.60+.09*((n*7)%4)))
        ry=margin*(1.12+.08*((n*5)%3))
        cx=halo+width*frac
        for top in (True,False):
            cy=halo-margin*.14 if top else halo+height+margin*.12
            offset=(n%3-1)*margin*.12
            d.ellipse((cx-rx,cy-ry+offset,cx+rx,cy+ry+offset),fill=255)
    for frac,size in ((.22,.95),(.73,1.15)):
        cy=halo+height*frac;r=margin*size
        for cx in (halo-margin*.15,halo+width+margin*.2):
            d.ellipse((cx-r*.8,cy-r,cx+r*.8,cy+r),fill=255)
    mask=mask.filter(ImageFilter.GaussianBlur(max(.8,margin*.26)))
    # No alpha reduction is permitted over any of the sensitive core.
    ImageDraw.Draw(mask).rectangle((halo,halo,halo+width-1,halo+height-1),fill=255)
    return mask,halo


def _sticker(canvas,style_id,core,outer,pad):
    """Draw original sticker art. Every shape has an opaque core independent of its decorative edge."""
    layer=Image.new('RGBA',canvas.size,(0,0,0,0)); d=ImageDraw.Draw(layer)
    x0,y0,x1,y1=core; ox0,oy0,ox1,oy1=outer
    fill=STYLES[style_id]['color']
    if STYLES[style_id]['asset']:
        sprite,x,y=_asset_position(style_id,core,canvas.size)
        layer.alpha_composite(sprite,(x,y))
    elif style_id in ('mosaic-neutral','mosaic-warm','mosaic-charcoal'):
        # Opaque source-independent pixels: conventional mosaic look without
        # retaining readable fragments of the original name, number, or face.
        palettes={
            'mosaic-neutral':('#79838D','#9BA3AB','#C0C4C7','#8C969E','#ABB2B7'),
            'mosaic-warm':('#AC8D81','#D3B9A4','#E5D0BE','#B69D8E','#C9AE9C'),
            'mosaic-charcoal':('#303844','#434A54','#606977','#49515C','#353D49'),
        }
        colors=palettes[style_id]
        cell=max(5,min(15,round(min(x1-x0,y1-y0)/6)))
        for yy in range(oy0,oy1,cell):
            for xx in range(ox0,ox1,cell):
                idx=((xx//cell*29)^(yy//cell*53)^(xx//cell*yy//cell*7))%len(colors)
                d.rectangle((xx,yy,min(xx+cell,ox1),min(yy+cell,oy1)),fill=colors[idx])
        # Draw tiles over the entire (possibly clipped) core. Never sample the
        # underlying private pixels or soften the core with partial alpha.
        for yy in range(y0,y1,cell):
            for xx in range(x0,x1,cell):
                idx=((xx//cell*17)^(yy//cell*31)^(xx//cell*yy//cell*11))%len(colors)
                d.rectangle((xx,yy,min(xx+cell,x1),min(yy+cell,y1)),fill=colors[idx])
    elif style_id=='cloud':
        # Recompute from the sensitive region's width/height; keep a compact
        # fully opaque center and soften only the irregular exterior.
        alpha,halo=_cloud_alpha(x1-x0,y1-y0,pad)
        tint=Image.new('RGBA',alpha.size,fill)
        tint.putalpha(alpha)
        layer.alpha_composite(tint,(x0-halo,y0-halo))
    elif style_id=='brush-swipe':
        span=ox1-ox0; top=[]; bottom=[]
        for n in range(13):
            xx=ox0+n*span/12
            top.append((xx,max(0,oy0+(n*7%5-2)*pad*.22)))
            bottom.append((xx,min(canvas.height,oy1+(n*11%5-2)*pad*.23)))
        d.polygon(top+bottom[::-1],fill=fill)
        d.rectangle(core,fill=fill)
        for i in range(4):
            yy=oy0+((i*7)%5)*pad*.34
            d.line((ox0+span*.09+pad*i,yy,ox0+span*(.3+.12*i),yy-pad*.1),fill='#FFF8EB',width=max(1,pad//7))
        for n in range(3):
            yy=oy1-pad*.14+(n-1)*max(2,pad//5)
            d.line((ox0+span*.2,yy,ox1-span*.08-n*pad,yy-pad*.2),fill=fill,width=max(1,pad//6))
    elif style_id=='pixel-confetti':
        cell=max(5,min(19,round(min(x1-x0,y1-y0)/5)))
        colors=('#27344A','#425974','#718096','#D6DEE2','#EFCA79')
        left=(x0//cell-1)*cell;top=(y0//cell-1)*cell
        for yy in range(top,y1+cell*2,cell):
            for xx in range(left,x1+cell*2,cell):
                inside=xx<x1 and xx+cell>x0 and yy<y1 and yy+cell>y0
                if inside or (xx+cell>=x0-cell and xx<=x1+cell and yy+cell>=y0-cell and yy<=y1+cell and (xx//cell*13+yy//cell*7)%4==0):
                    idx=(xx//cell*17+yy//cell*11)%len(colors)
                    d.rectangle((xx,yy,xx+cell+1,yy+cell+1),fill=colors[idx])
        # Draw the actual sensitive core last: decorative pixels are never the privacy proof.
        # Use a dense coloured cell grid inside instead of a semi-transparent source mosaic.
        for yy in range((y0//cell)*cell,y1,cell):
            for xx in range((x0//cell)*cell,x1,cell):
                a=max(xx,x0);b=max(yy,y0);c=min(xx+cell,x1);e=min(yy+cell,y1)
                if a<c and b<e:
                    d.rectangle((a,b,c,e),fill=colors[(xx//cell*17+yy//cell*11)%len(colors)])
    elif style_id in ('mascot-cloud','flower-doodle'):
        cx=(x0+x1)/2;cy=(y0+y1)/2
        rx=(x1-x0)/2+pad*1.25;ry=(y1-y0)/2+pad*1.25
        if style_id=='flower-doodle':
            for n in range(8):
                theta=2*math.pi*n/8
                px=cx+math.cos(theta)*rx*.95;py=cy+math.sin(theta)*ry*.95
                d.ellipse((px-rx*.56,py-ry*.56,px+rx*.56,py+ry*.56),fill='#F6D181',outline='#B67054',width=max(2,pad//9))
            # Superellipse contains the entire rectangular privacy core without visible square corners.
            pts=[]
            for k in range(96):
                theta=2*math.pi*k/96;co=math.cos(theta);si=math.sin(theta)
                pts.append((cx+rx*.96*math.copysign(abs(co)**.5,co),cy+ry*.96*math.copysign(abs(si)**.5,si)))
            d.polygon(pts,fill=fill)
        else:
            d.ellipse((cx-rx,cy-ry,cx+rx,cy+ry),fill=fill)
            for px,py,r in ((cx-rx*.66,cy-ry*.58,.46),(cx+rx*.45,cy-ry*.63,.4),(cx-rx*.55,cy+ry*.55,.42),(cx+rx*.58,cy+ry*.48,.43)):
                d.ellipse((px-rx*r,py-ry*r,px+rx*r,py+ry*r),fill=fill)
        # Rectangular safety core lies inside the illustrated face, even for unusual aspect ratios.
        d.rectangle(core,fill=fill)
        eye=max(2,round(min(rx,ry)*.10))
        for ex in (cx-rx*.28,cx+rx*.28):
            d.ellipse((ex-eye,cy-eye*.9,ex+eye,cy+eye*1.1),fill='#403641')
        d.arc((cx-rx*.22,cy+ry*.02,cx+rx*.22,cy+ry*.52),start=10,end=170,fill='#403641',width=max(2,eye//2))
        if style_id=='mascot-cloud':
            for ex in (cx-rx*.55,cx+rx*.55):
                d.ellipse((ex-eye*.9,cy+eye*.6,ex+eye*.9,cy+eye*2),fill='#E9A7A0')
    else:raise ValueError('Unknown privacy sticker: '+style_id)
    return layer


def paint(canvas,compiled,t,fps):
    frame=round(t*fps); result=canvas.convert('RGBA')
    for ev in compiled['events']:
        if not ev['start_frame']<=frame<ev['end_frame']:continue
        core=box_at(ev,frame); w,h=result.size; x,y,bw,bh=core
        x0=max(0,math.floor(x*w));y0=max(0,math.floor(y*h));x1=min(w,math.ceil((x+bw)*w));y1=min(h,math.ceil((y+bh)*h))
        style=STYLES[ev['style_id']]; pad=max(3,round(style['pad']*w))
        outer=(max(0,x0-pad),max(0,y0-pad),min(w,x1+pad),min(h,y1+pad))
        result.alpha_composite(_sticker(result,ev['style_id'],(x0,y0,x1,y1),outer,pad))
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
