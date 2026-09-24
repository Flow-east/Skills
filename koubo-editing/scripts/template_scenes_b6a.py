"""B6a reference-led yellow/white and three playful designs.
Only licensed type and deterministic original geometry are used; product stickers from references are not copied.
"""
import math,random,hashlib
from PIL import Image,ImageDraw
from template_scenes_b3b import stack
KINDS={'cleanwhite','waxcute','qqcute','energycartoon'}
MODES={'cleanwhite':{'normal','display'},'waxcute':{'normal','display'},'qqcute':{'normal','hand'},'energycartoon':{'normal','arc'}}
SYMBOLS={'star','heart','arrow','burst','exclaim'}

def validate(p):
    from template_scenes import texts,interval
    k=p.variant['scene_system']['kind'];ids={}
    if any(p.p.get(x) for x in ('scene_notes','scene_highlights','scene_title_surface','scene_identity','scene_accents','scene_media','scene_callouts')):raise ValueError('Unsupported B6a auxiliary layer')
    for g in p.p['scene_captions']:
        for e in g['phrases']:
            ident=e.get('id')
            if not isinstance(ident,str) or not ident or ident in ids:raise ValueError('B6a requires unique nonempty phrase ids')
            ids[ident]=e
            if e.get('mode','normal') not in MODES[k]:raise ValueError('Unsupported B6a phrase mode')
            if any(e.get(x) for x in ('pointer','underline','reveal','reveal_times')) or e.get('color','normal')!='normal' or any('fill' in r for r in e.get('runs',[])):raise ValueError('B6a colors/decorations are contract controlled')
    for e in p.p.get('scene_tags',[]):
        a,b=interval(e,p.p['duration']);q=ids.get(e.get('phrase_id'))
        if not q or not q['start']<=a<b<=q['end'] or e.get('text') not in texts(q):raise ValueError('B6a tag must quote an active phrase')
        if e.get('orientation','horizontal')!='horizontal' or e.get('side','right') not in ('left','right'):raise ValueError('B6a tags are horizontal and side anchored')
        symbol=e.get('symbol')
        if symbol is not None and (symbol not in SYMBOLS or k=='cleanwhite'):raise ValueError('Unsupported semantic sticker symbol')
        if symbol and not str(e.get('symbol_reason','')).strip():raise ValueError('Sticker symbol requires explicit semantic reason')
        if any(x in e for x in ('asset','path','image','icon')):raise ValueError('B6a tags use original geometry, not undeclared sticker assets')
        if any(v in e for v in ('x','y')):
            from template_scenes import finite
            if not all(v in e and finite(e[v]) and 0<=e[v]<=1 for v in ('x','y')):raise ValueError('B6a explicit tag anchor needs normalized x/y pair')

def _metrics(p,runs,size,role,mode,maxw):
    k=p.variant['scene_system']['kind'];u=p.unit;pad=math.ceil((14 if k!='cleanwhite' else 10)*u);initial=size
    for _ in range(5):
        glyphs=[];x=0
        for r in runs:
            rr=r.get('role',role);mult=1.08 if rr=='keyword' and k in ('waxcute','qqcute') else 1
            f=p.font(size*mult,rr);text=r['text'];bb=f.getbbox(text,anchor='ls');glyphs.append((x,text,f,rr,bb));x+=f.getlength(text)
        left=min(x+b[0] for x,t,f,r,b in glyphs);right=max(x+b[2] for x,t,f,r,b in glyphs);top=min(b[1] for x,t,f,r,b in glyphs);bottom=max(b[3] for x,t,f,r,b in glyphs)
        w=math.ceil(right-left)+2*pad;h=bottom-top+2*pad
        if w<=maxw:return glyphs,left,top,w,h,pad
        size*=min(.96,(maxw-2*pad)/max(1,right-left))
        if size<initial*.70:raise ValueError('B6a text too long; split semantic phrases rather than shrink')
    raise ValueError('B6a text does not fit')

def line(p,runs,size,role='body',mode='normal',maxw=None):
    k=p.variant['scene_system']['kind'];u=p.unit;maxw=maxw or p.w*.86;glyphs,left,top,w,h,pad=_metrics(p,runs,size,role,mode,maxw);im=Image.new('RGBA',(w,h));d=ImageDraw.Draw(im)
    for x,text,f,rr,b in glyphs:
        pos=(pad+x-left,pad-top)
        if k=='cleanwhite':
            fill='#F4E86B' if rr=='keyword' else '#FFFFFF';edge='#29272A';sw=1.4 if mode=='display' else .6
        elif k=='waxcute':
            fill='#F5ABC9' if rr=='keyword' else '#FFF0A2';edge='#6F4B3A';sw=2.0
        elif k=='qqcute':
            fill='#F2BF32' if rr=='keyword' else '#F2A7D1';edge='#A04978';sw=1.6
        else:
            fill={'keyword':'#F45DA8','body':'#FFFFFF'}.get(rr,'#FFFFFF');edge='#191A1D';sw=2.7
        d.text((pos[0]+1.4*u,pos[1]+2*u),text,font=f,anchor='ls',fill=edge,stroke_width=max(1,round((sw+1.4)*u)),stroke_fill=edge)
        outer='#FFFFFF' if k in ('waxcute','qqcute') else edge
        d.text(pos,text,font=f,anchor='ls',fill=fill,stroke_width=max(1,round(sw*u)),stroke_fill=outer)
    if k=='cleanwhite' and mode=='display':
        extra=math.ceil(h*.08);im=im.transform((w+extra,h),Image.Transform.AFFINE,(1,.08,-extra,0,1,0),Image.Resampling.BICUBIC)
    return im

def panel(im,p,kind):
    u=p.unit;q=round(7*u);out=Image.new('RGBA',(im.width+2*q,im.height+2*q));d=ImageDraw.Draw(out)
    if kind=='cleanwhite':d.rectangle((0,q/2,out.width,out.height-q/2),fill=(248,246,238,155))
    elif kind=='waxcute':
        # Deterministic creamy cloud, not a copied sticker asset.
        d.rounded_rectangle((q,q,out.width-q,out.height-q),radius=round(13*u),fill=(255,248,225,235),outline='#DFA3C5',width=max(1,round(1.5*u)))
        for x in (q*1.2,out.width-q*1.2):d.ellipse((x-7*u,out.height-16*u,x+7*u,out.height-3*u),fill=(255,248,225,235),outline='#DFA3C5',width=max(1,round(u)))
    elif kind=='qqcute':d.rounded_rectangle((q/2,q/2,out.width-q/2,out.height-q/2),radius=round(12*u),fill=(255,248,220,72))
    else:d.rounded_rectangle((q,q,out.width-q,out.height-q),radius=round(5*u),fill=(255,255,255,228),outline='#17181B',width=max(1,round(2*u)))
    out.alpha_composite(im,(q,q));return out

def multicolor_glyphs(p,text,size,maxw,arc=False):
    u=p.unit;colors=['#F5D735','#F45DA8','#62B8F5','#64D890','#FFFFFF'];parts=[]
    for i,ch in enumerate(text):
        f=p.font(size,'title');bb=f.getbbox(ch);w=math.ceil(f.getlength(ch)+18*u);h=math.ceil((bb[3]-bb[1])+28*u);im=Image.new('RGBA',(w,h));d=ImageDraw.Draw(im)
        d.text((w/2+1.5*u,h/2+2*u),ch,font=f,anchor='mm',fill='#18191C',stroke_width=max(2,round(5*u)),stroke_fill='#18191C')
        d.text((w/2,h/2),ch,font=f,anchor='mm',fill=colors[i%len(colors)],stroke_width=max(1,round(1.5*u)),stroke_fill='#FFFFFF')
        angle=(-7,3,7,-3,5)[i%5];parts.append(im.rotate(angle,resample=Image.Resampling.BICUBIC,expand=True))
    overlap=round(10*u);w=sum(v.width for v in parts)-overlap*(len(parts)-1);h=max(v.height for v in parts)+round(16*u)
    if w>maxw:raise ValueError('Multicolor title too long; split title lines')
    out=Image.new('RGBA',(w,h));x=0
    for i,v in enumerate(parts):
        y=round((h-v.height)/2+(math.sin(i*math.pi/max(1,len(parts)-1))*-8*u if arc else 0));out.alpha_composite(v,(x,y));x+=v.width-overlap
    return out

def title(p):
    c=p.variant['scene_system'];k=c['kind'];u=p.unit;ims=[]
    for i,text in enumerate(p.p.get('scene_title_lines',[])):
        size=c['title_size'] if i==0 else c['subtitle_size']
        if k=='energycartoon':im=multicolor_glyphs(p,text,size,p.w*.86,True)
        else:
            rr='keyword' if k in ('waxcute','qqcute') and i==0 else 'body' if k in ('waxcute','qqcute') else 'title'
            im=line(p,[dict(text=text,role=rr)],size,'title','display' if k=='cleanwhite' else 'normal',p.w*.84)
            if k=='cleanwhite':im=panel(im,p,'cleanwhite')
            elif k=='waxcute':im=im.rotate(-2 if i%2==0 else 2,resample=Image.Resampling.BICUBIC,expand=True)
            elif k=='qqcute':im=panel(im,p,'qqcute')
        ims.append(im)
    return stack(ims,round((-2 if k=='qqcute' else 2)*u)) if ims else None

def _symbol(draw,kind,cx,cy,s,col,u):
    edge='#1B1C1F';w=max(1,round(2*u))
    if kind=='star':
        pts=[]
        for i in range(10):
            a=-math.pi/2+i*math.pi/5;r=s if i%2==0 else s*.44;pts.append((cx+math.cos(a)*r,cy+math.sin(a)*r))
        draw.polygon(pts,fill=col,outline=edge)
    elif kind=='heart':
        pts=[(cx,cy+s*.8),(cx-s,cy-s*.15),(cx-s*.7,cy-s*.75),(cx,cy-s*.3),(cx+s*.7,cy-s*.75),(cx+s,cy-s*.15)];draw.polygon(pts,fill=col,outline=edge)
    elif kind=='arrow':
        draw.polygon([(cx-s,cy-s*.25),(cx+s*.15,cy-s*.25),(cx+s*.15,cy-s*.65),(cx+s,cy),(cx+s*.15,cy+s*.65),(cx+s*.15,cy+s*.25),(cx-s,cy+s*.25)],fill=col,outline=edge)
    elif kind=='exclaim':
        draw.line((cx-s*.35,cy-s*.7,cx-s*.15,cy+s*.2),fill=col,width=max(2,round(7*u)));draw.ellipse((cx-s*.25,cy+s*.4,cx,cy+s*.65),fill=col,outline=edge);draw.line((cx+s*.25,cy-s*.9,cx+s*.5,cy+s*.1),fill=col,width=max(2,round(7*u)));draw.ellipse((cx+s*.4,cy+s*.35,cx+s*.7,cy+s*.65),fill=col,outline=edge)
    else:
        for i in range(8):
            a=i*math.pi/4;r1=s*.45;r2=s;draw.line((cx+math.cos(a)*r1,cy+math.sin(a)*r1,cx+math.cos(a)*r2,cy+math.sin(a)*r2),fill=col,width=w)
        draw.ellipse((cx-s*.3,cy-s*.3,cx+s*.3,cy+s*.3),fill=col,outline=edge)

def label(p,e):
    k=p.variant['scene_system']['kind'];u=p.unit;im=line(p,[dict(text=e['text'],role='sticker')],p.variant['scene_system']['tag_size'],'sticker','normal',p.w*.30)
    if k in ('waxcute','qqcute','energycartoon'):im=panel(im,p,k)
    symbol=e.get('symbol')
    if symbol:
        q=round(42*u);out=Image.new('RGBA',(im.width+q, max(im.height,round(46*u))));out.alpha_composite(im,(q,round((out.height-im.height)/2)));d=ImageDraw.Draw(out);_symbol(d,symbol,q*.48,out.height/2,11*u,{'waxcute':'#F4A5C9','qqcute':'#F2BF32','energycartoon':'#63C3F4'}[k],u);im=out
    if k=='cleanwhite':
        out=Image.new('RGBA',(im.width+round(9*u),im.height));d=ImageDraw.Draw(out);d.rectangle((0,im.height*.18,3*u,im.height*.82),fill='#F1E34F');out.alpha_composite(im,(round(9*u),0));im=out
    return im

def arc_line(p,runs,size,maxw):
    text=''.join(r['text'] for r in runs);roles=[]
    for r in runs:roles.extend([r.get('role','body')]*len(r['text']))
    u=p.unit;initial=size
    for _ in range(5):
        parts=[]
        for i,(ch,role) in enumerate(zip(text,roles)):
            im=line(p,[dict(text=ch,role=role)],size,role,'arc',maxw);parts.append(im.rotate((-4,1,4,-2)[i%4],resample=Image.Resampling.BICUBIC,expand=True))
        overlap=round(13*u);w=sum(v.width for v in parts)-overlap*(len(parts)-1);h=max(v.height for v in parts)+round(18*u)
        if w<=maxw:break
        size*=max(.80,maxw/w*.96)
        if size<initial*.70:raise ValueError('Arc phrase too long; split it')
    out=Image.new('RGBA',(w,h));x=0
    for i,v in enumerate(parts):
        y=round((h-v.height)/2-math.sin(i*math.pi/max(1,len(parts)-1))*7*u);out.alpha_composite(v,(x,y));x+=v.width-overlap
    return out

def layout(p):
    from template_scenes import texts,_box
    c=p.variant['scene_system'];k=c['kind'];u=p.unit;entries=[]
    def add(im,x,y,a,b,role,anim='fade'):
        x=round(x);y=round(y);env=round(11*u) if anim in ('pop','soft','label') else 0;entries.append(dict(image=im,x=x,y=y,start=a,end=b,role=role,animation=anim,box=_box(im,x,y,env)))
    ti=title(p)
    if ti:add(ti,(p.w-ti.width)/2,p.h*c['title_y']-ti.height/2,0,min(p.p['duration'],p.p.get('title_duration',c['title_duration'])),'title','pop' if k in ('waxcute','energycartoon') else 'fade')
    for g in p.p['scene_captions']:
        blocks=[]
        for e in g['phrases']:
            mode=e.get('mode','normal');runs=e.get('runs') or [dict(text=texts(e),role='body')];size=c['display_size'] if mode in ('display','arc') else c['compact_size'] if mode=='hand' else c['body_size']
            if k=='energycartoon' and mode=='arc':im=arc_line(p,runs,size,p.w*.84)
            else:im=line(p,runs,size,'body',mode,p.w*.84)
            if k=='cleanwhite' and mode=='normal':im=panel(im,p,'cleanwhite')
            if k=='qqcute' and mode=='hand':
                # Hand mode uses the sticker font plus small square marks, without fabricated wording.
                im=line(p,[dict(text=texts(e),role='sticker')],size,'sticker','normal',p.w*.78);q=round(12*u);out=Image.new('RGBA',(im.width+2*q,im.height));out.alpha_composite(im,(q,0));d=ImageDraw.Draw(out)
                for x,y in ((2*u,im.height*.3),(8*u,im.height*.65),(out.width-7*u,im.height*.4)):d.rectangle((x,y,x+4*u,y+4*u),fill='#F2A7D1');im=out
            blocks.append((e,im))
        gap=round(2*u);total=sum(im.height for e,im in blocks)+gap*(len(blocks)-1);y=p.h*c['caption_y']-total/2
        for i,(e,im) in enumerate(blocks):
            x=(p.w-im.width)/2
            if len(blocks)==2 and k in ('waxcute','qqcute','energycartoon'):x=p.w*.07 if i==0 else p.w*.93-im.width
            anim='soft' if k=='cleanwhite' else 'pop';add(im,x,y,e['start'],e['end'],'caption',anim);y+=im.height+gap
    for e in p.p.get('scene_tags',[]):
        im=label(p,e);x=p.w*e['x'] if 'x' in e else p.w*.94-im.width if e.get('side','right')=='right' else p.w*.06;y=p.h*e['y']-im.height/2 if 'y' in e else p.h*c['tag_y']-im.height/2;add(im,x,y,e['start'],e['end'],'tag','label')
    return entries
