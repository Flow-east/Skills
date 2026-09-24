"""B3a: serif red, brush luxury white, mixed-size cyan bilingual layouts.
Licensed substitute fonts; observed designs, original bounded motion curves.
"""
import math
from PIL import Image, ImageDraw
from scene_bilingual import KINDS, wrap_text


def validate(p):
    from template_scenes import interval, texts
    k=p.variant['scene_system']['kind']
    if p.p.get('scene_notes') or p.p.get('scene_title_surface'):
        raise ValueError('B3 does not reuse B2 notes/title surfaces')
    for g in p.p['scene_captions']:
        for e in g['phrases']:
            if e.get('mode','normal')!='normal' or e.get('color','normal')!='normal':
                raise ValueError('B3 uses authored runs, not B2 modes or arbitrary colors')
            if any('fill' in r for r in e.get('runs',[])):
                raise ValueError('B3 color is template-bound; use body/keyword roles')
    if p.p.get('scene_tags') and k!='bired':
        raise ValueError('Only red bilingual uses independent corner labels')
    previous=0
    for e in p.p.get('scene_highlights',[]):
        a,b=interval(e,p.p['duration'])
        if k!='biluxe' or a<previous:
            raise ValueError('Nonoverlapping brush highlights belong only to luxury white')
        previous=b
        if not isinstance(e.get('text'),str) or not 1<=len(e['text'])<=8 or not str(e.get('reason','')).strip():
            raise ValueError('Highlight needs short semantic text and reason')
        anchors=[q for g in p.p['scene_captions'] for q in g['phrases'] if q.get('id')==e.get('phrase_id')]
        if len(anchors)!=1 or not anchors[0]['start']<=a<b<=anchors[0]['end']:
            raise ValueError('Highlight must anchor inside its Chinese phrase')
        # A summary can omit punctuation, not invent a new claim.
        if e['text'] not in texts(anchors[0]):
            raise ValueError('Highlight must quote its anchored phrase')


def line(p,runs,size,role='body',style='normal',maxw=None):
    """Baseline-aligned mixed sizes; full ink/shadow bounds, explicit font roles."""
    c=p.variant['scene_system'];k=c['kind'];u=p.unit
    pad=math.ceil(12*u);maxw=maxw or p.w*.87
    for factor in (1,.96,.92,.88,.84,.8,.76,.72):
        glyphs=[];width=0
        for r in runs:
            rr=r.get('role',role);rs=size
            if role=='body' and rr=='keyword':rs=c['keyword_size']
            font=p.font(rs*factor,rr)
            glyphs.append((width,r['text'],font,rr));width+=font.getlength(r['text'])
        if width+2*pad<=maxw:break
    else:raise ValueError('B3 phrase too long: split semantically, not below 72%')
    boxes=[f.getbbox(t,anchor='ls') for _,t,f,_ in glyphs]
    ascent=max(-b[1] for b in boxes);descent=max(b[3] for b in boxes)
    im=Image.new('RGBA',(math.ceil(width)+2*pad,ascent+descent+2*pad));d=ImageDraw.Draw(im)
    for x,text,font,rr in glyphs:
        def ink(dx,dy,fill,stroke=0,edge=None):
            d.text((pad+x+dx*u,pad+ascent+dy*u),text,font=font,anchor='ls',fill=fill,
                   stroke_width=max(0,round(stroke*u)),stroke_fill=edge or fill)
        if role=='translation':
            ink(1,2,'#171717',1.2);ink(0,0,'#F6F5F1')
        elif k=='bired':
            if style=='headline':
                ink(2,3,'#3A1818',4);ink(0,0,'#FFFDF7',2.4,'#882B2A')
            elif style=='subhead' or rr in ('keyword','sticker'):
                ink(2,3,'#301B1B',3);ink(0,0,'#983633',1.9,'#FFF9EE')
            else:ink(2,3,'#171414',2.2);ink(0,0,'#FFFFFF')
        elif k=='biluxe':
            if style=='headline' or style=='display':
                ink(2,3,'#55585A',1.8);ink(0,0,'#E9EBEA',.5,'#FFFFFF')
            else:
                fill='#F4EE99' if style=='subhead' or rr=='keyword' else '#FFFFFF'
                ink(1.5,2,'#3C3B32',1.5);ink(0,0,fill)
        else:
            fill='#8BF2E7' if rr in ('keyword','title','sticker') else '#F0F0EB'
            ink(2,3,'#202526',2.5 if rr in ('keyword','title') else 1.2);ink(0,0,fill)
    if k=='bired' and style=='headline':
        # Original oblique simulation, not the reference's identified font.
        shear=.12;extra=math.ceil(im.height*shear)
        im=im.transform((im.width+extra,im.height),Image.Transform.AFFINE,(1,shear,-extra,0,1,0),Image.Resampling.BICUBIC)
        if im.width>maxw:raise ValueError('Oblique title exceeds safe width; shorten title')
    return im


def translation(p,e,maxw):
    c=p.variant['scene_system'];pad=math.ceil(12*p.unit)
    rows,size=wrap_text(p,e['text'],c['translation_size'],maxw-2*pad)
    ims=[line(p,[{'text':row}],size,'translation',maxw=maxw) for row in rows]
    gap=round(-12*p.unit);w=max(x.width for x in ims);h=sum(x.height for x in ims)+gap*(len(ims)-1)
    out=Image.new('RGBA',(w,h));y=0
    for im in ims:
        out.alpha_composite(im,(0,y));y+=im.height+gap
    return out


def title(p):
    c=p.variant['scene_system'];k=c['kind'];rows=p.p.get('scene_title_lines',[])
    if not rows:return None
    ims=[]
    for j,text in enumerate(rows):
        role='title' if j==0 else 'body' if k!='bired' else 'keyword'
        size=c['title_size'] if j==0 else c['subtitle_size']
        ims.append(line(p,[dict(text=text,role=role)],size,role,'headline' if j==0 else 'subhead',p.w*.87))
    gap=round(-13*p.unit);w=max(i.width for i in ims);h=sum(i.height for i in ims)+gap*(len(ims)-1)
    if k=='biblue':
        out=Image.new('RGBA',(round(p.w*.95),h),(235,240,239,75));left=round(10*p.unit)
    else:out=Image.new('RGBA',(w,h));left=None
    y=0
    for im in ims:
        out.alpha_composite(im,(left if left is not None else (w-im.width)//2,y));y+=im.height+gap
    return out


def layout(p):
    from template_scenes import _box, texts
    c=p.variant['scene_system'];k=c['kind'];u=p.unit;entries=[]
    def add(im,x,y,a,b,role,animation='fade'):
        x=round(x);y=round(y);env=round(10*u) if animation in ('soft','label') else 0
        entries.append(dict(image=im,x=x,y=y,start=a,end=b,role=role,animation=animation,box=_box(im,x,y,env)))
    ti=title(p)
    if ti:
        add(ti,(p.w-ti.width)/2,p.h*c['title_y']-ti.height/2,0,min(p.p['duration'],p.p.get('title_duration',c['title_duration'])),'title')
    translations={e['phrase_id']:e for e in p.p['scene_translations']}
    for g in p.p['scene_captions']:
        blocks=[]
        for j,e in enumerate(g['phrases']):
            runs=e.get('runs') or [dict(text=texts(e),role='keyword' if k=='biluxe' and j==0 else 'body')]
            zh=line(p,runs,c['body_size']);en=translation(p,translations[e['id']],p.w*.83)
            blocks.append((e,zh,en))
        inner=-round(10*u);gap=round(7*u)
        total=sum(zh.height+en.height+inner for _,zh,en in blocks)+gap*(len(blocks)-1)
        y=p.h*c['caption_y']-total/2
        for j,(e,zh,en) in enumerate(blocks):
            w=max(zh.width,en.width)
            if len(blocks)>1 and k in ('bired','biluxe'):
                x=p.w*.075 if j==0 else p.w*.925-w
            else:x=(p.w-w)/2
            # Base positions don't jump when a delayed translation appears.
            add(zh,x if k!='biblue' else (p.w-zh.width)/2,y,e['start'],e['end'],'caption','soft' if k=='biluxe' else 'fade')
            te=translations[e['id']]
            add(en,x if k!='biblue' else (p.w-en.width)/2,y+zh.height+inner,te['start'],te['end'],'translation')
            y+=zh.height+en.height+inner+gap
    for e in p.p.get('scene_tags',[]):
        im=line(p,[dict(text=e['text'],role='sticker')],c['tag_size'],'sticker',maxw=p.w*.38)
        x=p.w*.94-im.width if e.get('side','right')=='right' else p.w*.06
        add(im,x,p.h*c['tag_y']-im.height/2,e['start'],e['end'],'tag','label')
    for e in p.p.get('scene_highlights',[]):
        im=line(p,[dict(text=e['text'],role='title')],c['display_size'],'title','display',p.w*.88)
        # Bounded original star glints; no external particles or copyrighted sprite.
        d=ImageDraw.Draw(im);w,h=im.size
        for x,y,r in [(9*u,12*u,5*u),(w-10*u,h*.28,6*u),(w*.65,7*u,3*u)]:
            d.line((x-r,y,x+r,y),fill='#FFFFFF',width=max(1,round(u)))
            d.line((x,y-r,x,y+r),fill='#FFFFFF',width=max(1,round(u)))
        add(im,(p.w-w)/2,p.h*c['title_y']-h/2,e['start'],e['end'],'highlight','pop')
    return entries
