"""B5b independent brown/ginger/black-yellow/verdant designs.
All type textures and geometry are original; no inferred official font or tracking.
"""
import math,random,hashlib
from PIL import Image,ImageDraw,ImageFilter,ImageChops
from template_scenes_b3b import stack
KINDS={'deepbrown','ginger','blackyellow','verdant'}
MODES={'deepbrown':{'normal'},'ginger':{'normal','display','impact'},'blackyellow':{'normal','display'},'verdant':{'normal','compact'}}

def validate(p):
    from template_scenes import interval,texts,finite
    k=p.variant['scene_system']['kind'];phrases={};duration=p.p['duration']
    if any(p.p.get(key) for key in ('scene_notes','scene_highlights','scene_title_surface','scene_identity','scene_accents','scene_media')):raise ValueError('Unsupported B5b auxiliary layer')
    for g in p.p['scene_captions']:
        for e in g['phrases']:
            ident=e.get('id')
            if not isinstance(ident,str) or not ident or ident in phrases:raise ValueError('B5b needs unique phrase ids')
            phrases[ident]=e
            if e.get('mode','normal') not in MODES[k]:raise ValueError('Unsupported B5b phrase mode')
            if any(e.get(key) for key in ('pointer','underline')) or e.get('color','normal')!='normal' or any('fill' in r for r in e.get('runs',[])):raise ValueError('B5b decoration/color is contract bound')
    for e in p.p.get('scene_tags',[]):
        a,b=interval(e,duration);q=phrases.get(e.get('phrase_id'))
        if not q or not q['start']<=a<b<=q['end'] or e['text'] not in texts(q):raise ValueError('Tag must quote active B5b phrase')
        if e.get('orientation','horizontal')!='horizontal' or e.get('icon'):raise ValueError('B5b tags use typography, not arbitrary icons')
    calls=p.p.get('scene_callouts',[])
    if not isinstance(calls,list) or calls and k not in ('blackyellow','verdant'):raise ValueError('Retained labels require blackyellow or verdant')
    for e in calls:
        a,b=interval(e,duration);q=phrases.get(e.get('phrase_id'))
        if not q or not q['start']<=a<q['end'] or not isinstance(e.get('text'),str) or not 1<=len(e['text'])<=10 or e['text'] not in texts(q):raise ValueError('Retained label must quote phrase and enter during it')
        if isinstance(e.get('slot'),bool) or e.get('slot') not in (0,1) or e.get('side','left') not in ('left','right') or not str(e.get('reason','')).strip():raise ValueError('Label needs slot/side/reason')
        if any(v in e for v in ('x','y')) and any(not finite(e.get(v)) or not 0<=e[v]<=1 for v in ('x','y')):raise ValueError('Label anchor needs normalized x/y together')
    for i,e in enumerate(calls):
        for q in calls[i+1:]:
            if e.get('side','left')==q.get('side','left') and e['slot']==q['slot'] and min(e['end'],q['end'])>max(e['start'],q['start']):raise ValueError('Overlapping retained label slot')
    for e in p.p.get('scene_canvas',[]):
        if k=='verdant' and e['kind']=='circle' and not str(e.get('composition_review','')).strip():raise ValueError('Verdant circle needs actual composition review, never a default privacy shortcut')

def line(p,runs,size,role='body',mode='normal',maxw=None):
    k=p.variant['scene_system']['kind'];u=p.unit;maxw=maxw or p.w*.88
    pad=math.ceil((20 if k=='blackyellow' and mode=='display' else 12)*u)
    shear=.14 if k=='ginger' and (role=='title' or mode in ('display','impact')) else 0
    original=size
    for attempt in range(4):
        glyphs=[];x=0
        for r in runs:
            rr=r.get('role',role);f=p.font(size,rr);t=r['text'];bb=f.getbbox(t,anchor='ls');glyphs.append((x,t,f,rr,bb));x+=f.getlength(t)
        left=min(x+b[0] for x,t,f,r,b in glyphs);right=max(x+b[2] for x,t,f,r,b in glyphs);top=min(b[1] for x,t,f,r,b in glyphs);bottom=max(b[3] for x,t,f,r,b in glyphs)
        h=bottom-top+2*pad;w=math.ceil(right-left)+2*pad;final=w+math.ceil(h*shear)
        if final<=maxw:break
        size*=min(.97,(maxw-2*pad-math.ceil(h*shear))/max(1,right-left))
        if size<original*.72:raise ValueError('B5b text too long; split semantic phrases, not tiny type')
    else:raise ValueError('B5b text does not fit safe width')
    im=Image.new('RGBA',(w,h));d=ImageDraw.Draw(im);mask=Image.new('L',im.size);md=ImageDraw.Draw(mask)
    for x,t,f,rr,bb in glyphs:
        pos=(pad+x-left,pad-top)
        def draw(fill,sw=0,edge=None,dx=0,dy=0):d.text((pos[0]+dx*u,pos[1]+dy*u),t,font=f,anchor='ls',fill=fill,stroke_width=round(sw*u),stroke_fill=edge or fill)
        if k=='deepbrown':
            if role=='title':draw('#352515',1.4,dx=2,dy=3);draw('#F4D48F',.25,'#FBEAC5');md.text(pos,t,font=f,anchor='ls',fill=255)
            else:
                fill='#FFF1CC' if rr=='keyword' else '#413826';edge='#312518' if rr=='keyword' else '#FFF5D6'
                draw('#281A0E',4.2,dx=1,dy=2);draw(fill,2.8,edge)
        elif k=='ginger':
            fill='#F19BBD' if mode=='impact' or rr=='keyword' and mode!='normal' else '#FFFDF2'
            draw('#3F3137',1.2,dx=2,dy=2);draw(fill,.65,'#815769' if fill=='#F19BBD' else '#4B3E43')
        elif k=='blackyellow':
            if role=='sticker':draw('#49442D')
            elif mode=='display':
                fill='#FFFDF1' if rr=='keyword' else '#FFF796'
                draw('#514B17',.55,dx=.5,dy=1);draw(fill,.5,'#EAD648');md.text(pos,t,font=f,anchor='ls',fill=220,stroke_width=max(1,round(1*u)))
            else:
                if role=='title':draw('#28241E',.7,dx=1.5,dy=2)
                draw('#FFFDF3',.55 if role=='title' else .35,'#292720' if role=='title' else '#121212')
        else:
            if role=='title':draw('#1A391D',4,dx=1,dy=2);draw('#38682B',3,'#F8F5D8')
            elif role=='sticker':draw('#F8F5D8')
            else:
                fill='#6EB252' if rr=='keyword' else '#FFFEE9';draw('#19351B',1.0,dx=1.7,dy=2.1);draw(fill,.35,'#264925')
    if k=='deepbrown' and role=='title':
        # Fixed original fine gold flecks clipped to glyph interiors, not random frame noise.
        texture=Image.new('RGBA',im.size);td=ImageDraw.Draw(texture);rng=random.Random(hashlib.sha256(''.join(r['text'] for r in runs).encode()).hexdigest())
        for _ in range(max(1,round(w*h/95))):
            x=rng.randrange(w);y=rng.randrange(h);td.line((x,y,x+rng.randrange(1,4),y),fill=(128,84,32,100),width=max(1,round(u)))
        texture.putalpha(ImageChops.multiply(texture.getchannel('A'),mask));im.alpha_composite(texture)
    if k=='blackyellow' and mode=='display':
        glow=Image.new('RGBA',im.size,'#FFF35B');glow.putalpha(mask.filter(ImageFilter.GaussianBlur(4*u)).point(lambda a:round(a*.7)));glow.alpha_composite(im);im=glow
    if shear:
        extra=math.ceil(h*shear);im=im.transform((w+extra,h),Image.Transform.AFFINE,(1,shear,-extra,0,1,0),Image.Resampling.BICUBIC)
    return im

def backed(im,color,u):
    out=Image.new('RGBA',im.size);d=ImageDraw.Draw(out);d.rounded_rectangle((0,0,im.width-1,im.height-1),radius=round(2*u),fill=color);out.alpha_composite(im);return out

def bracket(im,u):
    q=round(8*u);out=Image.new('RGBA',(im.width+2*q,im.height));out.alpha_composite(im,(q,0));d=ImageDraw.Draw(out);w,h=out.size;c='#E4DFD3'
    d.arc((1,h*.18,16*u,h*.78),170,280,fill=c,width=max(1,round(.7*u)));d.arc((w-16*u,h*.18,w-1,h*.78),-10,100,fill=c,width=max(1,round(.7*u)));return out

def label(p,text,size,maxw):
    k=p.variant['scene_system']['kind'];u=p.unit
    im=line(p,[dict(text=text,role='sticker')],size,'sticker',maxw=maxw)
    if k=='blackyellow':return backed(im,'#FFFDF4',u)
    if k=='verdant':
        im=backed(im,'#66944D',u);d=ImageDraw.Draw(im)
        for x in range(round(5*u),im.width-round(4*u),max(2,round(5*u))):d.line((x,2*u,x+u,2*u),fill='#ECE6BB',width=max(1,round(u)))
    return im

def title(p):
    c=p.variant['scene_system'];k=c['kind'];u=p.unit;ims=[]
    for i,t in enumerate(p.p.get('scene_title_lines',[])):
        im=line(p,[dict(text=t,role='title')],c['title_size'] if i==0 else c['subtitle_size'],'title',maxw=p.w*.84);ims.append(im)
    if not ims:return None
    im=stack(ims,round(2*u))
    if k=='ginger':
        q=round(14*u);out=Image.new('RGBA',(im.width+2*q,im.height+2*q));mask=Image.new('L',out.size);ImageDraw.Draw(mask).ellipse((q,im.height*.12,out.width-q,out.height-im.height*.12),fill=70);glow=Image.new('RGBA',out.size,'#DAA5BF');glow.putalpha(mask.filter(ImageFilter.GaussianBlur(12*u)));out.alpha_composite(glow);out.alpha_composite(im,(q,q));im=out
    return im

def layout(p):
    from template_scenes import texts,_box
    c=p.variant['scene_system'];k=c['kind'];u=p.unit;entries=[]
    def add(im,x,y,a,b,role,anim='fade'):
        x=round(x);y=round(y);env=round(10*u) if anim in ('label','soft') else 0;entries.append(dict(image=im,x=x,y=y,start=a,end=b,role=role,animation=anim,box=_box(im,x,y,env)))
    ti=title(p)
    if ti:add(ti,(p.w-ti.width)/2,p.h*c['title_y']-ti.height/2,0,min(p.p['duration'],p.p.get('title_duration',c['title_duration'])),'title')
    for g in p.p['scene_captions']:
        blocks=[]
        for e in g['phrases']:
            mode=e.get('mode','normal');runs=e.get('runs') or [dict(text=texts(e),role='body')];size=c['display_size'] if mode in ('display','impact') else c['compact_size'] if mode=='compact' else c['body_size']
            im=line(p,runs,size,'body',mode,p.w*.86)
            if k=='ginger' and mode=='normal':im=bracket(im,u)
            if k=='blackyellow' and mode=='normal':im=backed(im,'#101010',u)
            blocks.append((e,im))
        gap=round(3*u);total=sum(im.height for e,im in blocks)+gap*(len(blocks)-1);y=p.h*c['caption_y']-total/2
        for i,(e,im) in enumerate(blocks):
            x=(p.w-im.width)/2
            if k=='verdant' and len(blocks)==2:x=p.w*.10 if i==0 else p.w*.90-im.width
            anim='soft' if k=='ginger' and e.get('mode')=='impact' else 'pop' if k=='verdant' and e.get('mode','normal')=='normal' else 'fade'
            add(im,x,y,e['start'],e['end'],'caption',anim);y+=im.height+gap
    for e in p.p.get('scene_tags',[]):
        im=label(p,e['text'],c['tag_size'],p.w*.31);x=p.w*.94-im.width if e.get('side','right')=='right' else p.w*.06
        add(im,x,p.h*c['tag_y']-im.height/2,e['start'],e['end'],'tag','label')
    for e in p.p.get('scene_callouts',[]):
        im=label(p,e['text'],22,p.w*.34);x=p.w*.06 if e.get('side','left')=='left' else p.w*.94-im.width
        add(im,p.w*e['x'] if 'x' in e else x,p.h*e['y'] if 'y' in e else p.h*(c['callout_y']+e['slot']*.06),e['start'],e['end'],'callout')
    return entries
