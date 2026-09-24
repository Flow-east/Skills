"""B5a: four reference-led typography/layout systems. Original geometric surfaces.
No reference photo extraction, automatic semantic placement or official font claim.
"""
import hashlib, math, random
from pathlib import Path
from PIL import Image, ImageDraw, ImageChops, ImageFilter, ImageOps
from template_scenes_b3b import stack
KINDS={'orangeline','colorful','mint','tornred'}
MODES={'orangeline':{'normal','display','impact'},'colorful':{'normal','display','impact'},'mint':{'normal','card'},'tornred':{'normal','paper','impact'}}

def validate(p):
    from template_scenes import interval,texts,finite
    k=p.variant['scene_system']['kind'];duration=p.p['duration'];phrases={}
    if any(p.p.get(key) for key in ('scene_notes','scene_highlights','scene_title_surface','scene_identity','scene_accents')):raise ValueError('Unsupported B5a auxiliary layer')
    for g in p.p['scene_captions']:
        for e in g['phrases']:
            ident=e.get('id')
            if not isinstance(ident,str) or not ident or ident in phrases:raise ValueError('B5a requires unique phrase ids')
            phrases[ident]=e
            if e.get('mode','normal') not in MODES[k]:raise ValueError('Unsupported B5a caption mode')
            if e.get('pointer') or e.get('color','normal')!='normal' or any('fill' in r for r in e.get('runs',[])):raise ValueError('B5a colors/markers are template bound')
            if 'underline' in e:
                if k!='mint' or not isinstance(e['underline'],str) or not e['underline'] or e['underline'] not in texts(e):raise ValueError('Underline must quote mint phrase')
    for e in p.p.get('scene_tags',[]):
        a,b=interval(e,duration);q=phrases.get(e.get('phrase_id'))
        if not q or not q['start']<=a<b<=q['end'] or e['text'] not in texts(q):raise ValueError('B5a tag must quote active phrase')
        if e.get('icon') or e.get('orientation','horizontal')!='horizontal':raise ValueError('B5a has typographic tags, not arbitrary icons')
    calls=p.p.get('scene_callouts',[])
    if not isinstance(calls,list) or calls and k!='colorful':raise ValueError('Retained feature labels require colorful')
    for e in calls:
        a,b=interval(e,duration);q=phrases.get(e.get('phrase_id'))
        if not q or not q['start']<=a<q['end'] or not isinstance(e.get('text'),str) or not 1<=len(e['text'])<=9 or e['text'] not in texts(q):raise ValueError('Feature label must quote phrase and enter during it')
        if isinstance(e.get('slot'),bool) or e.get('slot') not in (0,1) or e.get('side','left') not in ('left','right') or not str(e.get('reason','')).strip():raise ValueError('Feature label needs slot/side/reason')
        if any(v in e for v in ('x','y')) and any(not finite(e.get(v)) or not 0<=e[v]<=1 for v in ('x','y')):raise ValueError('Feature anchor needs x/y together')
    for i,e in enumerate(calls):
        for q in calls[i+1:]:
            if e['slot']==q['slot'] and e.get('side','left')==q.get('side','left') and min(e['end'],q['end'])>max(e['start'],q['start']):raise ValueError('Overlapping feature label slot')
    media=p.p.get('scene_media',[])
    if not isinstance(media,list) or media and k!='tornred':raise ValueError('Illustration cards require tornred')
    p.scene_media_assets=[];p.scene_media_images={}
    for i,e in enumerate(media):
        a,b=interval(e,duration);q=phrases.get(e.get('phrase_id'))
        if not q or not q['start']<=a<b<=q['end']:raise ValueError('Illustration must fit anchored phrase clock')
        if any(not finite(e.get(v)) or not 0<=e[v]<=1 for v in ('x','y','width','height')) or not 0<e['width']<=.75 or not 0<e['height']<=.6:raise ValueError('Invalid bounded illustration rectangle')
        if e.get('fit','contain')!='contain':raise ValueError('Illustration card contains full image; no silent crop')
        if e.get('review_status')!='reviewed' or e.get('privacy_status')!='reviewed' or any(not isinstance(e.get(v),str) or not e[v].strip() for v in ('reason','source','rights','reviewer','privacy_review')):raise ValueError('Illustration needs source, rights and privacy review')
        path=Path(e.get('path',''))
        if not path.is_absolute() or not path.is_file():raise ValueError('Illustration needs existing absolute local path')
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        if digest!=e.get('sha256'):raise ValueError('Illustration hash changed; re-review required')
        with Image.open(path) as im:
            if im.format not in ('PNG','JPEG','WEBP') or getattr(im,'n_frames',1)!=1 or im.width*im.height>16_000_000:raise ValueError('Use reviewed single-frame raster illustration up to 16 MP')
            p.scene_media_images[i]=ImageOps.exif_transpose(im).convert('RGBA')
        p.scene_media_assets.append(dict(path=str(path),sha256=digest,source=e['source'],rights=e['rights'],privacy_status=e['privacy_status'],reviewer=e['reviewer']))

def _glyphs(p,runs,size,role):
    x=0;gs=[]
    for r in runs:
        rr=r.get('role',role);f=p.font(size,rr);t=r['text'];bb=f.getbbox(t,anchor='ls');gs.append((x,t,f,rr,bb));x+=f.getlength(t)
    return gs,x

def line(p,runs,size,role='body',mode='normal',maxw=None,underline=None):
    """Baseline/ink-bearing aware; thin serif stays thin, brush stays brush."""
    k=p.variant['scene_system']['kind'];u=p.unit;maxw=maxw or p.w*.88;pad=math.ceil(11*u)
    gs,width=_glyphs(p,runs,size,role);left=min(x+b[0] for x,t,f,r,b in gs);right=max(x+b[2] for x,t,f,r,b in gs)
    estimated=right-left+2*pad
    if estimated>maxw:
        factor=(maxw-2*pad)/max(1,right-left)
        if factor<.72:raise ValueError('B5a phrase too long; author semantic line split instead of tiny type')
        size*=factor;gs,width=_glyphs(p,runs,size,role);left=min(x+b[0] for x,t,f,r,b in gs);right=max(x+b[2] for x,t,f,r,b in gs)
    top=min(b[1] for x,t,f,r,b in gs);bottom=max(b[3] for x,t,f,r,b in gs)
    out=Image.new('RGBA',(math.ceil(right-left)+2*pad,bottom-top+2*pad));d=ImageDraw.Draw(out)
    for x,t,f,rr,bb in gs:
        pos=(pad+x-left,pad-top)
        def draw(fill,sw=0,edge=None,dx=0,dy=0):d.text((pos[0]+dx*u,pos[1]+dy*u),t,font=f,anchor='ls',fill=fill,stroke_width=round(sw*u),stroke_fill=edge or fill)
        if k=='orangeline':
            fill='#FF9B38' if mode=='impact' else '#FFF2A5' if rr=='keyword' else '#FFFFFF'
            draw('#161616',3 if role in ('title','sticker') else .8,dx=1.3,dy=2);draw(fill,1.7 if role in ('title','sticker') else .45,'#202020')
        elif k=='colorful':
            fill='#E74459' if mode=='impact' else '#FFED8E' if rr=='keyword' or mode=='display' else '#FFFAFF'
            if role in ('title','sticker'):
                draw('#B679D2',2.4,dx=.5,dy=.6);draw(fill,.5,'#9351AD')
            else:
                draw('#1D151D',1.2,dx=1,dy=1.8)
                draw(fill,.65 if mode=='impact' else .35,'#FFE8DA' if mode=='impact' else '#3B2633')
        elif k=='mint':
            fill='#111C17' if mode=='card' else '#FFFFFF' if role=='title' and mode=='white' else '#7BD6A1'
            if mode!='card':draw('#162A21',1,dx=1.1,dy=2.0)
            draw(fill)
        else:
            fill='#15100E' if mode=='paper' else '#9E2131' if mode in ('impact','red') or rr=='keyword' else '#FFFBF0'
            if mode not in ('paper','red'):draw('#251819',.6,dx=.8,dy=1.4)
            draw(fill,.65 if mode=='impact' or rr=='keyword' else 0,'#F9E0CF')
    if underline:
        # Span follows the actual role-font advances, not a percentage approximation.
        text=''.join(r['text'] for r in runs);start=text.index(underline);end=start+len(underline);cursor=0;spans=[]
        for x,t,f,rr,bb in gs:
            a=max(0,start-cursor);b=min(len(t),end-cursor)
            if a<b:spans.append((x+f.getlength(t[:a]),x+f.getlength(t[:b])))
            cursor+=len(t)
        y=out.height-round(5*u);color='#182B20' if mode=='card' else '#7EDAA5'
        for a,b in spans:d.line((pad+a-left,y,pad+b-left,y),fill=color,width=max(1,round(1.5*u)))
    if k=='colorful':
        # Actual oblique serif, not rotating the baseline as a substitute for italics.
        shear=.15;extra=math.ceil(out.height*shear)
        out=out.transform((out.width+extra,out.height),Image.Transform.AFFINE,(1,shear,-extra,0,1,0),Image.Resampling.BICUBIC)
        if out.width>maxw:raise ValueError('Oblique serif exceeds safe width; split caption')
    return out

def plate(im,color,u,style):
    out=Image.new('RGBA',im.size);d=ImageDraw.Draw(out);w,h=out.size
    if style=='underline':d.polygon([(2*u,h*.52),(w-2*u,h*.43),(w-2*u,h-2*u),(2*u,h-2*u)],fill=color)
    elif style=='round':d.rounded_rectangle((0,0,w-1,h-1),radius=round(7*u),fill=color)
    else:d.rectangle((0,0,w-1,h-1),fill=color)
    out.alpha_composite(im);return out

def paper(p,text,size,maxw):
    """Each character has its own stable torn silhouette; never random per frame."""
    u=p.unit;glyphs=[line(p,[dict(text=ch,role='sticker')],size,'sticker','paper',p.w) for ch in text]
    f=p.font(size,'sticker');boxes=[f.getbbox(ch,anchor='ls') for ch in text]
    top=min(b[1] for b in boxes);bottom=max(b[3] for b in boxes)
    tiles=[]
    for i,(ch,im,bb) in enumerate(zip(text,glyphs,boxes)):
        box=im.getbbox()
        if box:im=im.crop(box)
        else:im=Image.new('RGBA',(max(1,round(f.getlength(ch))),1))
        # Full-height individual paper tiles share a text baseline. A dash or comma
        # must not collapse its paper height or jump to the top of adjacent Hanzi.
        pad=round(5*u);w=im.width+pad*2;h=bottom-top+pad*2
        rng=random.Random(hashlib.sha256((text+'|'+str(i)).encode()).hexdigest());tile=Image.new('RGBA',(w,h));d=ImageDraw.Draw(tile)
        step=max(2,round(9*u));jitter=max(1,round(2*u));pts=[(x,rng.randint(0,jitter)) for x in range(0,w,step)]+[(w-1,0),(w-1,h-1)]+[(x,h-1-rng.randint(0,jitter)) for x in range(w-1,-1,-step)]+[(0,h-1)]
        d.polygon(pts,fill='#FFFDF7');tile.alpha_composite(im,(pad,pad+bb[1]-top));tile=tile.rotate((-1,1.1,-.6,.7)[i%4],Image.Resampling.BICUBIC,expand=True);tiles.append(tile)
    gap=max(1,round(u));w=sum(t.width for t in tiles)+gap*(len(tiles)-1);h=max(t.height for t in tiles)+round(3*u)
    if w>maxw:
        factor=maxw/w
        if factor<.72:raise ValueError('Torn paper phrase too long; split by meaning')
        return paper(p,text,size*factor*.98,maxw)
    out=Image.new('RGBA',(w,h));x=0
    for i,t in enumerate(tiles):out.alpha_composite(t,(x,round(u*(i%3))));x+=t.width+gap
    return out

def title(p):
    c=p.variant['scene_system'];k=c['kind'];u=p.unit;ims=[]
    for i,t in enumerate(p.p.get('scene_title_lines',[])):
        size=c['title_size'] if i==0 else c['subtitle_size'];mode='white' if k=='mint' and i else 'red' if k=='tornred' and i else 'normal'
        im=line(p,[dict(text=t,role='title')],size,'title',mode,p.w*.85)
        if k=='orangeline':im=plate(im,'#FF983F',u,'underline').rotate(3,Image.Resampling.BICUBIC,expand=True)
        if k=='tornred' and i:im=plate(im,'#FFFDF1',u,'round')
        ims.append(im)
    return stack(ims,round(2*u)) if ims else None

def layout(p):
    from template_scenes import _box,texts
    c=p.variant['scene_system'];k=c['kind'];u=p.unit;entries=[]
    def add(im,x,y,a,b,role,anim='fade'):
        x=round(x);y=round(y);env=round(10*u) if anim in ('label','soft') else 0
        entries.append(dict(image=im,x=x,y=y,start=a,end=b,role=role,animation=anim,box=_box(im,x,y,env)))
    ti=title(p)
    if ti:add(ti,(p.w-ti.width)/2,p.h*c['title_y']-ti.height/2,0,min(p.p['duration'],p.p.get('title_duration',c['title_duration'])),'title')
    # Illustration sits behind text; all simultaneous boxes must still be non-overlapping.
    for i,e in enumerate(p.p.get('scene_media',[])):
        w,h=round(p.w*e['width']),round(p.h*e['height']);im=Image.new('RGBA',(w,h),'#F7F4EF');src=ImageOps.contain(p.scene_media_images[i],(w,h),Image.Resampling.LANCZOS);im.alpha_composite(src,((w-src.width)//2,(h-src.height)//2));mask=Image.new('L',(w,h));ImageDraw.Draw(mask).rounded_rectangle((0,0,w-1,h-1),radius=round(13*u),fill=255);im.putalpha(mask);add(im,p.w*e['x'],p.h*e['y'],e['start'],e['end'],'illustration','pop')
    for g in p.p['scene_captions']:
        blocks=[]
        for e in g['phrases']:
            mode=e.get('mode','normal');runs=e.get('runs') or [dict(text=texts(e),role='body')]
            if k=='tornred' and mode=='paper':im=paper(p,texts(e),c['display_size'],p.w*.84)
            else:
                size=c['body_size'] if mode in ('normal','card') else c['display_size']
                im=line(p,runs,size,'body',mode,p.w*.86,underline=e.get('underline'))
                if k=='mint' and mode=='card':im=plate(im,'#78D89D',u,'round')
                if k=='tornred' and mode=='normal':im=plate(im,(20,16,14,125),u,'round')
            blocks.append((e,im))
        gap=round(6*u);height=sum(im.height for e,im in blocks)+gap*(len(blocks)-1);y=p.h*c['caption_y']-height/2
        for i,(e,im) in enumerate(blocks):
            x=(p.w-im.width)/2
            if len(blocks)>1:
                if k in ('orangeline','colorful'):x=p.w*.14 if i==0 else p.w*.86-im.width
                elif k=='tornred':x=p.w*.09 if i==0 else p.w*.91-im.width
            anim='label' if k=='orangeline' and e.get('mode')=='impact' else 'pop' if k=='tornred' and e.get('mode')=='paper' else 'fade'
            add(im,x,y,e['start'],e['end'],'caption',anim);y+=im.height+gap
    for e in p.p.get('scene_tags',[]):
        im=paper(p,e['text'],c['tag_size'],p.w*.30) if k=='tornred' else line(p,[dict(text=e['text'],role='sticker')],c['tag_size'],'sticker','card' if k=='mint' else 'normal',maxw=p.w*.30)
        if k=='orangeline':im=plate(im,'#FF983F',u,'underline')
        if k=='mint':im=plate(im,'#78D89D',u,'round')
        x=p.w*.94-im.width if e.get('side','right')=='right' else p.w*.06
        add(im,x,p.h*c['tag_y']-im.height/2,e['start'],e['end'],'tag','label')
    for e in p.p.get('scene_callouts',[]):
        im=line(p,[dict(text=e['text'],role='sticker')],22,'sticker',maxw=p.w*.34)
        # Slender purple bookends like product labels, not a filled caption rectangle.
        d=ImageDraw.Draw(im);d.line((2*u,im.height*.2,2*u,im.height*.8),fill='#D4A8E8',width=max(1,round(u)));d.line((im.width-2*u,im.height*.2,im.width-2*u,im.height*.8),fill='#D4A8E8',width=max(1,round(u)))
        x=p.w*.06 if e.get('side','left')=='left' else p.w*.94-im.width
        add(im,p.w*e['x'] if 'x' in e else x,p.h*e['y'] if 'y' in e else p.h*(c['callout_y']+e['slot']*.055),e['start'],e['end'],'callout')
    return entries
