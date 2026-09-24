"""Four distinct B4b layouts. Authored clocks, no semantic invention or tracking."""
import math
from PIL import Image, ImageDraw
from template_scenes_b3b import stack
from scene_bilingual import wrap_text
KINDS={'neon','purple','warm','mono'}

def validate(p):
    from template_scenes import interval,texts,finite
    k=p.variant['scene_system']['kind'];phrases={}
    if any(p.p.get(key) for key in ('scene_notes','scene_highlights','scene_title_surface','scene_identity','scene_callouts')):
        raise ValueError('B4b does not implement legacy auxiliary layers')
    for g in p.p['scene_captions']:
        for e in g['phrases']:
            ident=e.get('id')
            if not isinstance(ident,str) or not ident or ident in phrases:raise ValueError('B4b requires unique phrase ids')
            phrases[ident]=e
            mode=e.get('mode','normal')
            if mode not in ({'normal','bilingual','vertical'} if k=='purple' else {'normal'}):raise ValueError('Unsupported B4b mode')
            if e.get('pointer') or e.get('color','normal')!='normal' or any('fill' in r for r in e.get('runs',[])):raise ValueError('B4b style is contract-bound')
            if mode=='vertical':
                if not 1<=len(texts(e))<=10:raise ValueError('Vertical phrase max ten characters; split semantically')
                if not str(e.get('reason','')).strip() or not all(finite(e.get(v)) and 0<=e[v]<=1 for v in ('x','y')):raise ValueError('Vertical phrase needs explicit anchor and composition reason')
                if any(x.get('mode')!='vertical' for x in g['phrases']):raise ValueError('Vertical group cannot mix horizontal layout')
    for e in p.p.get('scene_tags',[]):
        a,b=interval(e,p.p['duration']);q=phrases.get(e.get('phrase_id'))
        if not q or not q['start']<=a<b<=q['end'] or e['text'] not in texts(q):raise ValueError('Tag must quote its active anchored phrase')
        orient=e.get('orientation','horizontal')
        if orient not in ({'horizontal','vertical'} if k in ('purple','mono') else {'horizontal'}):raise ValueError('Unsupported tag orientation')
        if orient=='vertical' and len(e['text'])>4:raise ValueError('Vertical tag max four characters')
        if e.get('icon'):raise ValueError('B4b does not ship official sticker icons')

def line(p,runs,size,role='body',maxw=None):
    """Baseline aligned mixed weights, then original outlined styling. Never truncate."""
    c=p.variant['scene_system'];k=c['kind'];u=p.unit;pad=round(11*u);maxw=maxw or p.w*.86
    for scale in (1,.96,.92,.88,.84,.8,.76,.72):
        glyphs=[];x=0
        for r in runs:
            rr=r.get('role',role);sz=c['keyword_size'] if rr=='keyword' and role=='body' else size
            f=p.font(sz*scale,rr);glyphs.append((x,r['text'],f,rr));x+=f.getlength(r['text'])
        if x+2*pad<=maxw:break
    else:raise ValueError('B4b phrase exceeds bounded 72% fitting; resegment')
    top=min(f.getbbox(t,anchor='ls')[1] for _,t,f,_ in glyphs);bottom=max(f.getbbox(t,anchor='ls')[3] for _,t,f,_ in glyphs)
    im=Image.new('RGBA',(math.ceil(x)+2*pad,bottom-top+2*pad));d=ImageDraw.Draw(im)
    for x,t,f,r in glyphs:
        pos=(pad+x,pad-top)
        accent={'neon':'#D5FF00','purple':'#B78AD6','warm':'#FFE35B','mono':'#FF9447'}[k]
        fill=accent if r in ('keyword','sticker') or role=='title' and k in ('warm','purple') else '#FFFFFF'
        def draw(col,sw=0,edge=None,dx=0,dy=0):d.text((pos[0]+dx*u,pos[1]+dy*u),t,font=f,anchor='ls',fill=col,stroke_width=round(sw*u),stroke_fill=edge or col)
        if k=='warm':
            if role=='title':draw('#FF7A20',7,'#FF8D25',1,2);draw('#FFF6C6',5);draw('#FF841F',2.5,'#79270F')
            else:draw(fill,3.3,'#5A2315')
        elif k=='mono':draw(fill,4,'#10110E');draw(fill,.6,'#FAF6DA')
        elif k=='purple':draw('#292230',2,dx=3,dy=4);draw(fill)
        else:draw('#252A12',.8,dx=1,dy=2);draw(fill)
    # Upright Noto glyphs skewed for purple, not sentence rotation. Columns remain upright.
    if k=='purple' and role!='translation':
        extra=math.ceil(im.height*.14);out=im.transform((im.width+extra,im.height),Image.Transform.AFFINE,(1,.14,-extra,0,1,0),resample=Image.Resampling.BICUBIC)
        if out.width>maxw:raise ValueError('Oblique glyph envelope exceeds width')
        im=out
    return im

def vertical(p,runs,size,role='body'):
    ims=[line(p,[dict(text=ch,role=r.get('role',role))],size,role,p.w*.25) for r in runs for ch in r['text']]
    return stack(ims,-round(13*p.unit))

def title(p):
    c=p.variant['scene_system'];k=c['kind'];u=p.unit;ims=[]
    for j,t in enumerate(p.p.get('scene_title_lines',[])):
        if k=='neon':t='['+t+']' if j==0 else '# '+t
        role='sticker' if k=='neon' and j else 'body' if k=='purple' and j else 'title'
        im=line(p,[dict(text=t,role=role)],c['title_size'] if j==0 else c['subtitle_size'],role,p.w*.91)
        if k=='mono':
            bg=Image.new('RGBA',im.size,(12,12,11,220));bg.alpha_composite(im);im=bg
        if k=='neon' and j:
            d=ImageDraw.Draw(im);d.line((12*u,im.height-5*u,im.width-12*u,im.height-5*u),fill='#D5FF00',width=max(1,round(u)))
        ims.append(im)
    return stack(ims,-round(5*u) if k in ('warm','mono') else round(2*u)) if ims else None

def layout(p):
    from template_scenes import _box,texts
    c=p.variant['scene_system'];k=c['kind'];u=p.unit;entries=[]
    def add(im,x,y,a,b,role,animation='fade'):
        x=round(x);y=round(y);env=round(10*u) if animation=='soft' else 0
        entries.append(dict(image=im,x=x,y=y,start=a,end=b,role=role,animation=animation,box=_box(im,x,y,env)))
    ti=title(p)
    if ti:add(ti,(p.w-ti.width)/2,p.h*c['title_y']-ti.height/2,0,min(p.p['duration'],p.p.get('title_duration',c['title_duration'])),'title')
    translations={e['phrase_id']:e for e in p.p.get('scene_translations',[])}
    for g in p.p['scene_captions']:
        blocks=[]
        for e in g['phrases']:
            runs=e.get('runs') or [dict(text=texts(e),role='body')]
            if e.get('mode')=='vertical':
                im=vertical(p,runs,c['body_size']);add(im,p.w*e['x'],p.h*e['y'],e['start'],e['end'],'caption');continue
            im=line(p,runs,c['body_size'])
            if k=='warm':
                bg=Image.new('RGBA',im.size);d=ImageDraw.Draw(bg);d.rounded_rectangle((0,im.height*.50,im.width-1,im.height-2*u),radius=13*u,fill='#FF651B');bg.alpha_composite(im);im=bg
            en=None
            if e['id'] in translations:
                rows,size=wrap_text(p,translations[e['id']]['text'],c['translation_size'],p.w*.80-22*u)
                en=stack([line(p,[dict(text=t,role='translation')],size,'translation',p.w*.82) for t in rows],-round(12*u))
            blocks.append((e,im,en))
        gap=round(7*u);total=sum(im.height+(en.height if en else 0) for _,im,en in blocks)+gap*max(0,len(blocks)-1);y=p.h*c['caption_y']-total/2
        for j,(e,im,en) in enumerate(blocks):
            if len(blocks)==1:x=(p.w-im.width)/2
            elif k=='neon':x=p.w*.08 if j==0 else p.w*.92-im.width if j==len(blocks)-1 else (p.w-im.width)/2
            elif k=='warm':x=p.w*(.08+j*.09)
            else:x=p.w*.08 if j==0 else p.w*.92-im.width
            add(im,x,y,e['start'],e['end'],'caption','pop' if k=='warm' else 'soft' if k=='neon' else 'fade')
            if en:
                te=translations[e['id']];add(en,(p.w-en.width)/2,y+im.height,te['start'],te['end'],'translation')
            y+=im.height+(en.height if en else 0)+gap
    for e in p.p.get('scene_tags',[]):
        runs=[dict(text=e['text'],role='sticker')]
        im=vertical(p,runs,c['tag_size'],'sticker') if e.get('orientation')=='vertical' else line(p,runs,c['tag_size'],'sticker',p.w*.38)
        x=p.w*.95-im.width if e.get('side','right')=='right' else p.w*.05
        add(im,x,p.h*c['tag_y']-im.height/2,e['start'],e['end'],'tag','pop' if k=='warm' else 'fade')
    return entries
