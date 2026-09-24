"""B4c: reference-led elegant pink, promo, brown gold and comic hot pink.
Text/icon geometry is original. No automatic semantics, identity or segmentation.
"""
import math
from PIL import Image,ImageDraw,ImageChops
from template_scenes_b3b import stack
from scene_bilingual import wrap_text
KINDS={'elegantpink','promo','browngold','hotpink'}

def validate(p):
    from template_scenes import interval,texts,finite
    k=p.variant['scene_system']['kind'];phrases={};duration=p.p['duration']
    if any(p.p.get(key) for key in ('scene_notes','scene_highlights','scene_title_surface')):raise ValueError('B4c does not implement legacy auxiliary layers')
    for g in p.p['scene_captions']:
        for e in g['phrases']:
            ident=e.get('id')
            if not isinstance(ident,str) or not ident or ident in phrases:raise ValueError('B4c requires unique phrase ids')
            phrases[ident]=e;mode=e.get('mode','bilingual' if k=='elegantpink' else 'normal')
            modes={'bilingual','ribbon'} if k=='elegantpink' else {'normal','display','arc'} if k=='hotpink' else {'normal'}
            if mode not in modes:raise ValueError('Unsupported B4c phrase mode')
            if k=='elegantpink' and mode=='bilingual' and len(g['phrases'])!=1:raise ValueError('Elegant bilingual mode requires one phrase')
            if k=='elegantpink' and any(x.get('mode','bilingual')!=mode for x in g['phrases']):raise ValueError('Do not mix ribbon and bilingual group')
            if mode=='arc' and not 1<=len(texts(e))<=8:raise ValueError('Arc display limited to eight characters')
            if e.get('pointer') or e.get('color','normal')!='normal' or any('fill' in r for r in e.get('runs',[])):raise ValueError('B4c colors and pointer design are template-bound')
    for e in p.p.get('scene_tags',[]):
        a,b=interval(e,duration);q=phrases.get(e.get('phrase_id'))
        if not q or not q['start']<=a<b<=q['end'] or e['text'] not in texts(q):raise ValueError('B4c tag must quote active anchored phrase')
        if e.get('orientation','horizontal')!='horizontal':raise ValueError('B4c tags are horizontal')
        icons={'promo':{None,'megaphone','cart'},'elegantpink':{None,'heart_cursor'},'hotpink':{None,'heart'},'browngold':{None}}[k]
        if e.get('icon') not in icons:raise ValueError('Icon not part of selected template')
    callouts=p.p.get('scene_callouts',[])
    if not isinstance(callouts,list) or callouts and k!='elegantpink':raise ValueError('Retained scene list requires elegantpink')
    for e in callouts:
        a,b=interval(e,duration);q=phrases.get(e.get('phrase_id'));slot=e.get('slot')
        if not q or not q['start']<=a<q['end'] or not isinstance(e.get('text'),str) or not 1<=len(e['text'])<=6 or e['text'] not in texts(q):raise ValueError('List must quote phrase and enter during it')
        if any(v in e for v in ('x','y')) and any(not finite(e.get(v)) or not 0<=e[v]<=1 for v in ('x','y')):raise ValueError('List anchor requires normalized x and y together')
        if isinstance(slot,bool) or slot not in (0,1,2) or not str(e.get('reason','')).strip() or e.get('side','left') not in ('left','right'):raise ValueError('List requires slot/side/reason')
    for i,e in enumerate(callouts):
        for q in callouts[i+1:]:
            if e.get('side','left')==q.get('side','left') and e['slot']==q['slot'] and min(e['end'],q['end'])>max(e['start'],q['start']):raise ValueError('List slot collision')
    ids=p.p.get('scene_identity',[])
    if not isinstance(ids,list) or len(ids)>1 or ids and k!='browngold':raise ValueError('Only browngold supports a reviewed identity card')
    for e in ids:
        interval(e,duration)
        for field,limit in (('name',4),('detail',16)):
            if not isinstance(e.get(field),str) or not 1<=len(e[field])<=limit:raise ValueError('Identity text length invalid')
        rows=e.get('detail_lines')
        if rows is not None and (not isinstance(rows,list) or not 1<=len(rows)<=2 or any(not isinstance(x,str) or not x for x in rows) or ''.join(rows)!=e['detail']):raise ValueError('Identity detail_lines must faithfully partition detail into at most two rows')
        if e.get('review_status')!='reviewed' or any(not str(e.get(v,'')).strip() for v in ('source','reviewer','reason')):raise ValueError('Identity requires provenance and review')
        if any(not finite(e.get(v)) or not 0<=e[v]<=1 for v in ('x','y')):raise ValueError('Identity requires explicit anchor')
    accents=p.p.get('scene_accents',[])
    if not isinstance(accents,list) or accents and k!='hotpink':raise ValueError('Comic accents require hotpink')
    for e in accents:
        interval(e,duration)
        if e.get('kind') not in ('rays','hearts') or not str(e.get('reason','')).strip():raise ValueError('Comic accent needs supported kind/reason')
        if any(not finite(e.get(v)) or not 0<=e[v]<=1 for v in ('x','y','width','height')) or not 0<e['width']<=.35 or not 0<e['height']<=.35:raise ValueError('Accent needs bounded normalized rectangle')
        if e.get('side','left') not in ('left','right'):raise ValueError('Invalid accent direction')

def line(p,runs,size,role='body',mode='normal',maxw=None):
    """Tight actual-ink bounds with multi-edge and per-template size hierarchy."""
    c=p.variant['scene_system'];k=c['kind'];u=p.unit;pad=math.ceil(12*u);maxw=maxw or p.w*.86
    for factor in (1,.96,.92,.88,.84,.8,.76,.72):
        glyphs=[];x=0
        for run in runs:
            rr=run.get('role',role);sz=c['keyword_size'] if role=='body' and rr=='keyword' and mode!='ribbon' else size
            f=p.font(sz*factor,rr);bb=f.getbbox(run['text'],anchor='ls');glyphs.append((x,run['text'],f,rr,bb));x+=f.getlength(run['text'])
        left=min(xx+bb[0] for xx,t,f,rr,bb in glyphs);right=max(xx+bb[2] for xx,t,f,rr,bb in glyphs)
        if math.ceil(right-left)+2*pad<=maxw:break
    else:raise ValueError('B4c text too wide; resegment instead of shrinking below 72%')
    top=min(z[4][1] for z in glyphs);bottom=max(z[4][3] for z in glyphs);im=Image.new('RGBA',(math.ceil(right-left)+2*pad,bottom-top+2*pad));d=ImageDraw.Draw(im)
    for x,t,f,rr,bb in glyphs:
        pos=(pad+x-left,pad-top)
        def draw(fill,sw=0,edge=None,dx=0,dy=0):d.text((pos[0]+dx*u,pos[1]+dy*u),t,font=f,anchor='ls',fill=fill,stroke_width=round(sw*u),stroke_fill=edge or fill)
        if k=='elegantpink':
            fill='#FFFFFF' if role=='title' or mode=='ribbon' else '#DA069C' if rr=='keyword' or role=='sticker' else '#080808'
            draw(fill)
        elif k=='promo':
            fill='#ED301B' if rr in ('keyword','sticker') else '#FFFCEF'
            draw('#3D1009',7,dx=1,dy=2);draw('#FFCE74',5);draw('#74180E',3.6);draw(fill,1.3,'#FFF6DE')
            # Original halftone points clipped strictly inside glyph fill, never on counters.
            mask=Image.new('L',im.size);md=ImageDraw.Draw(mask);md.text(pos,t,font=f,anchor='ls',fill=255)
            dots=Image.new('RGBA',im.size);dd=ImageDraw.Draw(dots);step=max(3,round(5*u));rad=max(1,round(.65*u))
            for yy in range(round(im.height*.50),im.height,step):
                for xx in range(0,im.width,step):dd.ellipse((xx,yy,xx+rad,yy+rad),fill='#FFC37B' if rr=='keyword' else '#DC7A56')
            dots.putalpha(ImageChops.multiply(dots.getchannel('A'),mask));im.alpha_composite(dots)
        elif k=='browngold':
            fill='#EABD77' if rr in ('keyword','sticker') or mode=='gold' else '#FFFDF4'
            for z in (5,4,3):draw('#3E3020',1.2,dx=z,dy=z)
            draw(fill,.7,'#6A5134')
        else:
            fill='#F14AA5' if rr in ('keyword','sticker') or role=='title' or mode in ('display','arc') else '#FFF8F3'
            draw('#22121D',4 if role=='title' else 2,dx=2,dy=3);draw(fill,.8,'#782952' if fill=='#F14AA5' else '#7E5B73')
    return im

def backed(im,color,u,pad=0):
    q=round(pad*u);out=Image.new('RGBA',(im.width+q*2,im.height+q*2),color);out.alpha_composite(im,(q,q));return out

def title(p):
    c=p.variant['scene_system'];k=c['kind'];u=p.unit;ims=[]
    for j,t in enumerate(p.p.get('scene_title_lines',[])):
        size=c['title_size'] if j==0 else c['subtitle_size'];mode='gold' if k=='browngold' and j else 'normal'
        im=line(p,[dict(text=t,role='title')],size,'title',mode,p.w*.88)
        if k=='elegantpink':im=backed(im,'#F000B7',u)
        ims.append(im)
    if not ims:return None
    im=stack(ims,round(3*u) if k=='elegantpink' else -round(5*u),'left' if k=='elegantpink' else 'center')
    if k=='hotpink':
        # Broken corner frame, not a uniform banner/card.
        q=round(9*u);out=Image.new('RGBA',(im.width+q*2,im.height+q*2));out.alpha_composite(im,(q,q));d=ImageDraw.Draw(out);w,h=out.size
        d.line((q,h*.32,q,q,w*.15,q),fill='#15131A',width=max(1,round(2*u)));d.line((w-q,h*.65,w-q,h-q,w*.85,h-q),fill='#15131A',width=max(1,round(2*u)));im=out
    return im

def heart(u,color='#EE55A2',size=48):
    n=max(8,round(size*u));im=Image.new('RGBA',(n,n));d=ImageDraw.Draw(im);d.ellipse((n*.08,n*.12,n*.54,n*.59),fill=color);d.ellipse((n*.46,n*.12,n*.92,n*.59),fill=color);d.polygon([(n*.11,n*.40),(n*.89,n*.40),(n*.50,n*.92)],fill=color);return im

def icon(p,kind):
    # 3x supersampling makes deterministic original icons; no emoji or reference bitmaps.
    u=p.unit*3;n=round(76*u);im=Image.new('RGBA',(n,n));d=ImageDraw.Draw(im);sw=max(1,round(2*u))
    if kind in ('heart','heart_cursor'):
        im.alpha_composite(heart(u,'#B690E5' if kind=='heart_cursor' else '#F273B5',68),(0,0))
        if kind=='heart_cursor':d.polygon([(28*u,30*u),(65*u,45*u),(48*u,48*u),(55*u,62*u),(48*u,65*u),(41*u,51*u),(32*u,63*u)],fill='#FFFFFF',outline='#17131B',width=sw)
    elif kind=='megaphone':
        d.polygon([(18*u,30*u),(48*u,18*u),(48*u,54*u),(18*u,45*u)],fill='#EF332B',outline='#8C1E16',width=sw);d.rounded_rectangle((8*u,31*u,23*u,44*u),radius=4*u,fill='#FFEFC9');d.polygon([(25*u,46*u),(37*u,50*u),(32*u,65*u),(22*u,59*u)],fill='#E5AA52');d.ellipse((41*u,17*u,54*u,54*u),fill='#FF5650',outline='#9E281B',width=sw)
        for y,ey in ((17,9),(33,31),(50,57)):d.line((59*u,y*u,71*u,ey*u),fill='#FFD37D',width=round(4*u))
    elif kind=='cart':
        d.line((5*u,18*u,16*u,18*u,24*u,55*u,59*u,55*u),fill='#A62B20',width=round(4*u));d.polygon([(19*u,25*u),(68*u,25*u),(61*u,46*u),(24*u,46*u)],fill='#FFD890',outline='#BE712E',width=sw)
        for x in (31,43,55):d.line((x*u,29*u,x*u,42*u),fill='#6C4D38',width=round(3*u))
        for x in (29,55):d.ellipse(((x-5)*u,60*u,(x+5)*u,70*u),fill='#EBCD83',outline='#623D22',width=sw)
    else:raise ValueError('Unknown original icon')
    return im.resize((round(76*p.unit),round(76*p.unit)),Image.Resampling.LANCZOS)

def arc(p,e):
    from template_scenes import texts
    c=p.variant['scene_system'];chars=list(texts(e));n=len(chars);u=p.unit;ims=[];positions=[];x=0
    for i,ch in enumerate(chars):
        q=(i/(n-1)-.5) if n>1 else 0;im=line(p,[dict(text=ch,role='keyword')],c['display_size'],'sticker','arc',p.w*.25).rotate(-q*24,Image.Resampling.BICUBIC,expand=True)
        y=round(abs(q)*24*u);ims.append(im);positions.append((round(x),y));x+=im.width-round(9*u)
    width=max(x+im.width for (x,y),im in zip(positions,ims));height=max(y+im.height for (x,y),im in zip(positions,ims))
    if width>p.w*.86:raise ValueError('Arc phrase too wide; choose shorter semantic phrase')
    out=Image.new('RGBA',(width,height))
    for im,pos in zip(ims,positions):out.alpha_composite(im,pos)
    return out

def identity(p,e):
    u=p.unit;name=line(p,[dict(text=e['name'],role='sticker')],39,'sticker','gold',p.w*.38)
    # Small serif details use the declared separate role, not the brush name font.
    rows=e.get('detail_lines') or [e['detail']]
    details=[line(p,[dict(text=t,role='translation')],18,'translation','gold',p.w*.42) for t in rows]
    out=stack([name]+details,-round(8*u),'left');d=ImageDraw.Draw(out);d.line((12*u,name.height-7*u,out.width-12*u,name.height-7*u),fill='#E9C88D',width=max(1,round(2*u)));return out

def accent(p,e):
    w=round(p.w*e['width']);h=round(p.h*e['height']);im=Image.new('RGBA',(w,h));d=ImageDraw.Draw(im)
    if e['kind']=='hearts':
        for x,y,s in ((.1,.25,.32),(.53,.05,.22),(.48,.60,.28)):
            v=heart(1,'#F2A1D0',max(8,min(w,h)*s));im.alpha_composite(v,(round(x*w),round(y*h)))
    else:
        # Sparse converging tapered lines in a bounded edge panel; never full-frame face overlay.
        right=e.get('side','left')=='right';target=(0 if right else w,h*.48)
        for j in range(12):
            y=h*(j+.3)/12;x=w if right else 0;end=(target[0]+(w*.20 if right else -w*.20),target[1]+(y-target[1])*.48)
            d.polygon([(x,max(0,y-1.3*p.unit)),(x,min(h,y+1.3*p.unit)),end],fill=(21,17,23,220))
    return im

def layout(p):
    from template_scenes import _box,texts
    c=p.variant['scene_system'];k=c['kind'];u=p.unit;entries=[]
    def add(im,x,y,a,b,role,animation='fade'):
        x=round(x);y=round(y);env=round(10*u) if animation in ('soft','label') else 0
        entries.append(dict(image=im,x=x,y=y,start=a,end=b,role=role,animation=animation,box=_box(im,x,y,env)))
    ti=title(p)
    if ti:add(ti,(p.w-ti.width)/2,p.h*c['title_y']-ti.height/2,0,min(p.p['duration'],p.p.get('title_duration',c['title_duration'])),'title')
    translations={e['phrase_id']:e for e in p.p.get('scene_translations',[])}
    for g in p.p['scene_captions']:
        blocks=[]
        for e in g['phrases']:
            mode=e.get('mode','bilingual' if k=='elegantpink' else 'normal');runs=e.get('runs') or [dict(text=texts(e),role='body')]
            if mode=='arc':im=arc(p,e)
            else:im=line(p,runs,36 if mode=='ribbon' else c['body_size'] if mode!='display' else c['display_size'],'body',mode)
            if k=='elegantpink':im=backed(im,'#F000B7' if mode=='ribbon' else '#FFFFFF',u)
            en=None
            if e['id'] in translations:
                rows,size=wrap_text(p,translations[e['id']]['text'],c['translation_size'],p.w*.80-24*u)
                en=stack([line(p,[dict(text=t,role='translation')],size,'translation',maxw=p.w*.82) for t in rows],-round(12*u));en=backed(en,'#FFFFFF',u)
            blocks.append((e,im,en))
        gap=round(6*u);total=sum(im.height+(en.height+round(2*u) if en else 0) for _,im,en in blocks)+gap*(len(blocks)-1);y=p.h*c['caption_y']-total/2
        for j,(e,im,en) in enumerate(blocks):
            x=(p.w-im.width)/2 if len(blocks)==1 else p.w*.08 if j%2==0 else p.w*.92-im.width
            add(im,x,y,e['start'],e['end'],'caption','pop' if k in ('promo','hotpink') else 'label' if k=='elegantpink' and e.get('mode')=='ribbon' else 'fade')
            if en:
                te=translations[e['id']];add(en,(p.w-en.width)/2,y+im.height+round(2*u),te['start'],te['end'],'translation')
            y+=im.height+(en.height+round(2*u) if en else 0)+gap
    for e in p.p.get('scene_tags',[]):
        im=line(p,[dict(text=e['text'],role='sticker')],c['tag_size'],'sticker',maxw=p.w*.32)
        if e.get('icon'):
            ic=icon(p,e['icon']);out=Image.new('RGBA',(max(im.width,ic.width),im.height+ic.height-round(9*u)));out.alpha_composite(ic,((out.width-ic.width)//2,0));out.alpha_composite(im,((out.width-im.width)//2,ic.height-round(9*u)));im=out
        if k=='hotpink':im=im.rotate(7,Image.Resampling.BICUBIC,expand=True)
        x=p.w*.95-im.width if e.get('side','right')=='right' else p.w*.05
        add(im,x,p.h*c['tag_y']-im.height/2,e['start'],e['end'],'tag','pop')
    for e in p.p.get('scene_callouts',[]):
        im=line(p,[dict(text=e['text'],role='sticker')],22,'sticker',maxw=p.w*.27);im=backed(im,'#FFEFFB',u)
        x=p.w*.055 if e.get('side','left')=='left' else p.w*.945-im.width
        if 'x' in e:x=p.w*e['x']
        y=p.h*e['y'] if 'y' in e else p.h*(c['callout_y']+e['slot']*c['callout_step'])
        add(im,x,y,e['start'],e['end'],'callout')
    for e in p.p.get('scene_identity',[]):add(identity(p,e),p.w*e['x'],p.h*e['y'],e['start'],e['end'],'identity')
    for e in p.p.get('scene_accents',[]):add(accent(p,e),p.w*e['x'],p.h*e['y'],e['start'],e['end'],'accent')
    return entries
