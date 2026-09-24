"""Four reference-led B5c designs; licensed fonts and original geometry only."""
import math,random,hashlib
from PIL import Image,ImageDraw
from template_scenes_b3b import stack
KINDS={'ins','nostalgia','transyellow','tornedge'}
MODES={'ins':{'normal'},'nostalgia':{'normal','brush'},'transyellow':{'normal','display'},'tornedge':{'normal','compact'}}

def validate(p):
    from template_scenes import texts,interval
    k=p.variant['scene_system']['kind'];ids={}
    if any(p.p.get(v) for v in ('scene_notes','scene_highlights','scene_title_surface','scene_identity','scene_accents','scene_media','scene_callouts')):raise ValueError('Unsupported B5c auxiliary layer')
    for g in p.p['scene_captions']:
        for e in g['phrases']:
            ident=e.get('id')
            if not isinstance(ident,str) or not ident or ident in ids:raise ValueError('B5c needs unique phrase ids')
            ids[ident]=e
            if e.get('mode','normal') not in MODES[k]:raise ValueError('Unsupported B5c phrase mode')
            if any(e.get(v) for v in ('pointer','underline','reveal','reveal_times')) or e.get('color','normal')!='normal' or any('fill' in r for r in e.get('runs',[])):raise ValueError('B5c decoration is contract bound; word reveal not implemented')
    for e in p.p.get('scene_tags',[]):
        a,b=interval(e,p.p['duration']);q=ids.get(e.get('phrase_id'))
        if not q or not q['start']<=a<b<=q['end'] or e['text'] not in texts(q):raise ValueError('B5c tag must quote an active phrase')
        if e.get('orientation','horizontal')!='horizontal' or e.get('icon') or e.get('side','right') not in ('left','right'):raise ValueError('B5c tags use horizontal template geometry')
    for e in p.p.get('scene_canvas',[]):
        if e['kind']=='circle' and not str(e.get('composition_review','')).strip():raise ValueError('Circle needs actual composition review; never a privacy shortcut')

def line(p,runs,size,role='body',mode='normal',maxw=None):
    k=p.variant['scene_system']['kind'];u=p.unit;maxw=maxw or p.w*.86;pad=math.ceil(9*u)
    shear=.12 if k=='transyellow' and mode=='display' else .045 if k=='nostalgia' and mode=='brush' else 0
    original=size
    for attempt in range(5):
        glyphs=[];x=0
        for r in runs:
            rr=r.get('role',role);fr='keyword' if k=='nostalgia' and mode=='brush' else rr
            mult=1.18 if k=='tornedge' and rr=='keyword' and role=='body' and mode=='normal' else 1
            f=p.font(size*mult,fr);t=r['text'];bb=f.getbbox(t,anchor='ls');glyphs.append((x,t,f,rr,bb));x+=f.getlength(t)
        left=min(x+b[0] for x,t,f,r,b in glyphs);right=max(x+b[2] for x,t,f,r,b in glyphs);top=min(b[1] for x,t,f,r,b in glyphs);bottom=max(b[3] for x,t,f,r,b in glyphs)
        h=bottom-top+2*pad;w=math.ceil(right-left)+2*pad
        if w+math.ceil(h*shear)<=maxw:break
        size*=min(.97,(maxw-2*pad-math.ceil(h*shear))/max(1,right-left))
        if size<original*.72:raise ValueError('B5c text too long; split phrases, do not shrink to tiny text')
    else:raise ValueError('B5c line cannot fit safe width')
    im=Image.new('RGBA',(w,h));d=ImageDraw.Draw(im)
    for x,t,f,rr,b in glyphs:
        fill='#FFF8E2';edge='#302A24'
        if k=='ins':fill='#FFF9E8' if role!='sticker' else '#674A40'
        elif k=='nostalgia':fill='#F4E4B7'
        elif k=='transyellow':fill='#F4E65B' if role=='title' or rr=='keyword' and mode=='normal' else '#EBA059' if rr=='keyword' or role=='sticker' else '#FFFFFF'
        elif k=='tornedge':fill='#EBDD78' if rr=='keyword' else '#FFFDE5'
        pos=(pad+x-left,pad-top)
        d.text((pos[0]+1.2*u,pos[1]+1.8*u),t,font=f,anchor='ls',fill=edge,stroke_width=max(1,round(.7*u)),stroke_fill=edge)
        d.text(pos,t,font=f,anchor='ls',fill=fill)
    if shear:
        extra=math.ceil(h*shear);im=im.transform((w+extra,h),Image.Transform.AFFINE,(1,shear,-extra,0,1,0),Image.Resampling.BICUBIC)
    return im

def panel(im,u,kind):
    out=Image.new('RGBA',im.size);d=ImageDraw.Draw(out);w,h=im.size
    if kind=='ins':
        # Original stepped tape edges and small blue offsets seen in reference.
        q=max(1,round(3*u));d.rectangle((w*.42,0,w*.65,h-1),fill='#BDD9EA')
        d.polygon([(0,q),(w*.16,q),(w*.16,0),(w*.34,q),(w*.58,q),(w*.58,2*q),(w*.78,2*q),(w*.78,q),(w-1,q),(w-1,h-q-1),(w*.84,h-q-1),(w*.84,h-1),(w*.61,h-1),(w*.61,h-q-1),(w*.24,h-q-1),(w*.24,h-1),(0,h-1)],fill=(100,66,54,245))
    elif kind=='nostalgia':d.rounded_rectangle((0,0,w-1,h-1),radius=round(5*u),fill=(71,53,41,155))
    elif kind=='transyellow':d.rounded_rectangle((0,0,w-1,h-1),radius=round(2*u),fill=(33,32,28,140))
    else:
        # Deterministic original paper edge, independent of scene timing.
        rng=random.Random(52);step=max(3,round(8*u));j=max(1,round(2*u));points=[(0,j)]
        points += [(x,rng.randint(0,j)) for x in range(0,w,step)]+[(w-1,j),(w-1,h-1-j)]
        points += [(x,h-1-rng.randint(0,j)) for x in reversed(range(0,w,step))]+[(0,h-1-j)]
        d.polygon(points,fill=(55,54,43,150))
    out.alpha_composite(im);return out

def title(p):
    c=p.variant['scene_system'];k=c['kind'];u=p.unit;ims=[]
    for i,t in enumerate(p.p.get('scene_title_lines',[])):
        if k=='ins':
            chars=[]
            for j,ch in enumerate(t):
                im=line(p,[dict(text=ch,role='title')],c['title_size'] if i==0 else c['subtitle_size'],'title')
                if j==max(1,len(t)//3):
                    im=panel(im,u,'ins');im=im.rotate(-8,resample=Image.Resampling.BICUBIC,expand=True)
                    d=ImageDraw.Draw(im);d.line((4*u,5*u,im.width-5*u,9*u),fill='#B28D7D',width=max(1,round(u)))
                chars.append(im)
            # Small tight inter-character packing preserves title width; painted bounds remain explicit.
            overlap=round(11*u);w=sum(v.width for v in chars)-overlap*(len(chars)-1);h=max(v.height for v in chars)+round(4*u)
            if w>p.w*.86:raise ValueError('Ins collage title too long; split title lines')
            im=Image.new('RGBA',(w,h));x=0
            for j,v in enumerate(chars):im.alpha_composite(v,(x,round((h-v.height)/2)));x+=v.width-overlap
        else:im=line(p,[dict(text=t,role='title')],c['title_size'] if i==0 else c['subtitle_size'],'title',maxw=p.w*.84)
        ims.append(im)
    return stack(ims,round(u)) if ims else None

def label(p,text,size,maxw):
    k=p.variant['scene_system']['kind'];u=p.unit;im=line(p,[dict(text=text,role='sticker')],size,'sticker',maxw=maxw-12*u)
    if k=='ins':
        q=round(6*u);out=Image.new('RGBA',(im.width+2*q,im.height+2*q));d=ImageDraw.Draw(out)
        d.rectangle((q+2,q+2,out.width-1,out.height-1),fill='#8D9FB4');d.rectangle((0,0,out.width-q,out.height-q),fill='#FFF7E4');out.alpha_composite(im,(q,q))
        x=5*u;y=5*u
        for angle in (0,60,120):
            a=math.radians(angle);dx=4*u*math.cos(a);dy=4*u*math.sin(a);d.line((x-dx,y-dy,x+dx,y+dy),fill='#839BB9',width=max(1,round(1.2*u)))
        return out
    if k in ('nostalgia','tornedge'):return panel(im,u,k)
    return im

def layout(p):
    from template_scenes import texts,_box
    c=p.variant['scene_system'];k=c['kind'];u=p.unit;entries=[]
    def add(im,x,y,a,b,role,anim='fade'):
        x=round(x);y=round(y);env=round(10*u) if anim in ('soft','label') else 0;entries.append(dict(image=im,x=x,y=y,start=a,end=b,role=role,animation=anim,box=_box(im,x,y,env)))
    ti=title(p)
    if ti:add(ti,(p.w-ti.width)/2,p.h*c['title_y']-ti.height/2,0,min(p.p['duration'],p.p.get('title_duration',c['title_duration'])),'title')
    for g in p.p['scene_captions']:
        blocks=[]
        for e in g['phrases']:
            mode=e.get('mode','normal');size=c['display_size'] if mode in ('display','brush') else c['compact_size'] if mode=='compact' else c['body_size']
            im=line(p,e.get('runs') or [dict(text=texts(e),role='body')],size,'body',mode,p.w*.84)
            if k in ('ins','nostalgia','transyellow') and mode=='normal' or k=='tornedge' and mode=='compact':im=panel(im,u,k)
            blocks.append((e,im))
        gap=round(3*u);total=sum(im.height for e,im in blocks)+gap*(len(blocks)-1);y=p.h*c['caption_y']-total/2
        for i,(e,im) in enumerate(blocks):
            x=(p.w-im.width)/2
            if len(blocks)==2 and k in ('transyellow','tornedge'):x=p.w*.08 if i==0 else p.w*.92-im.width
            add(im,x,y,e['start'],e['end'],'caption','soft' if k=='transyellow' and e.get('mode')=='display' else 'fade');y+=im.height+gap
    for e in p.p.get('scene_tags',[]):
        im=label(p,e['text'],c['tag_size'],p.w*.32);x=p.w*.94-im.width if e.get('side','right')=='right' else p.w*.06
        add(im,x,p.h*c['tag_y']-im.height/2,e['start'],e['end'],'tag','label')
    return entries
