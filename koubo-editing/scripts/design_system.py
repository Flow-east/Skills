"""Template-owned composition; content/timestamps remain authored by the edit plan.
All animation happens on bounded sprites, not a scaled full-screen text canvas.
No face detector is implied: protected_regions are authored output-clock rectangles.
"""
import math
from PIL import Image, ImageDraw


def rules(painter):
    return painter.variant.get('design_system', {})


def ease(x):
    x = max(0., min(1., x))
    return 1 - (1-x)**3


def animated(sprite, age, remaining, cfg, unit):
    duration = max(.001, cfg.get('in_ms', 240)/1000)
    q = max(0., min(1., age/duration)); e = ease(q)
    opacity = min(ease(age/min(.15, duration)), ease(remaining/max(.001,cfg.get('out_ms',140)/1000)))
    kind = cfg.get('enter', 'fade'); scale = 1.; dx = dy = 0
    if kind == 'punch': scale = .78 + .22*e
    elif kind == 'bounce': scale = 1 + 2.70158*(q-1)**3 + 1.70158*(q-1)**2
    elif kind == 'rise': dy = round(16*unit*(1-e))
    elif kind == 'slide': dx = round(-22*unit*(1-e))
    layer = sprite.copy()
    if kind == 'wipe':
        mask = Image.new('L', layer.size); ImageDraw.Draw(mask).rectangle((0,0,round(layer.width*e),layer.height),fill=255)
        from PIL import ImageChops
        layer.putalpha(ImageChops.multiply(layer.getchannel('A'),mask))
    if scale != 1:
        layer = layer.resize((max(1,round(layer.width*scale)),max(1,round(layer.height*scale))),Image.Resampling.LANCZOS)
    layer.putalpha(layer.getchannel('A').point(lambda a: round(a*opacity)))
    return layer, dx, dy


def position(painter, sprite, anchor, align='center', offset=(0,0)):
    margin = max(12,round(22*painter.unit))
    if sprite.width > painter.w-2*margin or sprite.height > painter.h-2*margin:
        raise ValueError('Template sprite exceeds safe area')
    x = painter.w*anchor[0] - (sprite.width/2 if align=='center' else 0) + offset[0]
    y = painter.h*anchor[1] - sprite.height/2 + offset[1]
    return round(max(margin,min(painter.w-margin-sprite.width,x))),round(max(margin,min(painter.h-margin-sprite.height,y)))


def overlaps(a,b):
    return min(a[2],b[2])>max(a[0],b[0]) and min(a[3],b[3])>max(a[1],b[1])


def protected_boxes(painter,t):
    result=list(getattr(painter,'design_boxes',[]))
    for region in painter.p.get('protected_regions',[]):
        if region.get('start',0)<=t<region.get('end',painter.p['duration']):
            x1,y1,x2,y2=region['box']; result.append((x1*painter.w,y1*painter.h,x2*painter.w,y2*painter.h))
    return result


def interval_regions(painter,start,end):
    return [(r['box'][0]*painter.w,r['box'][1]*painter.h,r['box'][2]*painter.w,r['box'][3]*painter.h)
            for r in painter.p.get('protected_regions',[])
            if r.get('start',0)<end and r.get('end',painter.p['duration'])>start]


def envelope(painter,sprite,cfg):
    kind=cfg.get('enter');factor=1.101 if kind=='bounce' else 1
    dx=22*painter.unit if kind=='slide' else 0;dy=16*painter.unit if kind=='rise' else 0
    return Image.new('RGBA',(math.ceil(sprite.width*factor+2*dx),math.ceil(sprite.height*factor+2*dy)))


def title_layout(painter):
    key=('design_title_layout',)
    if key in painter.layers:return painter.layers[key]
    cfg=rules(painter)['title'];sprite=title_sprite(painter);area=envelope(painter,sprite,cfg)
    align='center' if cfg['kind'] in ('headline','pill','pink_headline','gold_headline') else 'left'
    x,y=position(painter,area,cfg['anchor'],align);box=(x,y,x+area.width,y+area.height)
    duration=painter.p.get('title_duration',cfg['duration'])
    if any(overlaps(box,b) for b in interval_regions(painter,0,duration)):raise ValueError('Title overlaps protected region; revise title anchor')
    result=(sprite,area,box);painter.layers[key]=result;return result


def caption_layout(painter,ev):
    import json
    key=('design_caption_layout',json.dumps(ev,sort_keys=True,ensure_ascii=False))
    if key in painter.layers:return painter.layers[key]
    sprite,cfg=caption_sprite(painter,ev);animation=dict(cfg)
    animation.update({k:ev[k] for k in ('enter','in_ms','out_ms') if k in ev})
    area=envelope(painter,sprite,animation);anchor=cfg['anchor']
    if ev.get('position') is not None:
        x,y=painter._event_pos(ev,painter._active_clip);anchor=[x/painter.w,y/painter.h]
    anchors=[anchor]+([] if ev.get('position') is not None and not ev.get('template_position') else cfg.get('fallback_anchors',[]))
    occupied=interval_regions(painter,ev['start'],ev['end'])
    if painter.p.get('title') and ev['start']<painter.p.get('title_duration',rules(painter)['title']['duration']):occupied.append(title_layout(painter)[2])
    for candidate in anchors:
        x,y=position(painter,area,candidate,cfg['align']);box=(x,y,x+area.width,y+area.height)
        if not any(overlaps(box,b) for b in occupied):break
    else:raise ValueError('Caption overlaps protected region/title; revise template layout')
    result=(sprite,area,box,animation);painter.layers[key]=result;return result


def sticker_layout(painter,ev):
    import json
    from keyword_stickers import badge
    key=('design_sticker_layout',json.dumps(ev,sort_keys=True,ensure_ascii=False))
    if key in painter.layers:return painter.layers[key]
    cfg=rules(painter)['sticker'];sprite=badge(painter,ev);area=envelope(painter,sprite,cfg)
    anchors=[ev['position']] if 'position' in ev else cfg['anchors'];occupied=interval_regions(painter,ev['start'],ev['end'])
    if painter.p.get('title') and ev['start']<painter.p.get('title_duration',rules(painter)['title']['duration']):occupied.append(title_layout(painter)[2])
    for c in painter.p['clips']:
        if c['output_start']>=ev['end'] or c['output_end']<=ev['start']:continue
        events=c.get('caption_events') or painter.p.get('caption_events') or painter._auto_events(c)
        for e in events:
            if e['start']<ev['end'] and e['end']>ev['start']:occupied.append(caption_layout(painter,e)[2])
    for anchor in anchors:
        x,y=position(painter,area,anchor);box=(x,y,x+area.width,y+area.height)
        padded=(box[0]-6*painter.unit,box[1]-6*painter.unit,box[2]+6*painter.unit,box[3]+6*painter.unit)
        if not any(overlaps(padded,b) for b in occupied):break
    else:raise ValueError('No safe template sticker anchor; author another position/protected region')
    result=(sprite,area,box,cfg);painter.layers[key]=result;return result


def sticker_position(painter,ev,sprite,t):
    _,area,box,_=sticker_layout(painter,ev)
    return round(box[0]+(area.width-sprite.width)/2),round(box[1]+(area.height-sprite.height)/2)


def composite_slot(painter,canvas,sprite,area,box,age,remaining,cfg):
    layer,dx,dy=animated(sprite,age,remaining,cfg,painter.unit)
    x=round(box[0]+(area.width-layer.width)/2+dx);y=round(box[1]+(area.height-layer.height)/2+dy)
    canvas.alpha_composite(layer,(x,y))


def paint_sticker(painter,canvas,ev,t):
    sprite,area,box,cfg=sticker_layout(painter,ev)
    composite_slot(painter,canvas,sprite,area,box,t-ev['start'],ev['end']-t,cfg)


def _measure(painter,runs,cfg,maxw):
    """Wrap on styled phrase boundaries, split overlong body runs only when necessary.
    A keyword stays atomic. Shrink all roles together until at most two lines fit.
    """
    for factor in (1,.94,.88,.82,.76,.70,.64,.58,.52):
        chunks=[]
        for r in runs:
            keyword=r.get('style') in ('keyword','accent')
            size=r.get('size',cfg['keyword_size'] if keyword else cfg['size'])*factor
            f=painter.font(size,'keyword' if keyword else 'body'); text=r.get('text','')
            if not keyword and f.getlength(text)>maxw:
                part=''
                for ch in text:
                    if part and f.getlength(part+ch)>maxw: chunks.append((dict(r,text=part),f));part=''
                    part+=ch
                if part:chunks.append((dict(r,text=part),f))
            else: chunks.append((r,f))
        lines=[]; line=[]; width=0
        for r,f in chunks:
            rw=f.getlength(r['text'])
            if line and width+rw>maxw:lines.append(line);line=[];width=0
            line.append((r,f));width+=rw
        if line:lines.append(line)
        if len(lines)<=2 and all(sum(f.getlength(r['text']) for r,f in line)<=maxw for line in lines):return lines
    raise ValueError('Caption too long for template; author a semantic break instead of clipping text')


def caption_sprite(painter,ev):
    cfg=dict(rules(painter)['caption']);cfg.update({k:ev[k] for k in ('kind','align','max_width','line_gap') if k in ev})
    if cfg['kind'] in ('pink_stack','gold_outline'):
        from reference_typography import caption_sprite as reference_caption
        return reference_caption(painter,ev,cfg)
    runs=ev.get('runs') or [dict(text=ev.get('text',''),style=ev.get('style','base'))]
    u=painter.unit;pad=round(22*u);maxw=painter.w*cfg['max_width']-pad*2
    lines=_measure(painter,runs,cfg,maxw)
    if not lines:raise ValueError('Empty design caption')
    widths=[sum(f.getlength(r['text']) for r,f in ln) for ln in lines]
    heights=[max(f.size for r,f in ln)*cfg['line_gap'] for ln in lines]
    kind=cfg['kind'];extra=round(18*u) if kind in ('note','editorial','dialogue') else 0
    w=math.ceil(max(widths))+2*pad;h=math.ceil(sum(heights))+2*pad+extra
    im=Image.new('RGBA',(w,h));d=ImageDraw.Draw(im);accent=painter.theme['accent']
    if kind=='dialogue':
        d.rounded_rectangle((3*u,3*u,w-4*u,h-14*u),radius=22*u,fill='#FFF7E5',outline='#FFFFFF',width=max(1,round(4*u)))
        d.polygon([(w*.72,h-19*u),(w*.82,h-19*u),(w*.79,h-1*u)],fill='#FFF7E5')
    elif kind=='editorial':
        d.rounded_rectangle((0,0,w-1,h-1),radius=5*u,fill=(20,26,23,218))
        d.line((pad,pad*.65,w-pad,pad*.65),fill=accent,width=max(1,round(2*u)))
    y=pad+extra*.35
    for ln,lw,lh in zip(lines,widths,heights):
        x=pad if cfg['align']=='left' else (w-lw)/2;cy=y+lh/2
        for r,f in ln:
            text=r['text'];kw=r.get('style') in ('keyword','accent');tw=f.getlength(text)
            fill=r.get('fill',accent if kw else painter.theme['text']);sw=0
            if kind=='impact':
                sw=round((6 if kw else 4)*u)
                d.text((x+3*u,cy+4*u),text,font=f,anchor='lm',fill='#14131B',stroke_width=sw+1,stroke_fill='#14131B')
            elif kind=='dialogue' and kw:
                d.rounded_rectangle((x-4*u,cy-f.size*.52,x+tw+4*u,cy+f.size*.62),radius=8*u,fill='#F9CED7')
                fill='#942C52'
            elif kind=='note':sw=max(1,round(2*u))
            if kind=='editorial' and kw:fill=accent
            d.text((x,cy),text,font=f,anchor='lm',fill=fill,stroke_width=sw,stroke_fill=painter.theme['stroke'])
            if kw and kind=='note':
                yy=cy+f.size*.64;d.line([(x,yy),(x+tw*.45,yy+2*u),(x+tw,yy-2*u)],fill=accent,width=max(1,round(3*u)))
            x+=tw
        y+=lh
    return im,cfg


def paint_caption(painter,canvas,ev,t):
    if not ev['start']<=t<ev['end']:return
    if ev.get('english'):raise ValueError('Design v2 has no bilingual layout; select a bilingual template')
    sprite,area,box,cfg=caption_layout(painter,ev)
    composite_slot(painter,canvas,sprite,area,box,t-ev['start'],ev['end']-t,cfg)
    painter.design_boxes=getattr(painter,'design_boxes',[])+[box]


def title_sprite(painter):
    cfg=rules(painter)['title'];u=painter.unit;pad=round(20*u)
    if cfg['kind'] in ('pink_headline','gold_headline'):
        from reference_typography import title_sprite as reference_title
        return reference_title(painter,cfg)
    # Reuse bounded line measurement with the title role by drawing independently.
    text=painter.p['title'];maxw=painter.w*cfg['max_width']-2*pad
    f=painter.font(cfg['size'],'title')
    if f.getlength(text)<=maxw:lines=[text]
    else:
        # Prefer authored/punctuation breaks over an orphan final word.
        candidates=[i+1 for i,ch in enumerate(text[:-1]) if ch in '，,：:；;']
        if not candidates:candidates=list(range(1,len(text)))
        split=min(candidates,key=lambda i:max(f.getlength(text[:i]),f.getlength(text[i:])))
        lines=[text[:split],text[split:]]
        f=painter.fit(max(lines,key=lambda x:f.getlength(x)),cfg['size'],maxw,'title')
    subtitle=painter.p.get('subtitle','');sf=painter.fit(subtitle,24,maxw,'body') if subtitle else None
    w=math.ceil(max([f.getlength(s) for s in lines]+([sf.getlength(subtitle)] if sf else [])))+2*pad
    h=math.ceil(len(lines)*f.size*1.25)+2*pad+(sf.size+12 if sf else 0)
    im=Image.new('RGBA',(w,h));d=ImageDraw.Draw(im);kind=cfg['kind'];accent=painter.theme['accent']
    if kind=='pill':d.rounded_rectangle((1,1,w-2,h-2),radius=26*u,fill='#FBE5B5',outline='#FFFFFF',width=max(1,round(4*u)))
    if kind=='editorial':d.line((pad, h-5*u,w-pad,h-5*u),fill=accent,width=max(1,round(2*u)))
    for i,text in enumerate(lines):
        x=w/2 if kind in ('headline','pill','pink_headline','gold_headline') else pad;y=pad+(i+.5)*f.size*1.25
        fill=accent if kind=='headline' else ('#244336' if kind=='pill' else '#FFF5DE');sw=round((5 if kind=='headline' else 2 if kind=='note' else 1)*u)
        d.text((x,y),text,font=f,anchor='mm' if kind in ('headline','pill','pink_headline','gold_headline') else 'lm',fill=fill,stroke_width=sw,stroke_fill='#1E211D' if kind!='pill' else '#FBE5B5')
    if kind=='note':d.line((pad,h-7*u,w-pad,h-10*u),fill=accent,width=max(1,round(3*u)))
    if sf:d.text((pad,h-pad-sf.size/2),subtitle,font=sf,anchor='lm',fill='#FFFFFF',stroke_width=1,stroke_fill='#1E211D')
    return im


def paint_title(painter,canvas,t):
    cfg=rules(painter)['title'];duration=painter.p.get('title_duration',cfg['duration'])
    if not painter.p.get('title') or not 0<=t<duration:return
    sprite,area,box=title_layout(painter)
    composite_slot(painter,canvas,sprite,area,box,t,duration-t,cfg)
    painter.design_boxes.append(box)


def validate(painter):
    cfg=rules(painter)
    if not cfg:return
    if any(c.get('card') for c in painter.p['clips']):raise ValueError('Design v2 does not use legacy generic cards; author captions/keyword stickers instead')
    if painter.p.get('eyebrow'):raise ValueError('Design v2 needs an authored eyebrow layout; use title/subtitle')
    if cfg.get('version')!=2:raise ValueError('Unknown template design version')
    supported={'impact','dialogue','note','editorial','pink_stack','gold_outline'}
    if cfg['caption']['kind'] not in supported:raise ValueError('Unknown caption design')
    for role in ('caption','title','sticker'):
        r=cfg[role]
        if r.get('enter') not in ('punch','bounce','rise','slide','wipe','fade'):raise ValueError('Unknown template animation')
        if not .15<=r['max_width']<=.92:raise ValueError('Invalid design width')
        if not 0<r.get('in_ms',200)<=2000 or not 0<r.get('out_ms',140)<=2000:raise ValueError('Invalid animation duration')
        anchors=r.get('anchors',[r.get('anchor')])
        if not anchors:raise ValueError('Template needs a layout anchor')
        for a in anchors:
            if not isinstance(a,list) or len(a)!=2 or not all(isinstance(v,(int,float)) and math.isfinite(v) and 0<=v<=1 for v in a):raise ValueError('Invalid design anchor')
    for r in painter.p.get('protected_regions',[]):
        box=r.get('box',[])
        if len(box)!=4 or not all(isinstance(x,(int,float)) and math.isfinite(x) and 0<=x<=1 for x in box) or not box[0]<box[2] or not box[1]<box[3]:raise ValueError('Invalid protected rectangle')
        a,b=r.get('start',0),r.get('end',painter.p['duration'])
        if not all(isinstance(x,(int,float)) and math.isfinite(x) for x in (a,b)) or not 0<=a<b<=painter.p['duration']:raise ValueError('Invalid protected-region output times')
    if painter.p.get('english_map'):raise ValueError('Design v2 needs an authored bilingual layout; choose a bilingual template')


def audit_layout(painter):
    """Resolve all events before encoding; this is geometric QA, not aesthetic approval."""
    if not rules(painter):return None
    report={'version':2,'template':painter.variant['id'],'time_space':'output','events':[],
            'face_protection':'authored regions' if painter.p.get('protected_regions') else 'not supplied; visual face review required',
            'scope':'bounded full-animation envelopes; no automatic semantic/aesthetic approval'}
    def record(role,start,end,result):
        box=result[2]
        report['events'].append(dict(role=role,start=start,end=end,box=list(box)))
    if painter.p.get('title'):
        record('title',0,min(painter.p['duration'],painter.p.get('title_duration',rules(painter)['title']['duration'])),title_layout(painter))
    for c in painter.p['clips']:
        painter._active_clip=c
        for ev in c.get('caption_events') or painter.p.get('caption_events') or painter._auto_events(c):
            if ev.get('english'):raise ValueError('Design v2 has no bilingual event layout')
            record('caption',ev['start'],ev['end'],caption_layout(painter,ev))
    for ev in painter.p.get('keyword_stickers',[]):record('sticker',ev['start'],ev['end'],sticker_layout(painter,ev))
    report['passed']=True
    return report
