"""B4a reference-led typography and bounded semantic graphic components.
Original assets only. Shared helpers describe rendering, never choose semantics.
"""
import math
from PIL import Image,ImageDraw,ImageFilter
from scene_bilingual import wrap_text
from template_scenes_b3b import stack
KINDS={'shine','green','tech','science'}


def validate(p):
    from template_scenes import interval,texts,finite
    k=p.variant['scene_system']['kind'];duration=p.p['duration']
    if p.p.get('scene_notes') or p.p.get('scene_highlights') or p.p.get('scene_title_surface'):
        raise ValueError('B4 uses own callouts/identity schema, not legacy notes or highlights')
    phrases={}
    for g in p.p['scene_captions']:
        for e in g['phrases']:
            ident=e.get('id')
            if not isinstance(ident,str) or not ident or ident in phrases:raise ValueError('B4 phrases require unique ids')
            phrases[ident]=e
            modes={'compact','display'} if k=='green' else {'normal','paper'} if k=='science' else {'normal'}
            if e.get('mode','compact' if k=='green' else 'normal') not in modes:raise ValueError('Unsupported B4 phrase mode')
            if e.get('color','normal')!='normal' or any('fill' in r for r in e.get('runs',[])):raise ValueError('B4 colors are template-bound')
            pointer=e.get('pointer')
            if pointer is not None:
                if k not in ('shine','science') or not isinstance(pointer,str) or not pointer or pointer not in texts(e):raise ValueError('Pointer must quote its phrase in a pointer-enabled template')
                runs=e.get('runs') or [dict(text=texts(e),role='body')]
                if sum(r['text'].count(pointer) for r in runs)!=1:raise ValueError('Pointer needs one unambiguous occurrence wholly within one run')
            if k=='green' and e.get('mode','compact')=='compact' and len(g['phrases'])!=1:raise ValueError('Compact bilingual mode requires one phrase per group')
    for e in p.p.get('scene_tags',[]):
        a,b=interval(e,duration);q=phrases.get(e.get('phrase_id'))
        if not q or not q['start']<=a<b<=q['end'] or e.get('text') not in texts(q):raise ValueError('B4 tag must quote its anchored active phrase')
        if e.get('side','right') not in ('left','right'):raise ValueError('Unknown tag side')
        if e.get('icon') not in ({None,'bulb'} if k=='shine' else {None}):raise ValueError('Icon unsupported by this template')
        if e.get('orientation','horizontal') not in ({'horizontal','vertical'} if k=='shine' else {'horizontal'}):raise ValueError('Unsupported tag orientation')
        if e.get('orientation')=='vertical' and len(e['text'])>4:raise ValueError('Vertical tag max four characters')
    callouts=p.p.get('scene_callouts',[])
    if callouts and k!='green':raise ValueError('Retained chevron callouts require green template')
    for e in callouts:
        a,b=interval(e,duration);q=phrases.get(e.get('phrase_id'))
        if not q or not q['start']<=a<q['end'] or not isinstance(e.get('text'),str) or not 1<=len(e['text'])<=6 or e['text'] not in texts(q):raise ValueError('Callout must quote phrase and enter while phrase is active')
        if not str(e.get('reason','')).strip() or e.get('slot') not in (0,1) or isinstance(e.get('slot'),bool) or e.get('side','right') not in ('left','right'):raise ValueError('Callout needs semantic reason and declared slot/side')
    for i,e in enumerate(callouts):
        for other in callouts[i+1:]:
            if e['slot']==other['slot'] and min(e['end'],other['end'])>max(e['start'],other['start']):raise ValueError('Overlapping callout slot')
    identity=p.p.get('scene_identity',[])
    if identity and k not in ('tech','science'):raise ValueError('Identity card not part of template')
    if not isinstance(identity,list) or len(identity)>1:raise ValueError('At most one reviewed identity card')
    for e in identity:
        interval(e,duration)
        for field,limit in (('name',4),('detail',12)):
            if not isinstance(e.get(field),str) or not 1<=len(e[field])<=limit:raise ValueError('Identity text exceeds declared compact card')
        if e.get('review_status')!='reviewed' or not str(e.get('source','')).strip() or not str(e.get('reviewer','')).strip() or not str(e.get('reason','')).strip():raise ValueError('Identity requires source, reviewer, reviewed status and framing reason')
        x=e.get('x');y=e.get('y')
        if not finite(x) or not finite(y) or not 0<=x<=1 or not 0<=y<=1:raise ValueError('Identity needs explicit normalized top-left position')


def _gradient(size,stops):
    import numpy as np
    h=size[1];ys=np.linspace(0,1,h);rgb=np.stack([np.interp(ys,[a for a,b in stops],[b[c] for a,b in stops]) for c in range(3)],axis=1)
    arr=np.repeat(rgb[:,None,:],size[0],axis=1).astype('uint8');return Image.fromarray(arr).convert('RGBA')


def line(p,runs,size,role='body',style='normal',maxw=None):
    c=p.variant['scene_system'];k=c['kind'];u=p.unit;pad=math.ceil(13*u);maxw=maxw or p.w*.86
    shear=.14 if k in ('tech','science') and role in ('title','sticker') else 0
    for factor in (1,.96,.92,.88,.84,.8,.76,.72):
        glyphs=[];cursor=0;left=right=top=bottom=0
        for r in runs:
            rr=r.get('role',role);sz=c['keyword_size'] if role=='body' and rr=='keyword' else size
            if k=='green' and style=='compact':sz=c['compact_size']
            f=p.font(sz*factor,rr);box=f.getbbox(r['text'],anchor='ls');glyphs.append((cursor,r['text'],f,rr));left=min(left,cursor+box[0]);right=max(right,cursor+box[2]);top=min(top,box[1]);bottom=max(bottom,box[3]);cursor+=f.getlength(r['text'])
        if right-left+2*pad+math.ceil((bottom-top+2*pad)*shear)<=maxw:break
    else:raise ValueError('B4 text too long; resegment faithfully, minimum scale 72%')
    im=Image.new('RGBA',(math.ceil(right-left)+2*pad,math.ceil(bottom-top)+2*pad));d=ImageDraw.Draw(im);positions=[]
    for x,value,f,rr in glyphs:
        xx=pad+x-left;yy=pad-top;positions.append((value,xx,f))
        def ink(fill,sw=0,edge=None,dx=0,dy=0):
            d.text((xx+dx*u,yy+dy*u),value,font=f,anchor='ls',fill=fill,stroke_width=max(0,round(sw*u)),stroke_fill=edge or fill)
        def fill_gradient(stops):
            mask=Image.new('L',im.size);ImageDraw.Draw(mask).text((xx,yy),value,font=f,anchor='ls',fill=255)
            grad=_gradient(im.size,stops);im.paste(grad,(0,0),mask)
        if role=='translation':ink('#78F4B1',1.1,'#162A22')
        elif k=='shine':
            for z in (5,4,3):ink('#685019',1.5,dx=z*.5,dy=z)
            ink('#FFE34A' if rr in ('keyword','title','sticker') else '#FFFDE7',2.0,'#8F6A16')
            if rr in ('keyword','title','sticker'):fill_gradient([(0,(255,224,57)),(.4,(255,233,76)),(1,(255,255,218))])
        elif k=='green':
            if style=='subhead':ink('#092018')
            else:
                ink('#19201B',2,dx=1,dy=2)
                ink('#60EB9F' if rr=='keyword' or style=='compact' else '#FFFFFF',.5,'#D8FFE8' if rr=='keyword' else '#FFFFFF')
        elif k=='tech':
            if role=='title':
                for z in (5,4,3):ink('#182442',1,dx=z*.35,dy=z)
                ink('#FFFFFF',.7,'#CEEAFF');fill_gradient([(0,(255,255,255)),(.4,(240,250,255)),(.52,(126,153,193)),(.65,(255,255,255)),(1,(205,229,255))])
            elif role=='sticker':ink('#142F70',4,dx=1,dy=1);ink('#FFFFFF',2.6);ink('#1466C1')
            else:ink('#A4F1FF',.25,'#DEF9FF')
        elif k=='science':
            if role=='title':
                ink('#171818',4,dx=1.5,dy=3);ink('#B73731' if style=='headline' else '#132FAB',2.0,'#FFFFFF')
            elif style=='paper':
                ink('#201E14',3,dx=1,dy=2);ink('#A43739' if rr=='keyword' else '#F9F56D',1,'#FFF9E9')
            else:ink('#141414',3,dx=1,dy=1);ink('#FFFFFF')
    if shear:
        extra=math.ceil(im.height*shear);im=im.transform((im.width+extra,im.height),Image.Transform.AFFINE,(1,shear,-extra,0,1,0),Image.Resampling.BICUBIC)
    im.info['positions']=positions
    return im


def hand(u):
    """Original pointing-hand pictogram; no emoji/font dependence."""
    s=4;im=Image.new('RGBA',(int(42*u*s),int(52*u*s)));d=ImageDraw.Draw(im)
    pts=[(12,46),(7,33),(3,26),(5,22),(9,24),(14,30),(14,7),(17,3),(21,5),(22,23),(25,20),(29,22),(32,23),(35,27),(35,36),(30,47)]
    pts=[(round(x*u*s),round(y*u*s)) for x,y in pts];d.polygon(pts,fill='#FFF082',outline='#B28D26',width=max(1,round(1.5*u*s)))
    for x in (24,29):d.line((x*u*s,25*u*s,x*u*s,33*u*s),fill='#D7B341',width=max(1,round(u*s)))
    return im.resize((round(42*u),round(52*u)),Image.Resampling.LANCZOS)


def bulb(u):
    s=3;im=Image.new('RGBA',(round(55*u*s),round(67*u*s)));d=ImageDraw.Draw(im);sc=lambda v:round(v*u*s)
    d.ellipse((sc(12),sc(9),sc(43),sc(41)),fill='#FFF4A1',outline='#B78A26',width=sc(2));d.polygon([(sc(18),sc(34)),(sc(37),sc(34)),(sc(33),sc(50)),(sc(22),sc(50))],fill='#FFEE8C');d.rectangle((sc(22),sc(50),sc(33),sc(57)),fill='#C8BA8E');d.line((sc(22),sc(53),sc(33),sc(53)),fill='#6D6655',width=sc(1))
    for x1,y1,x2,y2 in [(27,1,27,5),(3,22,8,24),(47,24,53,22),(7,6,11,10),(44,9,48,5)]:d.line(tuple(sc(v) for v in (x1,y1,x2,y2)),fill='#F4D44D',width=sc(2))
    return im.resize((round(55*u),round(67*u)),Image.Resampling.LANCZOS)


def pointer_sprite(p,e,im):
    word=e.get('pointer')
    if not word:return im
    u=p.unit;h=hand(u);x=None
    for text,xx,f in im.info['positions']:
        if word in text:x=xx+f.getlength(text.split(word,1)[0])+f.getlength(word)/2-h.width/2;break
    if x is None:raise ValueError('Unresolved pointer run')
    # Never clamp to wrong word: pad sprite to contain indicated location.
    offset=max(0,math.ceil(-x));width=max(im.width+offset,math.ceil(x+offset+h.width))
    out=Image.new('RGBA',(width,im.height+h.height-round(8*u)));out.alpha_composite(im,(offset,0));out.alpha_composite(h,(round(x)+offset,im.height-round(8*u)));return out


def title(p):
    c=p.variant['scene_system'];k=c['kind'];u=p.unit;ims=[]
    for j,text in enumerate(p.p.get('scene_title_lines',[])):
        im=line(p,[dict(text=text,role='title')],c['title_size'] if j==0 else c['subtitle_size'],'title','headline' if j==0 else 'subhead',p.w*.88)
        if k=='green':
            bg=Image.new('RGBA',im.size,'#4DEC93' if j else (20,20,16,165));bg.alpha_composite(im);im=bg
        ims.append(im)
    if not ims:return None
    im=stack(ims,-round(10*u) if k in ('shine','science') else round(2*u),'right' if k=='green' else 'center')
    if k=='shine':
        extra=round(10*u);out=Image.new('RGBA',(im.width,im.height+extra));d=ImageDraw.Draw(out)
        d.polygon([(6*u,im.height),(im.width-13*u,im.height-6*u),(im.width-7*u,im.height+3*u),(9*u,im.height+7*u)],fill='#FFF2A0');out.alpha_composite(im);im=out
    return im


def tech_rail(p):
    u=p.unit;w=round(p.w*.91);h=round(77*u);im=Image.new('RGBA',(w,h));d=ImageDraw.Draw(im)
    d.polygon([(43*u,8*u),(w-4*u,8*u),(w-42*u,h-6*u),(6*u,h-6*u)],fill='#375DAD')
    d.polygon([(39*u,3*u),(w-6*u,3*u),(w-43*u,h-14*u),(3*u,h-14*u)],fill='#09277E')
    d.polygon([(39*u,3*u),(w-6*u,3*u),(w-11*u,10*u),(41*u,10*u),(12*u,h-14*u),(3*u,h-14*u)],fill='#A6F0FF')
    d.polygon([(w*.49,11*u),(w*.79,11*u),(w*.60,h-16*u),(w*.24,h-16*u)],fill='#174994')
    d.polygon([(w*.87,17*u),(w-18*u,17*u),(w-45*u,h-18*u),(w*.71,h-18*u)],fill='#133985')
    return im


def paper(p,im):
    u=p.unit;pad=round(9*u);out=Image.new('RGBA',(im.width+pad*2,im.height));w,h=out.size;d=ImageDraw.Draw(out)
    d.polygon([(pad,0),(w,0),(w-pad,h*.22),(w,h*.40),(w-pad,h*.66),(w,h*.88),(w-pad,h),(0,h),(pad,h*.76),(0,h*.5),(pad,h*.27),(0,0)],fill=(245,241,225,180));out.alpha_composite(im,(pad,0));out.info['positions']=[(t,x+pad,f) for t,x,f in im.info.get('positions',[])];return out


def callout(p,e):
    u=p.unit;im=line(p,[dict(text=e['text'],role='sticker')],p.variant['scene_system']['tag_size'],'sticker',maxw=p.w*.33);extra=round(29*u);out=Image.new('RGBA',(im.width+extra,im.height));out.alpha_composite(im,(extra,0));d=ImageDraw.Draw(out);y=im.height/2
    for x in (4*u,15*u):
        for col,sw in [('#123022',7),('#64F39F',3)]:d.line((x,y-8*u,x+7*u,y,x,y+8*u),fill=col,width=max(1,round(sw*u)))
    return out


def identity_sprite(p,e):
    c=p.variant['scene_system'];u=p.unit;k=c['kind']
    if k=='tech':
        rows=[]
        for value,size,fg,bg in [(e['detail'],17,'#CFFAFF','#344FAD'),(e['name'],25,'#2747AD','#B1F0EE')]:
            f=p.font(size,'sticker');w=round((size+10)*u);step=round((size+3)*u);im=Image.new('RGBA',(w,step*len(value)+round(10*u)),bg);d=ImageDraw.Draw(im)
            for i,ch in enumerate(value):d.text((w/2,round(5*u)+i*step),ch,font=f,anchor='mt',fill=fg)
            rows.append(im)
        out=Image.new('RGBA',(sum(i.width for i in rows)+round(6*u),max(i.height for i in rows)));out.alpha_composite(rows[0]);out.alpha_composite(rows[1],(rows[0].width+round(6*u),0));return out
    lines=[line(p,[dict(text=e['detail'],role='sticker')],18,'sticker',maxw=p.w*.38),line(p,[dict(text=e['name'],role='sticker')],23,'sticker',maxw=p.w*.35)]
    im=stack(lines,-round(12*u));w=im.width+round(18*u);h=im.height;out=Image.new('RGBA',(w,h));d=ImageDraw.Draw(out);d.polygon([(12*u,0),(w,0),(w-12*u,h*.66),(0,h*.66)],fill='#234BB0');d.polygon([(12*u,h*.67),(w-12*u,h*.67),(w-22*u,h),(0,h)],fill='#4DA7D0');out.alpha_composite(im,(round(8*u),0));return out


def layout(p):
    from template_scenes import _box,texts
    c=p.variant['scene_system'];k=c['kind'];u=p.unit;entries=[]
    def add(im,x,y,a,b,role,animation='fade',**kw):
        x=round(x);y=round(y);env=round(10*u) if animation in ('soft','label') else 0
        entries.append(dict(image=im,x=x,y=y,start=a,end=b,role=role,animation=animation,box=_box(im,x,y,env),**kw))
    ti=title(p)
    if ti:add(ti,(p.w-ti.width)/2,p.h*c['title_y']-ti.height/2,0,min(p.p['duration'],p.p.get('title_duration',c['title_duration'])),'title')
    rail=None
    if k=='tech':
        rail=tech_rail(p);rx=(p.w-rail.width)/2;ry=p.h*c['caption_y']-rail.height/2
        add(rail,rx,ry,0,p.p['duration'],'caption_surface','steady',layer_id='tech-rail')
    translations={e['phrase_id']:e for e in p.p.get('scene_translations',[])}
    for g in p.p['scene_captions']:
        blocks=[]
        for e in g['phrases']:
            mode=e.get('mode','compact' if k=='green' else 'normal');runs=e.get('runs') or [dict(text=texts(e),role='body')]
            if k=='green' and mode=='compact':runs=[dict(text=texts(e),role='body')]
            im=line(p,runs,c['body_size'],'body',mode,p.w*(.75 if k=='tech' else .82 if k=='science' and mode=='paper' else .86))
            if k=='science' and mode=='paper':im=paper(p,im)
            im=pointer_sprite(p,e,im)
            en=None
            if e['id'] in translations:
                rows,size=wrap_text(p,translations[e['id']]['text'],c['translation_size'],p.w*.82-26*u)
                en=stack([line(p,[dict(text=t)],size,'translation',maxw=p.w*.82) for t in rows],-round(12*u))
            blocks.append((e,im,en))
        inner=-round(10*u);gap=round(22*u) if k=='green' else round(3*u);total=sum(im.height+(en.height+inner if en else 0) for _,im,en in blocks)+gap*(len(blocks)-1);y=p.h*c['caption_y']-total/2
        for j,(e,im,en) in enumerate(blocks):
            if k=='tech':
                im=im.crop(im.getbbox())
                if im.height>rail.height-22*u:raise ValueError('Tech text exceeds rail height')
                add(im,(p.w-im.width)/2,ry+(rail.height-im.height)/2-3*u,e['start'],e['end'],'caption','steady',parent='tech-rail')
            else:
                x=p.w*.075 if len(blocks)>1 and j==0 else p.w*.925-im.width if len(blocks)>1 else (p.w-im.width)/2
                add(im,x,y,e['start'],e['end'],'caption','soft' if k=='green' and e.get('mode')=='display' else 'pop' if k=='shine' else 'fade')
            if en:
                te=translations[e['id']];add(en,(p.w-en.width)/2,y+im.height+inner,te['start'],te['end'],'translation')
            y+=im.height+(en.height+inner if en else 0)+gap
    for e in p.p.get('scene_tags',[]):
        if k=='green':im=callout(p,e)
        elif e.get('orientation')=='vertical':
            im=stack([line(p,[dict(text=t,role='sticker')],c['tag_size'],'sticker',maxw=p.w*.25) for t in e['text']],-round(15*u));im=im.rotate(-12 if e.get('side','right')=='right' else 12,Image.Resampling.BICUBIC,expand=True)
        else:im=line(p,[dict(text=e['text'],role='sticker')],c['tag_size'],'sticker',maxw=p.w*.4)
        if e.get('icon')=='bulb':
            icon=bulb(u);out=Image.new('RGBA',(im.width+icon.width,max(im.height,icon.height)));out.alpha_composite(icon,(0,(out.height-icon.height)//2));out.alpha_composite(im,(icon.width,(out.height-im.height)//2));im=out
        x=p.w*.95-im.width if e.get('side','right')=='right' else p.w*.05
        add(im,x,p.h*c['tag_y']-im.height/2,e['start'],e['end'],'tag','label' if k!='shine' else 'pop')
    for e in p.p.get('scene_callouts',[]):
        im=callout(p,e);x=p.w*.95-im.width if e.get('side','right')=='right' else p.w*.05;y=p.h*(c['callout_y']+e['slot']*c['callout_step'])-im.height/2
        add(im,x,y,e['start'],e['end'],'callout','label')
    for e in p.p.get('scene_identity',[]):
        im=identity_sprite(p,e);add(im,p.w*e['x'],p.h*e['y'],e['start'],e['end'],'identity','fade')
    return entries
