"""Five sample-led designs, not palette variants of the first three.
Deterministic text/paper/annotation rendering. Fonts and curves are substitutes.
"""
import math
from PIL import Image, ImageDraw

KINDS={'white','redyellow','variety','ink','latte'}
MODES={'white':{'normal'}, 'redyellow':{'normal','display','lead'},
       'variety':{'normal','display','small'},'ink':{'normal','paper'},
       'latte':{'normal','display'}}


def validate(p):
    from template_scenes import cfg,interval
    kind=cfg(p)['kind']
    surface=p.p.get('scene_title_surface','none')
    if surface not in ('none','paper') or surface=='paper' and kind!='ink':raise ValueError('Title surface is only an explicit ink paper adaptation')
    for g in p.p['scene_captions']:
        for e in g['phrases']:
            if e.get('mode','normal') not in MODES[kind]:raise ValueError('Phrase mode unsupported by selected template')
            if e.get('color','normal') not in ('normal','yellow','mint','pink'):raise ValueError('Unknown bounded palette state')
            if e.get('color','normal')!='normal' and kind!='latte':raise ValueError('Color state belongs only to latte')
    notes=p.p.get('scene_notes',[])
    if notes and kind!='redyellow':raise ValueError('Persistent notes belong to redyellow only')
    previous={}
    for e in notes:
        a,b=interval(e,p.p['duration']);slot=e.get('slot')
        if type(slot) is not int or not 0<=slot<=2:raise ValueError('Note requires slot 0..2')
        if not isinstance(e.get('text'),str) or not 1<=len(e['text'])<=7 or not str(e.get('reason','')).strip():raise ValueError('Note requires short text and semantic reason')
        if a<previous.get(slot,0):raise ValueError('Same note slot overlaps')
        previous[slot]=b
    for e in p.p.get('scene_canvas',[]):
        if e['kind']=='inset':
            scale=e.get('scale',.86)
            if isinstance(scale,bool) or not isinstance(scale,(int,float)) or not math.isfinite(scale) or not .7<=scale<=.94:raise ValueError('Inset scale outside design range')
            if not str(e.get('reason','')).strip():raise ValueError('Inset requires framing reason')
        if kind=='latte' and e.get('background','#FCF9DD')!='#FCF9DD':raise ValueError('Latte canvas uses fixed cream, not arbitrary recoloring')
    if p.p.get('scene_takeover') and kind!='redyellow':raise ValueError('Phrase takeover is redyellow-only')
    ornaments=p.p.get('scene_ornaments',[])
    if not isinstance(ornaments,list) or len(ornaments)>8:raise ValueError('B2 ornaments must be a bounded list')
    for e in ornaments:
        interval(e,p.p['duration'])
        if (kind,e.get('kind')) not in (('latte','cursor'),('variety','hearts')):
            raise ValueError('Ornament kind unsupported by selected B2 template')
        if not str(e.get('reason','')).strip():raise ValueError('Ornament requires semantic reason')
        if any(not isinstance(e.get(v),(int,float)) or isinstance(e.get(v),bool) or not math.isfinite(e[v]) or not .08<=e[v]<=.92 for v in ('x','y')):
            raise ValueError('Ornament anchor outside safe area')
        if e['end']-e['start']>1.5:raise ValueError('Ornament lasts too long')
    if kind in ('white','ink') and p.p.get('scene_tags'):raise ValueError('This restrained design does not add arbitrary tags')


def text(p,text,role,size,style,fill=None,tracking=0,maxw=None):
    """Ink bounds include all outlines/offsets; bounded fitting never below 72%."""
    u=p.unit;pad=math.ceil(17*u);maxw=maxw or p.w*.88
    if not text.strip():raise ValueError('Empty B2 text')
    for factor in (1,.96,.92,.88,.84,.8,.76,.72):
        f=p.font(size*factor,role)
        chunks=list(text) if tracking else [text]
        width=sum(f.getlength(x) for x in chunks)+max(0,len(chunks)-1)*tracking*u
        if width+2*pad<=maxw:break
    else:raise ValueError('B2 phrase too long: split semantically, not below 72%')
    boxes=[f.getbbox(t,anchor='ls') for t in chunks];asc=max(-b[1] for b in boxes);desc=max(b[3] for b in boxes)
    im=Image.new('RGBA',(math.ceil(width)+2*pad,asc+desc+2*pad));d=ImageDraw.Draw(im)
    x=pad
    for ch in chunks:
        def ink(dx,dy,col,sw=0,edge=None):
            d.text((x+dx*u,pad+asc+dy*u),ch,font=f,anchor='ls',fill=col,stroke_width=max(0,round(sw*u)),stroke_fill=edge or col)
        if style=='plain':ink(1,2,'#161616',.6);ink(0,0,fill or '#FFFFFF')
        elif style=='brush':ink(0,0,fill or '#17201B')
        elif style=='hand':ink(1,1,'#454139',.25);ink(0,0,fill or '#FFFFFF')
        elif style=='red':ink(2,3,'#2F1719',1.5);ink(0,0,fill or '#E34B65',.6,'#451E27')
        elif style=='gold':ink(2,3,'#3F321F',1);ink(0,0,fill or '#F0D366')
        elif style=='boldwhite':ink(2,3,'#312824',3);ink(0,0,fill or '#FFFFFF',1,'#393230')
        elif style=='bubble':
            ink(0,2,'#172318',8);ink(0,0,'#EEFFE8',5.5);ink(0,0,fill or '#FFFFFF',2.6,'#161616')
        elif style=='bubblepink':
            ink(0,2,'#271720',8);ink(0,0,'#FFD4EB',5.5);ink(0,0,fill or '#FFFFFF',2.6,'#19161A')
        elif style=='latte':
            ink(3,4,'#655C4B',2.4);ink(0,0,fill or '#FFFDF2',2.2,'#26251E')
        else:raise ValueError('Unknown B2 text style')
        x+=f.getlength(ch)+tracking*u
    return im


def plate(p,im,kind):
    u=p.unit
    if kind=='dark':
        # Tight subtle dark-backed lead, not a full-width card.
        b=im.getchannel('A').getbbox();im=im.crop((max(0,b[0]-5),max(0,b[1]-4),min(im.width,b[2]+5),min(im.height,b[3]+4)))
        bg=Image.new('RGBA',im.size,(16,17,16,170));bg.alpha_composite(im);return bg
    w=max(im.width+round(16*u),round(p.w*.72));h=im.height+round(5*u)
    out=Image.new('RGBA',(w,h));d=ImageDraw.Draw(out)
    d.rectangle((1,2,w-2,h-3),fill='#FAF9EC',outline='#9A9F94',width=max(1,round(u)))
    for x in (8*u,w-10*u):d.rectangle((x,h*.45,x+3*u,h*.45+3*u),fill='#364139')
    out.alpha_composite(im,((w-im.width)//2,(h-im.height)//2));return out


def phrase(p,e,index=0):
    from template_scenes import cfg,texts
    k=cfg(p)['kind'];mode=e.get('mode','normal');value=texts(e)
    if k=='white':
        im=text(p,value,'body',39 if index==0 else 44,'plain',maxw=p.w*.82)
        return plate(p,im,'dark') if index==0 else im
    if k=='redyellow':return text(p,value,'keyword' if mode!='normal' else 'body',74 if mode=='display' else 65 if mode=='lead' else 58, 'red' if mode=='display' else 'gold' if mode=='lead' else 'boldwhite')
    if k=='variety':
        size=86 if mode=='display' else 35 if mode=='small' else 59
        im=text(p,value,'keyword' if mode=='display' else 'body',size,'plain' if mode=='small' else 'bubble' if mode=='display' else 'bubblepink')
        return im if mode in ('display','small') else im.rotate(5,resample=Image.Resampling.BICUBIC,expand=True)
    if k=='ink':
        im=text(p,value,'body',30 if mode=='paper' else 40,'brush' if mode=='paper' else 'hand',tracking=2,maxw=p.w*.84)
        return plate(p,im,'paper') if mode=='paper' else im
    palette={'normal':'#FFFDF2','yellow':'#F1F09B','mint':'#B7EEE7','pink':'#F4B5C2'}
    return text(p,value,'keyword' if mode=='display' else 'body',72 if mode=='display' else 58,'latte',fill=palette[e.get('color','normal')],tracking=5,maxw=p.w*.89)


def title(p):
    from template_scenes import cfg
    k=cfg(p)['kind'];lines=p.p.get('scene_title_lines',[])
    if not lines:return None
    sizes={'white':(59,43),'redyellow':(58,43),'variety':(59,46),'ink':(67,57),'latte':(54,48)}
    ims=[]
    for i,line in enumerate(lines):
        style={'white':'boldwhite' if i==0 else 'plain','redyellow':'gold','variety':'bubblepink','ink':'brush','latte':'latte'}[k]
        ims.append(text(p,line,'body' if k=='white' and i>0 else 'title',sizes[k][min(i,1)],style,fill='#ECEC99' if k=='latte' and i==0 else None,tracking=2 if k=='ink' else 1 if k=='latte' else 0,maxw=p.w*.91))
    gap=round(-13*p.unit);w=max(i.width for i in ims);h=sum(i.height for i in ims)+gap*(len(ims)-1)
    out=Image.new('RGBA',(w,h));y=0
    for im in ims:
        x=0 if k in ('white','ink') else (w-im.width)//2
        out.alpha_composite(im,(x,y));y+=im.height+gap
    if k=='ink':
        # Original red seal mark, not a sampled official seal or generated text.
        d=ImageDraw.Draw(out);u=p.unit;d.rectangle((3*u,h*.52,11*u,h*.52+20*u),fill='#A23B37')
    if k=='ink' and p.p.get('scene_title_surface')=='paper':
        paper=Image.new('RGBA',out.size,'#F6F3E5')
        paper.alpha_composite(out);out=paper
    return out


def ornament(p,kind):
    """Small original vector-like marks; no sampled official sprite or emoji."""
    u=p.unit; n=max(24,round(58*u)); im=Image.new('RGBA',(n,n));d=ImageDraw.Draw(im)
    if kind=='cursor':
        q=n/58; outline=max(2,round(3*u))
        pts=[(9*q,7*q),(11*q,47*q),(22*q,36*q),(30*q,51*q),(39*q,47*q),(30*q,31*q),(46*q,30*q)]
        d.polygon(pts,fill='#FFFDF1');d.line(pts+[pts[0]],fill='#29251E',width=outline,joint='curve')
        d.arc((33*q,5*q,54*q,26*q),215,295,fill='#E0B755',width=max(2,round(3*u)))
    else:
        def heart(cx,cy,r,color):
            d.ellipse((cx-r,cy-r*.85,cx,cy+r*.25),fill=color)
            d.ellipse((cx,cy-r*.85,cx+r,cy+r*.25),fill=color)
            d.polygon([(cx-r,cy),(cx+r,cy),(cx,cy+r*1.3)],fill=color)
        heart(n*.52,n*.52,n*.21,'#F375AC');heart(n*.23,n*.23,n*.09,'#F6A6C9')
    return im


def layout(p):
    from template_scenes import cfg,_box
    c=cfg(p);k=c['kind'];u=p.unit;entries=[]
    def add(im,x,y,a,b,role,animation='fade'):
        x=round(x);y=round(y);pad=round(14*u) if animation=='heart_float' else round(10*u) if animation in ('soft','label') else 0
        entries.append({'image':im,'x':x,'y':y,'start':a,'end':b,'role':role,'animation':animation,'box':_box(im,x,y,pad)})
    ti=title(p)
    if ti:
        x=22*u if k=='white' else (p.w-ti.width)/2
        add(ti,x,p.h*c['title_y']-ti.height/2,0,min(p.p['duration'],p.p.get('title_duration',c['title_duration'])),'title')
    for g in p.p['scene_captions']:
        ims=[phrase(p,e,j) for j,e in enumerate(g['phrases'])];gap=round(3*u)
        total=sum(i.height for i in ims)+gap*(len(ims)-1);top=p.h*c['caption_y']-total/2
        for j,(e,im) in enumerate(zip(g['phrases'],ims)):
            if k=='white':x=p.w*.18 if j==0 else p.w*.29;x=min(x,p.w*.94-im.width)
            elif k=='latte' and len(ims)==2:x=p.w*.10 if j==0 else p.w*.90-im.width
            else:x=(p.w-im.width)/2
            # Red-yellow takeover is an authored, short crossfade on one anchor, not stacked copy.
            takeover=k=='redyellow' and p.p.get('scene_takeover') and len(ims)==2
            end=min(e['end'],g['phrases'][1]['start']+.16) if takeover and j==0 else e['end']
            if takeover: top=p.h*c['caption_y']-im.height/2
            animation=('ink_write' if k=='ink' and e.get('mode','normal')=='normal' else
                       'pop' if k=='variety' and e.get('mode')!='small' else
                       'soft' if k in ('redyellow','latte') else 'fade')
            add(im,x,top,e['start'],end,'caption',animation)
            if not takeover:top+=im.height+gap
    for e in p.p.get('scene_tags',[]):
        style={'redyellow':'gold','variety':'bubblepink','latte':'latte'}[k]
        im=text(p,e['text'],'sticker',c['tag_size'],style,maxw=p.w*.38)
        if k=='latte':
            d=ImageDraw.Draw(im);d.line((8*u,im.height*.28,3*u,im.height*.65),fill='#E8EB8E',width=max(1,round(2*u)))
        cx=c['tag_x'] if e.get('side','right')=='right' else 1-c['tag_x']
        x=min(p.w-24*u-im.width,max(24*u,p.w*cx-im.width/2))
        add(im,x,p.h*c['tag_y']-im.height/2,e['start'],e['end'],'tag','label')
    for e in p.p.get('scene_notes',[]):
        im=text(p,'* '+e['text'],'sticker',24,'gold',maxw=p.w*.24)
        d=ImageDraw.Draw(im);d.line((12*u,im.height-12*u,im.width-12*u,im.height-12*u),fill='#DEBF52',width=max(1,round(u)))
        add(im,p.w*.03,p.h*.55+e['slot']*47*u,e['start'],e['end'],'note','fade')
    for e in p.p.get('scene_ornaments',[]):
        im=ornament(p,e['kind']);x=p.w*e['x']-im.width/2;y=p.h*e['y']-im.height/2
        add(im,x,y,e['start'],e['end'],'ornament','cursor_tap' if e['kind']=='cursor' else 'heart_float')
    return entries
