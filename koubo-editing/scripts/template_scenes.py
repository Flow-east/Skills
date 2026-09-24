"""Sample-led scene templates. Output-clock phrase groups; video effects precede type.
Explicitly bounded independent designs, not a generic recolor engine. Fonts are
licensed substitutes. No automatic semantic decisions or official-engine claim.
"""
import json, math
from PIL import Image, ImageDraw, ImageFilter, ImageChops


def cfg(p): return p.variant.get('scene_system', {})
def finite(x): return isinstance(x,(float,int)) and not isinstance(x,bool) and math.isfinite(x)
def ease(x): return 1-(1-max(0.,min(1.,x)))**3

def interval(e, duration):
    a,b=e.get('start'),e.get('end')
    if not all(finite(v) for v in (a,b)) or not 0<=a<b<=duration:
        raise ValueError('Scene event needs finite OUTPUT start/end inside duration')
    return a,b


def texts(e): return ''.join(r['text'] for r in e.get('runs',[])) if e.get('runs') else e.get('text','')


def validate(p):
    c=cfg(p)
    if not c:return
    from template_contracts import validate_plan
    validate_plan(p)
    if c.get('version')!=1 or c.get('kind') not in ('pink','gold','grid','white','redyellow','variety','ink','latte','bired','biluxe','biblue','biyellow','luxury','brightyellow','navy','news','crispred','vividblue','shine','green','tech','science','neon','purple','warm','mono','elegantpink','promo','browngold','hotpink','orangeline','colorful','mint','tornred','deepbrown','ginger','blackyellow','verdant','ins','nostalgia','transyellow','tornedge','cleanwhite','waxcute','qqcute','energycartoon','floraltravel','magenta','lightbulb','redfestive','comicred','romance','emojiwhite','contrastpop'):raise ValueError('Unsupported scene template')
    if p.p.get('scene_time_space')!='output':raise ValueError('scene_time_space must explicitly be output')
    if not isinstance(p.p.get('scene_captions'),list) or not p.p['scene_captions']:raise ValueError('Scene template requires authored scene_captions; no silent legacy subtitle fallback')
    if p.p.get('english_map') or p.p.get('keyword_stickers') or p.p.get('caption_events') or p.p.get('viewport_events'):
        raise ValueError('Scene templates use scene_captions/scene_tags/scene_canvas; legacy layers cannot be mixed')
    if p.p.get('auto_semantics') or p.p.get('auto_viewport'):raise ValueError('Author scene events explicitly; disable legacy auto layers')
    for cl in p.p['clips']:
        if any(cl.get(k) for k in ('card','caption_events','viewport_events','stickers')):raise ValueError('Legacy clip overlays not supported in scene templates')
    duration=p.p['duration']; previous=0
    for g in p.p['scene_captions']:
        a,b=interval(g,duration)
        if a<previous:raise ValueError('Caption groups must not overlap or reorder')
        previous=b; phrases=g.get('phrases',[])
        limit=4 if c['kind']=='elegantpink' else 3 if c['kind'] in ('navy','neon','warm') else 2 if c['kind'] in ('pink','white','redyellow','variety','latte','bired','biluxe','luxury','crispred','vividblue','green','purple','browngold','orangeline','colorful','mint','tornred','ginger','blackyellow','verdant','transyellow','tornedge','waxcute','qqcute','energycartoon','floraltravel','magenta','lightbulb','redfestive','comicred','romance','emojiwhite','contrastpop') else 1
        if not 1<=len(phrases)<=limit:raise ValueError('Wrong phrase count for selected template layout')
        last=a
        for e in phrases:
            ea,eb=interval(e,duration)
            if not a<=ea<eb<=b or ea<last:raise ValueError('Phrase clocks must stay within group and enter in order')
            if not isinstance(texts(e),str) or not texts(e).strip():raise ValueError('Empty scene phrase')
            last=ea
            if e.get('symbol') not in (None,'cross') or e.get('symbol')=='cross' and c['kind']!='gold':raise ValueError('Phrase symbol unsupported in this template')
            if e.get('english'):raise ValueError('Bilingual scene layouts not implemented')
            for r in e.get('runs',[]):
                if not isinstance(r.get('text'),str) or not r['text'] or r.get('role','body') not in ('body','keyword'):raise ValueError('Invalid scene text run')
            if e.get('tone','normal') not in ('normal','warning'):raise ValueError('Unknown phrase tone')
    if c['kind'] in ('white','redyellow','variety','ink','latte'):
        from template_scenes_b2 import validate as validate_b2
        validate_b2(p)
    elif p.p.get('scene_notes'):
        raise ValueError('Persistent notes require redyellow template')
    from scene_bilingual import validate as validate_bilingual
    validate_bilingual(p)
    if c['kind'] in ('bired','biluxe','biblue'):
        from template_scenes_b3 import validate as validate_b3
        validate_b3(p)
    if c['kind'] in ('biyellow','luxury','brightyellow','navy','news','crispred','vividblue'):
        from template_scenes_b3b import validate as validate_b3b
        validate_b3b(p)
    if c['kind'] in ('neon','purple','warm','mono'):
        from template_scenes_b4b import validate as validate_b4b
        validate_b4b(p)
    if p.p.get('scene_accents') and c['kind'] not in ('elegantpink','promo','browngold','hotpink'):raise ValueError('Comic accents require declared B4c renderer')
    if p.p.get('scene_media') and c['kind']!='tornred':raise ValueError('Illustration cards require tornred renderer')
    if c['kind'] in ('cleanwhite','waxcute','qqcute','energycartoon'):
        from template_scenes_b6a import validate as validate_b6a
        validate_b6a(p)
    if c['kind'] in ('floraltravel','magenta','lightbulb','redfestive'):
        from template_scenes_b6b import validate as validate_b6b
        validate_b6b(p)
    if c['kind'] in ('comicred','romance','emojiwhite','contrastpop'):
        from template_scenes_b6c import validate as validate_b6c
        validate_b6c(p)
    if c['kind'] in ('ins','nostalgia','transyellow','tornedge'):
        from template_scenes_b5c import validate as validate_b5c
        validate_b5c(p)
    if c['kind'] in ('deepbrown','ginger','blackyellow','verdant'):
        from template_scenes_b5b import validate as validate_b5b
        validate_b5b(p)
    elif c['kind'] in ('orangeline','colorful','mint','tornred'):
        from template_scenes_b5a import validate as validate_b5a
        validate_b5a(p)
    elif c['kind'] in ('elegantpink','promo','browngold','hotpink'):
        from template_scenes_b4c import validate as validate_b4c
        validate_b4c(p)
    elif c['kind'] in ('shine','green','tech','science'):
        from template_scenes_b4 import validate as validate_b4
        validate_b4(p)
    elif p.p.get('scene_callouts') or p.p.get('scene_identity'):
        raise ValueError('B4 callout/identity layers require declared B4 template')
    # Typography must not silently drop/change the approved transcript.
    def canonical(text):
        out=[]
        for j,ch in enumerate(text):
            numeric_separator=ch in '.:,：' and 0<j<len(text)-1 and text[j-1].isdigit() and text[j+1].isdigit()
            if ch.isspace() or ch in '.,;:!?，。；：！？、' and not numeric_separator:continue
            out.append(ch)
        return ''.join(out)
    spoken=''.join(w['text'] for cl in p.p['clips'] for w in cl.get('words',[]))
    displayed=''.join(texts(e) for g in p.p['scene_captions'] for e in g['phrases'])
    if spoken and canonical(spoken)!=canonical(displayed):raise ValueError('Scene text differs from timed transcript; reconcile instead of silently dropping words')
    tags=p.p.get('scene_tags',[]);previous=0
    for e in tags:
        a,b=interval(e,duration)
        if a<previous:raise ValueError('Overlapping scene tags require a separate design')
        previous=b
        if not isinstance(e.get('text'),str) or not 1<=len(e['text'])<=10 or not str(e.get('reason','')).strip():raise ValueError('Tag requires short text and semantic reason')
        if e.get('side','right') not in ('left','right'):raise ValueError('Tag side must be a template slot')
        symbol=e.get('symbol')
        if c['kind'] in ('cleanwhite','waxcute','qqcute','energycartoon','floraltravel','magenta','lightbulb','redfestive','comicred','romance','emojiwhite','contrastpop'):
            if symbol not in (None,'star','heart','arrow','burst','exclaim'):raise ValueError('Symbol unsupported in this B6a template')
        elif symbol not in (None,'cross') or symbol=='cross' and c['kind']!='gold':raise ValueError('Symbol unsupported in this template')
    previous=0
    for e in p.p.get('scene_canvas',[]):
        a,b=interval(e,duration)
        if a<previous:raise ValueError('Overlapping canvas effects require authored composition; not supported')
        previous=b
        if e.get('kind') not in c['allowed_canvas']:raise ValueError('Canvas state not part of this template')
        if e['kind']=='vignette':
            if not finite(e.get('strength',.6)) or not 0<=e.get('strength',.6)<=.85:raise ValueError('Invalid vignette strength')
        if e['kind']=='circle':
            radius=e.get('radius',.39);center=e.get('center',[.5,.42])
            if not finite(radius) or not .15<=radius<=.48 or len(center)!=2 or not all(finite(v) and 0<=v<=1 for v in center):raise ValueError('Invalid circular viewport')
            rx=radius*p.w;cx,cy=center[0]*p.w,center[1]*p.h
            if cx-rx<0 or cx+rx>p.w or cy-rx<0 or cy+rx>p.h:raise ValueError('Circular viewport outside canvas')
            if not str(e.get('reason','')).strip():raise ValueError('Circle requires framing-review reason')
        if 'feather' in e and (c['kind'] not in ('verdant','transyellow','tornedge') or e['kind']!='circle' or not finite(e['feather']) or not .002<=e['feather']<=.04):raise ValueError('Feather requires declared B5 soft circle within supported radius')
        if e['kind']=='swipe' and b-a>.8:raise ValueError('Swipe interval must be <=0.8s')
    for r in p.p.get('protected_regions',[]):
        a,b=interval(dict(start=r.get('start',0),end=r.get('end',duration)),duration);box=r.get('box',[])
        if len(box)!=4 or not all(finite(x) and 0<=x<=1 for x in box) or not box[0]<box[2] or not box[1]<box[3]:raise ValueError('Invalid scene protected region')
    lines=p.p.get('scene_title_lines')
    if lines is not None and (not isinstance(lines,list) or not 1<=len(lines)<=c.get('title_max_lines',2) or any(not isinstance(x,str) or not x.strip() for x in lines)):
        raise ValueError('Author one or two scene_title_lines')
    if p.p.get('title') and not lines:raise ValueError('Scene title requires semantic scene_title_lines')
    td=p.p.get('title_duration',c['title_duration'])
    if not finite(td) or td<=0:raise ValueError('Invalid scene title duration')


def _glyphs(p,runs,sizes,factor,tracking=0):
    out=[];x=0
    for r in runs:
        role=r.get('role','body');f=p.font(sizes[role]*factor,role)
        chunks=list(r['text']) if tracking else [r['text']]
        for j,text in enumerate(chunks):
            if role=='title' and cfg(p)['kind']=='grid':
                scales=cfg(p).get('title_glyph_scales',[1]);f=p.font(sizes[role]*factor*scales[j%len(scales)],role)
            out.append((x,text,f,role,r.get('fill')));x+=f.getlength(text)+tracking*p.unit
    if tracking:x-=tracking*p.unit
    return out,x


def _ink(d,xy,text,font,kind,role,fill,u):
    x,y=xy
    def draw(dx,dy,ink,sw=0,edge=None):
        d.text((x+dx*u,y+dy*u),text,font=font,anchor='ls',fill=ink,stroke_width=max(0,round(sw*u)),stroke_fill=edge or ink)
    if kind=='pink':
        for offset in (4,3,2):draw(offset,offset,'#201A21',1)
        draw(0,0,fill,.4,'#382732')
    elif kind=='gold':
        if role=='title':
            for z in (5,4,3):draw(z,z,'#58452D',1.3)
            draw(0,0,fill,1,'#BA9D6B')
        else:
            draw(1.5,2,'#4B402D',5.0);draw(0,0,fill,3.1,'#FFF7D8');draw(0,0,fill)
    elif role in ('title','sticker'):
        draw(7,8,'#91EFD2',5.0);draw(4,5,'#9B61ED',5.0);draw(0,0,fill,4.0,'#100F19');draw(0,0,fill)
    else:draw(0,0,fill)


def text_sprite(p,runs,role='body',tone='normal',max_width=None,size=None):
    c=cfg(p);kind=c['kind'];u=p.unit
    runs=[dict(r,role=r.get('role',role)) for r in runs]
    sizes={'body':c['body_size'],'keyword':c['keyword_size'],'title':c['title_size'],'sticker':c['tag_size']}
    if size is not None:sizes={k:size for k in sizes}
    pad=round((13 if role in ('body','keyword') else 16)*u);maxw=max_width or p.w*.86
    tracking=1.0 if kind=='grid' and role=='title' else 0
    for factor in (1,.96,.92,.88,.84,.8,.76,.72):
        glyphs,width=_glyphs(p,runs,sizes,factor,tracking)
        if width+2*pad<=maxw:break
    else:raise ValueError('Scene phrase too long: split semantically instead of shrinking below 72%')
    ascent=max(-f.getbbox(text,anchor='ls')[1] for x,text,f,r,fill in glyphs)
    descent=max(f.getbbox(text,anchor='ls')[3] for x,text,f,r,fill in glyphs)
    im=Image.new('RGBA',(math.ceil(width)+2*pad,ascent+descent+2*pad));d=ImageDraw.Draw(im)
    for x,text,f,r,custom in glyphs:
        if kind=='pink':fill=('#F7E88C' if tone=='warning' else '#F3ABC9') if r in ('keyword','title','sticker') else '#FFFFFF'
        elif kind=='gold':fill='#FBE6B1' if r=='title' else '#50432E'
        else:fill='#F5FFF8' if r in ('title','sticker') else '#0C1112'
        _ink(d,(pad+x,pad+ascent),text,f,kind,r,custom or fill,u)
    return im


def grid_window(p,text):
    u=p.unit;w=round(p.w*.90);h=text.height+round(14*u);im=Image.new('RGBA',(w,h+round(13*u)));d=ImageDraw.Draw(im)
    d.rectangle((12*u,12*u,w-1,h+8*u),fill='#0D0C19')
    d.rectangle((10*u,10*u,w-5*u,h+5*u),fill='#B688EE')
    d.rectangle((5*u,6*u,w-9*u,h),fill='#EEFFF5',outline='#10111B',width=max(1,round(4*u)))
    for yy in range(round(12*u),int(h-3*u),max(3,round(6*u))):
        for xx in range(round(12*u),int(w-14*u),max(3,round(6*u))):d.ellipse((xx,yy,xx+u,yy+u),fill='#CFDCD9')
    im.alpha_composite(text,(round((w-text.width)/2),round((h-text.height)/2)))
    d.ellipse((0,0,23*u,23*u),fill='#BC86F4',outline='#11111A',width=max(1,round(3*u)))
    d.line((8*u,8*u,15*u,15*u),fill='#10101A',width=max(1,round(3*u)));d.line((8*u,15*u,15*u,8*u),fill='#10101A',width=max(1,round(3*u)))
    return im


def title_sprite(p):
    c=cfg(p);lines=p.p.get('scene_title_lines',[])
    if not lines:return None
    ims=[]
    for j,line in enumerate(lines):
        fill='#FFFFFF' if c['kind']=='pink' and j>0 else None
        ims.append(text_sprite(p,[dict(text=line,role='title',fill=fill)],'title',max_width=p.w*.90,size=c['title_size'] if j==0 or c['kind']!='pink' else c['title_size']*.58))
    gap=round(-8*p.unit);w=max(i.width for i in ims);h=sum(i.height for i in ims)+gap*(len(ims)-1)
    out=Image.new('RGBA',(w,h));y=0
    for im in ims:out.alpha_composite(im,((w-im.width)//2,y));y+=im.height+gap
    if c['kind']=='grid':
        d=ImageDraw.Draw(out);u=p.unit
        # Small original star accents; no sampled copyrighted stickers.
        for x,y in [(w*.19,12*u),(w*.77,h*.51)]:
            d.polygon([(x,y-6*u),(x+2*u,y-2*u),(x+7*u,y),(x+2*u,y+2*u),(x,y+7*u),(x-2*u,y+2*u),(x-6*u,y),(x-2*u,y-2*u)],fill='#D8EE77',outline='#10121B')
    return out


def tag_sprite(p,e):
    c=cfg(p);u=p.unit
    im=text_sprite(p,[dict(text=e['text'],role='sticker')],'sticker',tone=e.get('tone','normal'),max_width=p.w*.42)
    if c['kind']=='grid':
        bg=Image.new('RGBA',(im.width+round(12*u),im.height+round(12*u)));d=ImageDraw.Draw(bg)
        d.rectangle((bg.width*.43,bg.height-20*u,bg.width-4*u,bg.height-2*u),fill='#81E0B7');d.polygon([(bg.width*.6,bg.height-3*u),(bg.width*.6,bg.height+0*u),(bg.width*.65,bg.height-3*u)],fill='#81E0B7');d.line((4*u,bg.height*.53,bg.width*.2,bg.height*.53),fill='#8ADDBF',width=max(1,round(5*u)));bg.alpha_composite(im,(0,0));im=bg
    elif e.get('symbol')=='cross':im=add_cross(p,im)
    return im


def add_cross(p,im):
    u=p.unit;extra=round(42*u);out=Image.new('RGBA',(im.width+extra,im.height));out.alpha_composite(im,(0,0));d=ImageDraw.Draw(out);x=im.width+extra/2-4*u;y=im.height/2
    for col,sw in [('#302C2A',14),('#FF6864',10)]:
        d.line((x-12*u,y-12*u,x+12*u,y+12*u),fill=col,width=max(1,round(sw*u)));d.line((x-12*u,y+12*u,x+12*u,y-12*u),fill=col,width=max(1,round(sw*u)))
    return out


def phrase_sprite(p,e):
    im=text_sprite(p,e.get('runs') or [dict(text=e['text'])],tone=e.get('tone','normal'),max_width=p.w*(.84 if cfg(p)['kind']=='grid' else .86))
    if e.get('symbol')=='cross':im=add_cross(p,im)
    return grid_window(p,im) if cfg(p)['kind']=='grid' else im


def _box(im,x,y,pad=0):
    b=im.getchannel('A').getbbox() or (0,0,im.width,im.height)
    return (x+b[0]-pad,y+b[1]-pad,x+b[2]+pad,y+b[3]+pad)
def _overlap(a,b):return a[0]<b[2] and b[0]<a[2] and a[1]<b[3] and b[1]<a[3]


def layout(p):
    if cfg(p)['kind'] in ('cleanwhite','waxcute','qqcute','energycartoon'):
        from template_scenes_b6a import layout as layout_b6a
        if not hasattr(p,'scene_layout'):p.scene_layout=layout_b6a(p)
        return p.scene_layout
    if cfg(p)['kind'] in ('floraltravel','magenta','lightbulb','redfestive'):
        from template_scenes_b6b import layout as layout_b6b
        if not hasattr(p,'scene_layout'):p.scene_layout=layout_b6b(p)
        return p.scene_layout
    if cfg(p)['kind'] in ('comicred','romance','emojiwhite','contrastpop'):
        from template_scenes_b6c import layout as layout_b6c
        if not hasattr(p,'scene_layout'):p.scene_layout=layout_b6c(p)
        return p.scene_layout
    if cfg(p)['kind'] in ('ins','nostalgia','transyellow','tornedge'):
        from template_scenes_b5c import layout as layout_b5c
        if not hasattr(p,'scene_layout'):p.scene_layout=layout_b5c(p)
        return p.scene_layout
    if cfg(p)['kind'] in ('deepbrown','ginger','blackyellow','verdant'):
        from template_scenes_b5b import layout as layout_b5b
        if not hasattr(p,'scene_layout'):p.scene_layout=layout_b5b(p)
        return p.scene_layout
    if cfg(p)['kind'] in ('orangeline','colorful','mint','tornred'):
        from template_scenes_b5a import layout as layout_b5a
        if not hasattr(p,'scene_layout'):p.scene_layout=layout_b5a(p)
        return p.scene_layout
    if cfg(p).get('kind') in ('elegantpink','promo','browngold','hotpink'):
        from template_scenes_b4c import layout as layout_b4c
        if not hasattr(p,'scene_layout'):p.scene_layout=layout_b4c(p)
        return p.scene_layout
    if cfg(p).get('kind') in ('neon','purple','warm','mono'):
        from template_scenes_b4b import layout as layout_b4b
        if not hasattr(p,'scene_layout'):p.scene_layout=layout_b4b(p)
        return p.scene_layout
    if cfg(p).get('kind') in ('shine','green','tech','science'):
        from template_scenes_b4 import layout as layout_b4
        if not hasattr(p,'scene_layout'):p.scene_layout=layout_b4(p)
        return p.scene_layout
    if cfg(p).get('kind') in ('biyellow','luxury','brightyellow','navy','news','crispred','vividblue'):
        from template_scenes_b3b import layout as layout_b3b
        key=('b3b_layout',)
        if key not in p.layers:p.layers[key]=layout_b3b(p)
        return p.layers[key]
    if hasattr(p,'scene_layout'):return p.scene_layout
    c=cfg(p);u=p.unit;entries=[]
    if c['kind'] in ('white','redyellow','variety','ink','latte'):
        from template_scenes_b2 import layout as b2_layout
        p.scene_layout=b2_layout(p)
        return p.scene_layout
    if c['kind'] in ('bired','biluxe','biblue'):
        from template_scenes_b3 import layout as b3_layout
        p.scene_layout=b3_layout(p)
        return p.scene_layout
    def add(im,x,y,start,end,role,animation):
        env=round(10*u) if animation in ('soft','label') else 0
        entries.append(dict(image=im,x=round(x),y=round(y),start=start,end=end,role=role,animation=animation,box=_box(im,round(x),round(y),env)))
    title=title_sprite(p)
    if title is not None:add(title,(p.w-title.width)/2,p.h*c['title_y']-title.height/2,0,min(p.p['duration'],p.p.get('title_duration',c['title_duration'])),'title','fade')
    for g in p.p['scene_captions']:
        phrases=g['phrases'];ims=[]
        for e in phrases:
            im=phrase_sprite(p,e)
            ims.append(im)
        gap=round(2*u);total=sum(im.height for im in ims)+gap*(len(ims)-1)
        top=p.h*c['caption_y']-total/2;gw=min(p.w*.90,max(im.width for im in ims)+round(38*u))
        for k,(e,im) in enumerate(zip(phrases,ims)):
            x=(p.w-im.width)/2 if len(ims)==1 else (p.w-gw)/2 if k==0 else (p.w+gw)/2-im.width
            add(im,x,top,e['start'],e['end'],'caption','soft' if c['kind']=='pink' else 'fade');top+=im.height+gap
    for e in p.p.get('scene_tags',[]):
        im=tag_sprite(p,e);cx=c['tag_x'] if e.get('side','right')=='right' else 1-c['tag_x']
        x=min(p.w-24*u-im.width,max(24*u,p.w*cx-im.width/2));y=p.h*c['tag_y']-im.height/2
        add(im,x,y,e['start'],e['end'],'tag','label' if c['kind']=='grid' else 'fade')
    p.scene_layout=entries;return entries


def audit_layout(p):
    entries=layout(p);margin=12*p.unit;report=[]
    # Only tech's verified rail can intentionally contain a child caption.
    parents={e.get('layer_id'):e for e in entries if e.get('layer_id')}
    for e in entries:
        if e.get('parent'):
            parent=parents.get(e['parent'])
            if cfg(p).get('kind')!='tech' or e['role']!='caption' or not parent or parent['role']!='caption_surface' or not parent['start']<=e['start']<e['end']<=parent['end']:
                raise ValueError('Unsupported scene containment relationship')
            a,b=e['box'],parent['box']
            if not (b[0]<=a[0] and b[1]<=a[1] and a[2]<=b[2] and a[3]<=b[3]):raise ValueError('Child caption escapes tech rail')
    for e in entries:
        b=e['box']
        if b[0]<margin or b[1]<margin or b[2]>p.w-margin or b[3]>p.h-margin:raise ValueError(f'Scene {e["role"]} animation envelope outside safe canvas: {b}')
        for r in p.p.get('protected_regions',[]):
            if min(e['end'],r.get('end',p.p['duration']))>max(e['start'],r.get('start',0)):
                rb=tuple(v*(p.w if j%2==0 else p.h) for j,v in enumerate(r['box']))
                if _overlap(b,rb):raise ValueError(f'Scene {e["role"]} covers authored protected region; adjust this template layout')
        report.append({k:e[k] for k in ('role','start','end','box','animation')})
    for j,e in enumerate(entries):
        for other in entries[j+1:]:
            if (e.get('parent') and e['parent']==other.get('layer_id')) or (other.get('parent') and other['parent']==e.get('layer_id')):continue
            overlap=min(e['end'],other['end'])-max(e['start'],other['start'])
            if overlap>0 and _overlap(e['box'],other['box']):
                takeover=cfg(p).get('kind')=='redyellow' and p.p.get('scene_takeover') and e['role']==other['role']=='caption' and overlap<=.161 and e['start']!=other['start']
                if not takeover:raise ValueError('Scene typography layers collide; revise authored phrases/tag timing')
    return dict(version=1,template=p.variant['id'],time_space='output',passed=True,events=report,scope='Full animation envelopes; authored face regions, not automatic tracking or aesthetic acceptance')


def _style_backdrop(p, canvas, t):
    """Template-owned geometry under text; bounded, original, and screen-fixed.

    The A-batch revision opts in explicitly through ``style_surface``. Keeping
    the opt-in means historical fixtures and already-rendered non-A templates do
    not silently change merely because this helper exists.
    """
    if not p.p.get('style_surface'):
        return canvas
    k=cfg(p).get('kind'); u=p.unit; layer=Image.new('RGBA', canvas.size, (0,0,0,0)); d=ImageDraw.Draw(layer)
    if k=='bired':
        # restrained wine-red top rail keeps this template a poster, not a generic subtitle.
        d.rectangle((0,0,p.w,round(p.h*.205)),fill=(70,18,24,34))
        d.rectangle((round(p.w*.08),round(p.h*.205),round(p.w*.92),round(p.h*.209)),fill=(152,54,52,145))
    elif k=='biluxe':
        d.rectangle((0,0,p.w,round(p.h*.19)),fill=(255,255,250,38))
        d.line((round(p.w*.12),round(p.h*.198),round(p.w*.88),round(p.h*.198)),fill=(241,226,117,170),width=max(1,round(2*u)))
        for x,y,r in ((.82,.12,7),(.18,.17,4),(.73,.24,3)):
            cx,cy=round(p.w*x),round(p.h*y);d.line((cx-r*u,cy,cx+r*u,cy),fill=(255,255,255,150),width=max(1,round(u)));d.line((cx,cy-r*u,cx,cy+r*u),fill=(255,255,255,150),width=max(1,round(u)))
    elif k=='biblue':
        d.rectangle((0,0,p.w,round(p.h*.18)),fill=(204,238,235,80))
        d.rectangle((round(p.w*.06),round(p.h*.18),round(p.w*.94),round(p.h*.185)),fill=(90,210,199,190))
        d.rectangle((round(p.w*.90),round(p.h*.20),round(p.w*.94),round(p.h*.71)),fill=(90,210,199,80))
    elif k=='shine':
        y=round(p.h*.17);d.polygon([(round(p.w*.06),y),(round(p.w*.94),y-4*u),(round(p.w*.90),y+11*u),(round(p.w*.10),y+15*u)],fill=(255,229,73,50))
        d.rectangle((round(p.w*.08),round(p.h*.80),round(p.w*.92),round(p.h*.805)),fill=(254,222,60,120))
    elif k=='cleanwhite':
        d.rectangle((round(p.w*.05),round(p.h*.735),round(p.w*.95),round(p.h*.735+10*u)),fill=(255,255,255,45))
    elif k=='pink':
        d.ellipse((round(-.18*p.w),round(.03*p.h),round(.48*p.w),round(.46*p.h)),fill=(244,174,201,24))
        d.ellipse((round(.64*p.w),round(.52*p.h),round(1.18*p.w),round(1.08*p.h)),fill=(244,174,201,20))
    elif k=='gold':
        d.rectangle((round(p.w*.08),round(p.h*.70),round(p.w*.92),round(p.h*.88)),fill=(250,226,174,28))
        d.rectangle((round(p.w*.10),round(p.h*.70),round(p.w*.90),round(p.h*.705)),fill=(245,203,112,120))
    elif k=='green':
        d.rectangle((0,0,p.w,round(p.h*.20)),fill=(14,20,17,118))
        d.rectangle((round(p.w*.06),round(p.h*.205),round(p.w*.94),round(p.h*.247)),fill=(76,236,147,128))
        d.rectangle((round(p.w*.06),round(p.h*.77),round(p.w*.34),round(p.h*.775)),fill=(76,236,147,150))
    elif k=='biyellow':
        d.rectangle((0,0,p.w,round(p.h*.215)),fill=(12,13,12,110))
        d.rectangle((round(p.w*.06),round(p.h*.215),round(p.w*.94),round(p.h*.222)),fill=(255,220,36,200))
        d.rectangle((round(p.w*.08),round(p.h*.82),round(p.w*.92),round(p.h*.825)),fill=(255,220,36,145))
    elif k=='luxury':
        # Warm, restrained frame lines: a distinct luxury surface without a full-screen card.
        d.rectangle((round(p.w*.07),round(p.h*.12),round(p.w*.93),round(p.h*.123)),fill=(220,172,93,120))
        d.line((round(p.w*.12),round(p.h*.89),round(p.w*.88),round(p.h*.89)),fill=(243,194,112,105),width=max(1,round(2*u)))
        d.ellipse((round(p.w*.73),round(p.h*.04),round(p.w*1.12),round(p.h*.34)),fill=(132,55,45,30))
    elif k=='brightyellow':
        # Small yellow corner blocks and a sparse dot rhythm, not a generic tint.
        d.rectangle((0,0,round(p.w*.12),round(p.h*.055)),fill=(255,228,42,190))
        d.rectangle((round(p.w*.88),round(p.h*.055),p.w,round(p.h*.09)),fill=(255,228,42,150))
        for ix in range(4):
            for iy in range(3):
                cx=round(p.w*(.08+ix*.025));cy=round(p.h*(.16+iy*.018))
                d.ellipse((cx-u,cy-u,cx+u,cy+u),fill=(255,231,60,150))
    elif k=='navy':
        d.polygon([(0,round(p.h*.72)),(round(p.w*.31),round(p.h*.64)),(round(p.w*.55),p.h),(0,p.h)],fill=(20,48,82,105))
        d.line((round(p.w*.08),round(p.h*.205),round(p.w*.92),round(p.h*.205)),fill=(232,216,167,150),width=max(1,round(2*u)))
    elif k=='tech':
        d.polygon([(0,round(p.h*.24)),(round(p.w*.94),round(p.h*.10)),(p.w,round(p.h*.17)),(round(p.w*.05),round(p.h*.31))],fill=(33,99,198,48))
        d.line((round(p.w*.08),round(p.h*.77),round(p.w*.92),round(p.h*.62)),fill=(74,190,255,120),width=max(1,round(2*u)))
    elif k=='science':
        d.rectangle((round(p.w*.06),round(p.h*.19),round(p.w*.94),round(p.h*.194)),fill=(107,227,240,160))
        d.rectangle((round(p.w*.08),round(p.h*.86),round(p.w*.45),round(p.h*.866)),fill=(84,145,241,135))
        for x in (.12,.18,.24,.30):
            d.ellipse((round(p.w*x),round(p.h*.16),round(p.w*x)+2*u,round(p.h*.16)+2*u),fill=(155,245,255,170))
    elif k=='news':
        d.rectangle((0,round(p.h*.76),p.w,round(p.h*.765)),fill=(12,86,206,185))
        d.rectangle((round(p.w*.06),round(p.h*.82),round(p.w*.32),round(p.h*.827)),fill=(208,61,66,180))
        d.rectangle((round(p.w*.32),round(p.h*.82),round(p.w*.58),round(p.h*.827)),fill=(229,190,65,180))
    elif k=='orangeline':
        d.line((round(p.w*.08),round(p.h*.18),round(p.w*.84),round(p.h*.06)),fill=(255,143,54,155),width=max(1,round(3*u)))
        d.line((round(p.w*.15),round(p.h*.86),round(p.w*.88),round(p.h*.96)),fill=(255,164,72,120),width=max(1,round(2*u)))
        d.ellipse((round(-.18*p.w),round(p.h*.58),round(.34*p.w),round(1.12*p.h)),fill=(249,144,62,28))
    elif k=='crispred':
        col=(154,47,68,145);w=max(1,round(3*u))
        d.line((round(p.w*.06),round(p.h*.18),round(p.w*.25),round(p.h*.18)),fill=col,width=w)
        d.line((round(p.w*.06),round(p.h*.18),round(p.w*.06),round(p.h*.30)),fill=col,width=w)
        d.line((round(p.w*.75),round(p.h*.86),round(p.w*.94),round(p.h*.86)),fill=col,width=w)
        d.line((round(p.w*.94),round(p.h*.74),round(p.w*.94),round(p.h*.86)),fill=col,width=w)
    elif k=='white':
        d.line((round(p.w*.12),round(p.h*.19),round(p.w*.88),round(p.h*.19)),fill=(255,255,255,80),width=max(1,round(2*u)))
        d.rectangle((round(p.w*.07),round(p.h*.91),round(p.w*.93),round(p.h*.915)),fill=(12,12,12,85))
    elif k=='neon':
        # Sparse phosphor rails and scan marks preserve open portrait space.
        d.line((round(p.w*.06),round(p.h*.205),round(p.w*.94),round(p.h*.205)),fill=(205,255,0,170),width=max(1,round(2*u)))
        d.line((round(p.w*.08),round(p.h*.79),round(p.w*.36),round(p.h*.79)),fill=(205,255,0,115),width=max(1,round(2*u)))
        for y in (.12,.145,.17):d.rectangle((round(p.w*.86),round(p.h*y),round(p.w*.94),round(p.h*y+u/p.h)),fill=(205,255,0,110))
    elif k=='purple':
        d.polygon([(0,round(p.h*.16)),(round(p.w*.36),round(p.h*.09)),(round(p.w*.41),round(p.h*.13)),(0,round(p.h*.21))],fill=(165,114,207,65))
        d.line((round(p.w*.92),round(p.h*.22),round(p.w*.92),round(p.h*.72)),fill=(189,139,221,145),width=max(1,round(3*u)))
        d.line((round(p.w*.08),round(p.h*.87),round(p.w*.38),round(p.h*.87)),fill=(189,139,221,105),width=max(1,round(2*u)))
    elif k=='vividblue':
        d.rectangle((round(p.w*.055),round(p.h*.18),round(p.w*.945),round(p.h*.184)),fill=(32,226,225,145))
        d.polygon([(round(p.w*.70),round(p.h*.77)),(p.w,round(p.h*.69)),(p.w,round(p.h*.94)),(round(p.w*.82),round(p.h*.91))],fill=(25,126,153,35))
        d.rectangle((round(p.w*.06),round(p.h*.88),round(p.w*.28),round(p.h*.885)),fill=(98,67,51,150))
    elif k=='colorful':
        d.polygon([(0,round(p.h*.08)),(round(p.w*.28),0),(round(p.w*.34),round(p.h*.035)),(0,round(p.h*.14))],fill=(210,77,83,60))
        d.line((round(p.w*.08),round(p.h*.19),round(p.w*.42),round(p.h*.16)),fill=(232,207,72,145),width=max(1,round(3*u)))
        d.line((round(p.w*.65),round(p.h*.87),round(p.w*.94),round(p.h*.83)),fill=(204,157,226,145),width=max(1,round(3*u)))
    elif k=='ink':
        d.ellipse((round(-.22*p.w),round(.03*p.h),round(.34*p.w),round(.48*p.h)),fill=(235,232,215,25))
        d.line((round(p.w*.10),round(p.h*.20),round(p.w*.38),round(p.h*.20)),fill=(164,58,54,105),width=max(1,round(2*u)))
        d.rectangle((round(p.w*.08),round(p.h*.89),round(p.w*.92),round(p.h*.894)),fill=(244,241,225,65))
    elif k=='mint':
        d.ellipse((round(-.18*p.w),round(.55*p.h),round(.30*p.w),round(1.02*p.h)),fill=(85,190,132,28))
        d.line((round(p.w*.08),round(p.h*.19),round(p.w*.92),round(p.h*.19)),fill=(111,215,156,135),width=max(1,round(2*u)))
        d.line((round(p.w*.69),round(p.h*.87),round(p.w*.94),round(p.h*.87)),fill=(78,163,113,110),width=max(1,round(2*u)))
    elif k=='tornred':
        d.polygon([(0,round(p.h*.12)),(round(p.w*.33),round(p.h*.07)),(round(p.w*.38),round(p.h*.13)),(0,round(p.h*.18))],fill=(182,43,50,62))
        d.polygon([(round(p.w*.68),round(p.h*.82)),(p.w,round(p.h*.75)),(p.w,round(p.h*.95)),(round(p.w*.76),round(p.h*.91))],fill=(181,40,48,52))
        d.line((round(p.w*.08),round(p.h*.205),round(p.w*.92),round(p.h*.205)),fill=(236,223,198,115),width=max(1,round(2*u)))
    elif k=='warm':
        d.polygon([(0,0),(round(p.w*.28),0),(round(p.w*.18),round(p.h*.13)),(0,round(p.h*.17))],fill=(255,126,31,65))
        d.ellipse((round(p.w*.72),round(-.08*p.h),round(1.12*p.w),round(.30*p.h)),fill=(255,224,80,32))
        d.line((round(p.w*.08),round(p.h*.88),round(p.w*.92),round(p.h*.88)),fill=(255,146,36,125),width=max(1,round(3*u)))
    elif k=='deepbrown':
        d.rectangle((0,0,p.w,round(p.h*.18)),fill=(55,38,24,42))
        d.line((round(p.w*.09),round(p.h*.19),round(p.w*.91),round(p.h*.19)),fill=(221,183,112,130),width=max(1,round(2*u)))
        d.ellipse((round(-.12*p.w),round(.64*p.h),round(.32*p.w),round(1.04*p.h)),fill=(89,59,33,30))
    elif k=='waxcute':
        d.ellipse((round(-.12*p.w),round(.03*p.h),round(.28*p.w),round(.34*p.h)),fill=(250,177,207,34))
        d.ellipse((round(.76*p.w),round(.08*p.h),round(1.08*p.w),round(.37*p.h)),fill=(255,233,143,30))
        for x,y,col in ((.08,.22,(245,172,207,135)),(.13,.19,(255,229,135,145)),(.88,.18,(150,211,245,130)),(.92,.23,(118,216,164,125))):
            cx,cy=round(p.w*x),round(p.h*y);r=max(2,round(3*u));d.ellipse((cx-r,cy-r,cx+r,cy+r),fill=col)
    elif k=='mono':
        d.polygon([(0,round(p.h*.09)),(round(p.w*.30),round(p.h*.055)),(round(p.w*.33),round(p.h*.105)),(0,round(p.h*.14))],fill=(8,8,8,110))
        d.rectangle((round(p.w*.08),round(p.h*.205),round(p.w*.92),round(p.h*.209)),fill=(255,255,255,110))
        d.rectangle((round(p.w*.91),round(p.h*.56),round(p.w*.925),round(p.h*.76)),fill=(255,147,67,155))
    elif k=='elegantpink':
        d.polygon([(0,round(p.h*.10)),(round(p.w*.37),round(p.h*.055)),(round(p.w*.40),round(p.h*.115)),(0,round(p.h*.16))],fill=(240,0,183,55))
        d.line((round(p.w*.06),round(p.h*.205),round(p.w*.94),round(p.h*.205)),fill=(255,232,249,150),width=max(1,round(2*u)))
        d.ellipse((round(p.w*.79),round(p.h*.70),round(1.04*p.w),round(p.h*.94)),fill=(240,0,183,22))
    elif k=='qqcute':
        d.rounded_rectangle((round(p.w*.04),round(p.h*.045),round(p.w*.96),round(p.h*.18)),radius=round(12*u),fill=(255,248,220,34))
        for x,y,col in ((.07,.26,(242,167,209,140)),(.11,.23,(242,191,50,150)),(.88,.25,(242,167,209,140)),(.92,.21,(242,191,50,150))):
            q=max(2,round(4*u));cx,cy=round(p.w*x),round(p.h*y);d.rectangle((cx-q,cy-q,cx+q,cy+q),fill=col)
    elif k=='redyellow':
        d.line((round(p.w*.08),round(p.h*.205),round(p.w*.92),round(p.h*.205)),fill=(238,204,73,170),width=max(1,round(2*u)))
        d.polygon([(round(p.w*.72),round(p.h*.08)),(p.w,round(p.h*.04)),(p.w,round(p.h*.15)),(round(p.w*.78),round(p.h*.18))],fill=(178,42,58,42))
        d.rectangle((round(p.w*.035),round(p.h*.55),round(p.w*.042),round(p.h*.76)),fill=(238,204,73,125))
    elif k=='ginger':
        d.ellipse((round(-.16*p.w),round(.02*p.h),round(.30*p.w),round(.43*p.h)),fill=(222,159,188,24))
        d.polygon([(round(p.w*.18),round(p.h*.055)),(round(p.w*.82),round(p.h*.045)),(round(p.w*.78),round(p.h*.16)),(round(p.w*.22),round(p.h*.17))],fill=(54,39,48,42))
        d.line((round(p.w*.11),round(p.h*.205),round(p.w*.39),round(p.h*.185)),fill=(238,200,217,125),width=max(1,round(2*u)))
        d.line((round(p.w*.68),round(p.h*.87),round(p.w*.91),round(p.h*.85)),fill=(238,200,217,105),width=max(1,round(2*u)))
    elif k=='promo':
        d.polygon([(0,round(p.h*.76)),(round(p.w*.28),round(p.h*.70)),(round(p.w*.34),p.h),(0,p.h)],fill=(153,23,31,40))
        d.line((round(p.w*.08),round(p.h*.91),round(p.w*.92),round(p.h*.86)),fill=(232,183,68,135),width=max(1,round(3*u)))
        for x in (.78,.83,.88):d.line((round(p.w*x),round(p.h*.18),round(p.w*(x+.07)),round(p.h*.14)),fill=(183,37,43,100),width=max(1,round(2*u)))
    elif k=='energycartoon':
        for i in range(6):
            a=-.55+i*.22;x1=round(p.w*.06);y1=round(p.h*.24);x2=round(x1+math.cos(a)*p.w*.12);y2=round(y1+math.sin(a)*p.w*.12);d.line((x1,y1,x2,y2),fill=(245,93,168,115),width=max(1,round(2*u)))
        for x,y,col in ((.88,.18,(245,215,53,155)),(.92,.22,(99,195,244,145)),(.84,.24,(100,216,144,140))):
            cx,cy=round(p.w*x),round(p.h*y);r=max(2,round(4*u));d.ellipse((cx-r,cy-r,cx+r,cy+r),fill=col)
    elif k=='browngold':
        d.rectangle((round(p.w*.07),round(p.h*.10),round(p.w*.93),round(p.h*.103)),fill=(231,187,109,125))
        d.line((round(p.w*.12),round(p.h*.89),round(p.w*.88),round(p.h*.89)),fill=(231,187,109,110),width=max(1,round(2*u)))
        d.ellipse((round(p.w*.75),round(-.08*p.h),round(1.13*p.w),round(.29*p.h)),fill=(110,71,35,28))
    elif k=='latte':
        d.ellipse((round(-.16*p.w),round(.60*p.h),round(.28*p.w),round(1.04*p.h)),fill=(245,224,143,28))
        d.line((round(p.w*.08),round(p.h*.20),round(p.w*.92),round(p.h*.20)),fill=(242,226,154,130),width=max(1,round(2*u)))
        for x,col in ((.78,(244,181,196,115)),(.84,(173,222,204,115)),(.90,(243,230,148,130))):d.rectangle((round(p.w*x),round(p.h*.15),round(p.w*(x+.025)),round(p.h*.175)),fill=col)
    elif k=='blackyellow':
        d.rectangle((0,0,p.w,round(p.h*.18)),fill=(7,7,7,54));d.line((round(p.w*.07),round(p.h*.19),round(p.w*.93),round(p.h*.19)),fill=(255,235,74,155),width=max(1,round(2*u)))
        d.rectangle((round(p.w*.90),round(p.h*.58),round(p.w*.93),round(p.h*.78)),fill=(255,244,203,105))
    elif k=='floraltravel':
        d.polygon([(0,round(p.h*.08)),(round(p.w*.32),round(p.h*.035)),(round(p.w*.37),round(p.h*.10)),(0,round(p.h*.16))],fill=(222,178,84,45))
        d.line((round(p.w*.08),round(p.h*.88),round(p.w*.92),round(p.h*.84)),fill=(117,67,39,105),width=max(1,round(2*u)))
        d.ellipse((round(p.w*.78),round(p.h*.10),round(1.06*p.w),round(p.h*.36)),fill=(235,156,181,24))
    elif k=='verdant':
        d.ellipse((round(-.16*p.w),round(.57*p.h),round(.29*p.w),round(1.03*p.h)),fill=(101,158,76,28));d.line((round(p.w*.08),round(p.h*.20),round(p.w*.92),round(p.h*.20)),fill=(125,172,89,140),width=max(1,round(2*u)))
        for x in (.82,.87,.92):d.line((round(p.w*x),round(p.h*.15),round(p.w*(x+.025)),round(p.h*.12)),fill=(222,232,184,125),width=max(1,round(2*u)))
    elif k=='ins':
        d.polygon([(0,round(p.h*.10)),(round(p.w*.28),round(p.h*.06)),(round(p.w*.33),round(p.h*.12)),(0,round(p.h*.16))],fill=(105,73,60,55));d.rectangle((round(p.w*.82),round(p.h*.17),round(p.w*.92),round(p.h*.20)),fill=(188,217,234,95))
        for x,y in ((.08,.24),(.92,.22),(.87,.87)):d.line((round(p.w*x-3*u),round(p.h*y),round(p.w*x+3*u),round(p.h*y)),fill=(255,248,226,135),width=max(1,round(u)))
    elif k=='magenta':
        d.polygon([(0,round(p.h*.12)),(round(p.w*.36),round(p.h*.06)),(round(p.w*.40),round(p.h*.12)),(0,round(p.h*.18))],fill=(209,28,116,48));d.line((round(p.w*.08),round(p.h*.20),round(p.w*.92),round(p.h*.20)),fill=(247,92,158,140),width=max(1,round(2*u)))
        d.ellipse((round(p.w*.76),round(p.h*.70),round(1.08*p.w),round(1.01*p.h)),fill=(124,25,75,24))
    elif k=='hotpink':
        col=(244,56,139,120);d.line((round(p.w*.06),round(p.h*.18),round(p.w*.26),round(p.h*.18)),fill=col,width=max(1,round(3*u)));d.line((round(p.w*.06),round(p.h*.18),round(p.w*.06),round(p.h*.28)),fill=col,width=max(1,round(3*u)))
        d.line((round(p.w*.74),round(p.h*.87),round(p.w*.94),round(p.h*.87)),fill=col,width=max(1,round(3*u)));d.line((round(p.w*.94),round(p.h*.77),round(p.w*.94),round(p.h*.87)),fill=col,width=max(1,round(3*u)))
    elif k=='nostalgia':
        d.rectangle((0,0,p.w,round(p.h*.18)),fill=(75,55,40,36));d.line((round(p.w*.10),round(p.h*.195),round(p.w*.90),round(p.h*.195)),fill=(224,198,136,125),width=max(1,round(2*u)))
        d.ellipse((round(-.14*p.w),round(.63*p.h),round(.30*p.w),round(1.04*p.h)),fill=(110,78,49,25))
    elif k=='lightbulb':
        d.polygon([(0,round(p.h*.08)),(round(p.w*.31),round(p.h*.035)),(round(p.w*.36),round(p.h*.10)),(0,round(p.h*.16))],fill=(234,137,49,48));d.rectangle((round(p.w*.06),round(p.h*.79),round(p.w*.94),round(p.h*.80)),fill=(238,164,65,105))
        for x,y in ((.84,.15),(.90,.18),(.87,.23)):d.ellipse((round(p.w*x-3*u),round(p.h*y-3*u),round(p.w*x+3*u),round(p.h*y+3*u)),fill=(244,198,74,135))
    elif k=='redfestive':
        d.polygon([(0,0),(round(p.w*.42),0),(round(p.w*.34),round(p.h*.16)),(0,round(p.h*.20))],fill=(151,34,33,65))
        d.line((round(p.w*.07),round(p.h*.205),round(p.w*.93),round(p.h*.205)),fill=(241,190,83,150),width=max(1,round(3*u)))
        for i in range(5):
            x=round(p.w*(.78+i*.038));d.line((x,round(p.h*.12),x+round(16*u),round(p.h*.08)),fill=(248,197,92,110),width=max(1,round(2*u)))
    elif k=='variety':
        d.ellipse((round(-.12*p.w),round(.03*p.h),round(.24*p.w),round(.34*p.h)),fill=(255,160,202,30))
        d.ellipse((round(.80*p.w),round(.07*p.h),round(1.12*p.w),round(.36*p.h)),fill=(142,229,194,28))
        for x,y,col in ((.07,.24,(255,206,72,160)),(.12,.20,(243,105,169,145)),(.88,.20,(109,208,245,145)),(.93,.25,(126,221,164,145))):
            q=max(2,round(4*u));cx,cy=round(p.w*x),round(p.h*y);d.rounded_rectangle((cx-q,cy-q,cx+q,cy+q),radius=q//2,fill=col)
    elif k=='grid':
        d.rectangle((0,0,p.w,round(p.h*.19)),fill=(37,26,82,42))
        for x,y,col in ((.04,.08,(96,116,255,115)),(.10,.13,(167,91,238,115)),(.86,.07,(113,210,242,105)),(.91,.14,(128,95,238,110))):
            q=round(13*u);cx,cy=round(p.w*x),round(p.h*y);d.polygon([(cx-q,cy-q),(cx+q,cy-q),(cx+q,cy+q),(cx-q,cy+q)],fill=col)
        for x in (.08,.14,.20):d.line((round(p.w*x),round(p.h*.86),round(p.w*x),round(p.h*.89)),fill=(133,115,241,120),width=max(1,round(2*u)))
    elif k=='comicred':
        d.polygon([(0,round(p.h*.08)),(round(p.w*.29),round(p.h*.04)),(round(p.w*.35),round(p.h*.12)),(0,round(p.h*.17))],fill=(182,32,43,62))
        d.rectangle((round(p.w*.035),round(p.h*.53),round(p.w*.045),round(p.h*.78)),fill=(241,224,73,145))
        for x,y in ((.84,.14),(.89,.18),(.93,.13)):d.ellipse((round(p.w*x-3*u),round(p.h*y-3*u),round(p.w*x+3*u),round(p.h*y+3*u)),fill=(241,224,73,145))
    elif k=='romance':
        d.ellipse((round(-.18*p.w),round(.04*p.h),round(.28*p.w),round(.42*p.h)),fill=(245,147,190,28))
        d.ellipse((round(.75*p.w),round(.66*p.h),round(1.13*p.w),round(1.04*p.h)),fill=(255,220,228,25))
        d.line((round(p.w*.08),round(p.h*.205),round(p.w*.42),round(p.h*.19)),fill=(248,184,208,120),width=max(1,round(2*u)))
        d.line((round(p.w*.68),round(p.h*.88),round(p.w*.92),round(p.h*.85)),fill=(248,184,208,95),width=max(1,round(2*u)))
    elif k=='transyellow':
        d.polygon([(0,round(p.h*.07)),(round(p.w*.44),round(p.h*.04)),(round(p.w*.39),round(p.h*.17)),(0,round(p.h*.20))],fill=(242,224,85,48))
        d.rectangle((round(p.w*.06),round(p.h*.79),round(p.w*.94),round(p.h*.805)),fill=(242,224,85,72))
        d.rectangle((round(p.w*.84),round(p.h*.16),round(p.w*.92),round(p.h*.19)),fill=(235,160,89,100))
    elif k=='tornedge':
        top=round(p.h*.075);bottom=round(p.h*.16);pts=[(0,top),(round(p.w*.18),top-4*u),(round(p.w*.35),top+3*u),(round(p.w*.51),top-5*u),(round(p.w*.69),top+2*u),(round(p.w*.86),top-3*u),(p.w,top+2*u),(p.w,bottom),(0,bottom)]
        d.polygon(pts,fill=(245,238,197,36))
        d.line((round(p.w*.08),round(p.h*.205),round(p.w*.92),round(p.h*.205)),fill=(235,221,120,115),width=max(1,round(2*u)))
        d.polygon([(round(p.w*.84),round(p.h*.84)),(p.w,round(p.h*.80)),(p.w,p.h),(round(p.w*.90),p.h)],fill=(245,238,197,25))
    elif k=='emojiwhite':
        d.rectangle((0,0,p.w,round(p.h*.18)),fill=(255,255,255,25))
        for x,y,col in ((.06,.20,(255,210,77,155)),(.11,.24,(245,148,184,145)),(.87,.20,(12,12,14,145)),(.92,.24,(255,210,77,145))):
            q=max(2,round(4*u));cx,cy=round(p.w*x),round(p.h*y);d.rectangle((cx-q,cy-q,cx+q,cy+q),fill=col)
        d.line((round(p.w*.08),round(p.h*.87),round(p.w*.31),round(p.h*.87)),fill=(255,255,255,115),width=max(1,round(2*u)))
    elif k=='contrastpop':
        d.polygon([(0,0),(round(p.w*.35),0),(round(p.w*.25),round(p.h*.16)),(0,round(p.h*.20))],fill=(244,119,58,64))
        d.polygon([(p.w,round(p.h*.04)),(round(p.w*.78),round(p.h*.09)),(round(p.w*.84),round(p.h*.22)),(p.w,round(p.h*.17))],fill=(37,190,191,48))
        d.polygon([(0,round(p.h*.79)),(round(p.w*.18),round(p.h*.75)),(round(p.w*.28),p.h),(0,p.h)],fill=(10,12,15,58))
        d.line((round(p.w*.68),round(p.h*.87),round(p.w*.94),round(p.h*.83)),fill=(244,119,58,120),width=max(1,round(3*u)))
    if layer.getchannel('A').getbbox(): canvas=Image.alpha_composite(canvas,layer)
    return canvas


def video_layer(p,im,t):
    """Video-only operations; never transform burned-in title/caption layers."""
    canvas=_style_backdrop(p, im.convert('RGBA'), t)
    for e in p.p.get('scene_canvas',[]):
        if not e['start']<=t<e['end']:continue
        k=e['kind']
        if k=='circle':
            r=round(e.get('radius',.39)*p.w);cx,cy=e.get('center',[.5,.42]);mask=Image.new('L',canvas.size);d=ImageDraw.Draw(mask);x=cx*p.w;y=cy*p.h;d.ellipse((x-r,y-r,x+r,y+r),fill=255)
            if e.get('feather'):mask=mask.filter(ImageFilter.GaussianBlur(e['feather']*p.w))
            canvas=Image.composite(canvas,Image.new('RGBA',canvas.size,e.get('background','#080808')),mask)
        elif k=='inset':
            scale=e.get('scale',.86);size=(round(p.w*scale),round(p.h*scale))
            small=canvas.resize(size,Image.Resampling.LANCZOS)
            canvas=Image.new('RGBA',canvas.size,e.get('background','#080808'))
            canvas.alpha_composite(small,((p.w-size[0])//2,(p.h-size[1])//2))
        elif k=='vignette':
            key=('scene_vignette',p.w,p.h,e.get('strength',.6))
            if key not in p.layers:
                import numpy as np
                yy,xx=np.mgrid[:p.h,:p.w];dist=((xx/p.w-.5)/.66)**2+((yy/p.h-.43)/.75)**2
                a=np.clip((dist-.10)*e.get('strength',.6)*255,0,210).astype('uint8');shade=Image.new('RGBA',canvas.size,(0,0,0,0));shade.putalpha(Image.fromarray(a));p.layers[key]=shade
            strength=min(ease((t-e['start'])/.18),ease((e['end']-t)/.18));shade=p.layers[key].copy();shade.putalpha(shade.getchannel('A').point(lambda x:round(x*strength)));canvas=Image.alpha_composite(canvas,shade)
        elif k=='swipe':
            q=(t-e['start'])/(e['end']-e['start']);envelope=math.sin(math.pi*q)**2
            shift=round(p.w*ease(q));base=ImageChops.offset(canvas,shift,0)
            # Current-frame periodic displacement with horizontal continuous box blur.
            # Approximation, not recovered original temporal transition frames.
            radius=round(p.w*.075*envelope)
            if radius:
                import numpy as np
                pixels=np.asarray(base);padded=np.pad(pixels,((0,0),(radius,radius),(0,0)),mode='wrap')
                sums=np.cumsum(np.pad(padded,((0,0),(1,0),(0,0))),axis=1,dtype=np.uint32)
                width=2*radius+1;base=Image.fromarray(((sums[:,width:]-sums[:,:-width])/width).astype('uint8'))
            canvas=base
    return canvas


def paint(p,im,t):
    canvas=video_layer(p,im,t)
    from privacy_masking import paint as paint_privacy
    canvas=paint_privacy(canvas,p.privacy,t,p.p['fps'])
    for e in layout(p):
        if not e['start']<=t<e['end']:continue
        age=t-e['start'];remaining=e['end']-t;im=e['image'];dx=dy=0
        duration=.22 if e['animation']=='soft' else .18 if e['animation']=='label' else .10
        progress=ease(age/duration);opacity=1 if e['animation']=='steady' else min(progress,ease(remaining/.09))
        if e['animation']=='soft':dy=round(9*p.unit*(1-progress))
        elif e['animation']=='label':dx=round(9*p.unit*(1-progress))
        sprite=im.copy()
        if e['animation']=='pop':
            scale=.86+.14*ease(age/.24)
            sprite=im.resize((max(1,round(im.width*scale)),max(1,round(im.height*scale))),Image.Resampling.LANCZOS)
            dx=(im.width-sprite.width)//2;dy=(im.height-sprite.height)//2
        if e['animation']=='ink_write':
            # Sequential left-to-right ink reveal, on top of the licensed substitute font.
            q=min(1.,max(0.,age/.68));w=max(1,round(im.width*q));mask=Image.new('L',im.size);ImageDraw.Draw(mask).rectangle((0,0,w,im.height),fill=255)
            sprite.putalpha(ImageChops.multiply(sprite.getchannel('A'),mask))
        elif e['animation']=='heart_float':
            dy=round(-14*p.unit*ease(age/max(.01,e['end']-e['start'])))
        elif e['animation']=='cursor_tap':
            scale=.90+.10*ease(age/.18)
            sprite=im.resize((max(1,round(im.width*scale)),max(1,round(im.height*scale))),Image.Resampling.LANCZOS)
            dx=(im.width-sprite.width)//2;dy=(im.height-sprite.height)//2
        if e['animation']=='soft' and age<duration:sprite=sprite.filter(ImageFilter.GaussianBlur(2.2*p.unit*(1-progress)))
        sprite.putalpha(sprite.getchannel('A').point(lambda a:round(a*opacity)))
        canvas.alpha_composite(sprite,(e['x']+dx,e['y']+dy))
    return canvas.convert('RGB')


def write_srt(p,path):
    """SRT expresses visible spoken text, including retained first phrases, not tags."""
    from timeline import srt_time
    rows=[];previous=None
    for g in p['scene_captions']:
        phrases=[dict(e) for e in g['phrases']]
        if p.get('scene_takeover') and p.get('template_variant')=='tpl-red-yellow-editorial' and len(phrases)==2:
            phrases[0]['end']=min(phrases[0]['end'],phrases[1]['start']+.16)
        points=sorted({v for e in phrases for v in (e['start'],e['end'])})
        for a,b in zip(points,points[1:]):
            text='\n'.join(texts(e) for e in phrases if e['start']<=a<e['end'])
            if not text:continue
            if previous is not None and previous[2]==text and abs(previous[1]-a)<1e-7:previous[1]=b
            else:previous=[a,b,text];rows.append(previous)
    from pathlib import Path
    Path(path).write_text('\n'.join(f'{i}\n{srt_time(a)} --> {srt_time(b)}\n{text}\n' for i,(a,b,text) in enumerate(rows,1)),encoding='utf8')
