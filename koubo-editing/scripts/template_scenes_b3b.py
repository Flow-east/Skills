"""Seven reference-led layouts. Original geometry and licensed substitute fonts.
No implicit identity claims, numeric claims, or composition-changing video effects.
"""
import math
from PIL import Image, ImageDraw
from scene_bilingual import wrap_text

KINDS = {'biyellow', 'luxury', 'brightyellow', 'navy', 'news', 'crispred', 'vividblue'}
BILINGUAL = {'biyellow', 'brightyellow'}


def validate(p):
    from template_scenes import texts
    k = p.variant['scene_system']['kind']
    if p.p.get('scene_notes') or p.p.get('scene_highlights') or p.p.get('scene_title_surface'):
        raise ValueError('B3b does not implement notes/highlights/title surfaces')
    for g in p.p['scene_captions']:
        for e in g['phrases']:
            allowed = {'normal', 'display'} if k in {'luxury','news','navy'} else {'normal','label'} if k == 'vividblue' else {'normal'}
            if e.get('mode','normal') not in allowed or e.get('color','normal') != 'normal':
                raise ValueError('Undeclared B3b phrase state')
            if any('fill' in r for r in e.get('runs',[])):
                raise ValueError('B3b color is contract-bound')
    for e in p.p.get('scene_tags',[]):
        # Tags quote a currently visible phrase; no fabricated metrics/biography.
        if not any(q['start'] <= e['start'] < e['end'] <= q['end'] and e['text'] in texts(q)
                   for g in p.p['scene_captions'] for q in g['phrases']):
            raise ValueError('B3b tag must quote one overlapping phrase')
        if e.get('side','right') not in ('left','right'):
            raise ValueError('Unknown label side')


def line(p, runs, size, role='body', style='normal', maxw=None):
    """Mixed baseline sizes, including real negative bearings, bounded fit."""
    c=p.variant['scene_system'];k=c['kind'];u=p.unit;pad=math.ceil(13*u);maxw=maxw or p.w*.86
    for factor in (1,.96,.92,.88,.84,.8,.76,.72):
        glyphs=[];cursor=0;left=0;right=0;top=0;bottom=0
        for r in runs:
            rr=r.get('role',role);sz=c['keyword_size'] if role=='body' and rr=='keyword' else size
            if style=='display':sz=max(sz,c['display_size'])
            f=p.font(sz*factor,rr);box=f.getbbox(r['text'],anchor='ls')
            glyphs.append((cursor,r['text'],f,rr));left=min(left,cursor+box[0]);right=max(right,cursor+box[2]);top=min(top,box[1]);bottom=max(bottom,box[3]);cursor+=f.getlength(r['text'])
        if right-left+2*pad<=maxw:break
    else:raise ValueError('B3b text too long: resegment faithfully; minimum scale 72%')
    im=Image.new('RGBA',(math.ceil(right-left)+2*pad,math.ceil(bottom-top)+2*pad));d=ImageDraw.Draw(im)
    for x,text,f,rr in glyphs:
        def ink(fill,sw=0,edge=None,dx=0,dy=0):
            d.text((pad+x-left+dx*u,pad-top+dy*u),text,font=f,anchor='ls',fill=fill,stroke_width=max(0,round(sw*u)),stroke_fill=edge or fill)
        if role=='translation':
            ink('#FFFFFF',1.6,'#181818')
        elif k=='biyellow':
            color='#FFFFFF' if style=='headline' else '#FFE339'
            ink('#080808',5,dx=1,dy=3);ink(color,2.8,'#101010')
        elif k=='brightyellow':
            ink('#FFFDF1',6);ink('#11100B',3.6);ink('#FFE628',.4,'#332800')
        elif k=='luxury':
            color='#FFCC65' if style in ('headline','display') else '#ED957E' if rr=='keyword' else '#FFF9EB'
            ink('#2A201D',1.8,dx=1,dy=2);ink(color)
        elif k=='navy':
            if style=='headline':ink('#182F52',2.6,'#FFFCEF')
            else:ink('#161F30',1,dx=1,dy=2);ink('#F3E9B8' if style=='subhead' or rr=='body' else '#FFFFFF')
        elif k=='news':
            ink('#FFFFFF' if style in ('headline','subhead','tag') else '#0756D9')
        elif k=='crispred':
            if style=='headline':ink('#37202B',1.5,dx=1,dy=2);ink('#FFF5EF',.5,'#572935')
            elif rr=='keyword' or style=='subhead':ink('#913D47',1.1,'#FFF0DF')
            else:ink('#FAEEE8',.9,'#62252E',dx=1,dy=1);ink('#FFF5EB')
        elif k=='vividblue':
            ink('#12292D',2,dx=2,dy=3);ink('#21E6E3' if rr in ('keyword','title') and style!='label' else '#FFFFFF')
    return im


def plate(im,color,pad=0,slant=0,outline=None):
    out=Image.new('RGBA',(im.width+2*pad+slant,im.height+2*pad));d=ImageDraw.Draw(out);w,h=out.size
    if slant:d.polygon([(slant,0),(w,0),(w-slant,h),(0,h)],fill=color)
    else:d.rectangle((0,0,w-1,h-1),fill=color,outline=outline)
    out.alpha_composite(im,(pad+slant//2,pad));return out


def stack(ims,gap,align='center'):
    w=max(im.width for im in ims);h=sum(im.height for im in ims)+gap*(len(ims)-1)
    out=Image.new('RGBA',(w,h));y=0
    for im in ims:
        x=0 if align=='left' else w-im.width if align=='right' else (w-im.width)//2
        out.alpha_composite(im,(x,y));y+=im.height+gap
    return out


def title(p):
    c=p.variant['scene_system'];k=c['kind'];u=p.unit;ims=[]
    for j,value in enumerate(p.p.get('scene_title_lines',[])):
        role='title' if j==0 or k in ('biyellow','brightyellow','news') else 'body'
        im=line(p,[dict(text=value,role=role)],c['title_size'] if j==0 else c['subtitle_size'],role,'headline' if j==0 else 'subhead',p.w*(.78 if k=='brightyellow' else .82))
        if k=='news':im=plate(im,'#0954BA' if j==0 else '#D84638',slant=round(22*u))
        elif k=='navy' and j:im=plate(im,'#172D49')
        elif k=='crispred' and j:im=plate(im,(248,238,228,125))
        elif k=='vividblue' and j:
            out=Image.new('RGBA',(im.width+round(18*u),im.height));ImageDraw.Draw(out).polygon([(0,im.height),(12*u,4*u),(18*u,4*u),(6*u,im.height)],fill='#21E6E3');out.alpha_composite(im,(round(18*u),0));im=out
        ims.append(im)
    if not ims:return None
    out=stack(ims,-round(10*u) if k not in ('news','navy','crispred') else round(3*u),'left' if k in ('news','vividblue') else 'center')
    if k=='brightyellow':
        extra=round(28*u);z=Image.new('RGBA',(out.width+extra*2,out.height));z.alpha_composite(out,(extra,0));d=ImageDraw.Draw(z)
        for x,sign in [(extra*.55,-1),(z.width-extra*.55,1)]:
            d.line((x-sign*5*u,12*u,x+sign*4*u,35*u),fill='#FFFDEE',width=max(1,round(9*u)));d.line((x-sign*5*u,12*u,x+sign*4*u,35*u),fill='#18180D',width=max(1,round(6*u)));d.line((x-sign*5*u,12*u,x+sign*4*u,35*u),fill='#FFE628',width=max(1,round(3*u)))
            y=z.height*.66;r=5*u;d.polygon([(x,y-r),(x+r,y),(x,y+r),(x-r,y)],fill='#FFE628',outline='#FFFEEE')
        out=z
    return out


def news_tiles(p,e):
    from template_scenes import texts
    c=p.variant['scene_system'];u=p.unit;value=texts(e)
    # Per-character paper tiles, not a large generic rectangle.
    for scale in (1,.96,.92,.88,.84,.8,.76,.72):
        ims=[line(p,[dict(text=ch)],c['body_size']*scale,maxw=p.w*.86) for ch in value]
        # Crop only transparent padding; retain glyph ink and add measured tile padding.
        ims=[plate(i.crop(i.getbbox()),'#F4F0E3',max(2,round(3*u)),outline='#B4A780') if i.getbbox() else Image.new('RGBA',(max(1,round(8*u)),max(1,round(40*u)))) for i in ims]
        gap=max(1,round(2*u));w=sum(i.width for i in ims)+gap*(len(ims)-1)
        if w<=p.w*.86:break
    else:raise ValueError('News tiles too long; resegment')
    h=max(i.height for i in ims);out=Image.new('RGBA',(w,h));x=0
    for im in ims:out.alpha_composite(im,(x,(h-im.height)//2));x+=im.width+gap
    return out


def translation(p,e):
    c=p.variant['scene_system'];rows,size=wrap_text(p,e['text'],c['translation_size'],p.w*.82-26*p.unit)
    return stack([line(p,[dict(text=t)],size,'translation',maxw=p.w*.82) for t in rows],-round(12*p.unit))


def layout(p):
    from template_scenes import _box,texts
    c=p.variant['scene_system'];k=c['kind'];u=p.unit;entries=[]
    def add(im,x,y,a,b,role,animation='fade'):
        x=round(x);y=round(y);env=round(10*u) if animation in ('soft','label') else 0
        entries.append(dict(image=im,x=x,y=y,start=a,end=b,role=role,animation=animation,box=_box(im,x,y,env)))
    ti=title(p)
    if ti:add(ti,(p.w-ti.width)/2,p.h*c['title_y']-ti.height/2,0,min(p.p['duration'],p.p.get('title_duration',c['title_duration'])),'title')
    tr={e['phrase_id']:e for e in p.p.get('scene_translations',[])}
    for g in p.p['scene_captions']:
        blocks=[]
        for j,e in enumerate(g['phrases']):
            mode=e.get('mode','normal');runs=e.get('runs') or [dict(text=texts(e),role='body')]
            if k=='news':
                im=news_tiles(p,e) if mode=='normal' else plate(line(p,runs,c['body_size'],'body','display',p.w*.82),'#F5F1E5')
            elif k=='vividblue' and mode=='label':im=plate(line(p,[dict(text=texts(e))],c['tag_size'],'body','label',p.w*.82),'#624333')
            else:im=line(p,runs,c['body_size'],'body',mode)
            en=translation(p,tr[e['id']]) if k in BILINGUAL else None
            blocks.append((e,im,en))
        inner=-round(10*u);gap=round(22*u) if k in ('luxury','navy','crispred') else round(3*u)
        total=sum(im.height+(en.height+inner if en else 0) for _,im,en in blocks)+gap*(len(blocks)-1)
        y=p.h*c['caption_y']-total/2
        for j,(e,im,en) in enumerate(blocks):
            w=max(im.width,en.width if en else 0)
            if k in ('luxury','crispred','vividblue','navy') and len(blocks)>1:x=p.w*.065 if j%2==0 else p.w*.935-w
            elif k=='news' and e.get('mode')=='display':x=p.w*.93-w
            else:x=(p.w-w)/2
            anim='soft' if k in ('luxury','navy','crispred') else 'pop' if k=='brightyellow' else 'fade'
            add(im,x if k not in BILINGUAL else (p.w-im.width)/2,y,e['start'],e['end'],'caption',anim)
            if en:
                te=tr[e['id']];add(en,(p.w-en.width)/2,y+im.height+inner,te['start'],te['end'],'translation')
            y+=im.height+(en.height+inner if en else 0)+gap
    for e in p.p.get('scene_tags',[]):
        im=line(p,[dict(text=e['text'],role='sticker')],c['tag_size'],'sticker','tag',p.w*.38)
        if k=='news':
            # Original broadcast-like lower-third; quotes source, no news-authority claim.
            im=plate(im,'#125AC2');extra=round(36*u);out=Image.new('RGBA',(im.width+extra,im.height+round(5*u)),(244,241,232,255));out.alpha_composite(im,(extra,0));d=ImageDraw.Draw(out);cx=extra/2;cy=im.height/2;r=12*u
            d.ellipse((cx-r,cy-r,cx+r,cy+r),outline='#1A61AA',width=max(1,round(2*u)));d.arc((cx-r/2,cy-r,cx+r/2,cy+r),0,360,fill='#1A61AA');d.line((cx-r,cy,cx+r,cy),fill='#1A61AA');d.rectangle((0,out.height-3*u,out.width*.55,out.height),fill='#D1493D');d.rectangle((out.width*.55,out.height-3*u,out.width,out.height),fill='#E3C54A');im=out
        elif k=='crispred':
            d=ImageDraw.Draw(im);d.polygon([(8*u,im.height-8*u),(im.width-5*u,im.height-8*u),(im.width-12*u,im.height-4*u),(4*u,im.height-4*u)],fill='#C6747B')
        elif k=='navy':im=plate(im,'#1B3354')
        elif k=='vividblue':im=plate(im,'#624333')
        else:im=plate(im,(20,20,18,120))
        x=p.w*.94-im.width if e.get('side','right')=='right' else p.w*.06
        add(im,x,p.h*c['tag_y']-im.height/2,e['start'],e['end'],'tag','label')
    return entries
