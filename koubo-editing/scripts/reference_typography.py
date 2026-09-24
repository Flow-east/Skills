"""Two sample-led typography families, using licensed/local substitute fonts.
No copied sample video, proprietary font extraction, or claim of exact official fonts.
"""
import math
from PIL import Image,ImageDraw


def outlined(d,xy,text,font,kind,fill,u,anchor='lm',title=False):
    x,y=xy
    if kind=='pink':
        # Offset dark extrusion as in sample; no paper, underline or backing card.
        for shift in (4,3,2):
            d.text((x+shift*u,y+shift*u),text,font=font,anchor=anchor,fill='#161219',stroke_width=max(1,round(1.5*u)),stroke_fill='#161219')
        d.text((x,y),text,font=font,anchor=anchor,fill=fill,stroke_width=max(1,round(.55*u)),stroke_fill='#3B2935')
    elif title:
        for shift in (5,4,3):d.text((x+shift*u,y+shift*u),text,font=font,anchor=anchor,fill='#55452D',stroke_width=max(1,round(2*u)),stroke_fill='#55452D')
        d.text((x,y),text,font=font,anchor=anchor,fill='#FFF0C2',stroke_width=max(1,round(1.3*u)),stroke_fill='#D5BF86')
    else:
        d.text((x+2*u,y+3*u),text,font=font,anchor=anchor,fill='#51432C',stroke_width=max(1,round(6*u)),stroke_fill='#51432C')
        d.text((x,y),text,font=font,anchor=anchor,fill=fill,stroke_width=max(1,round(4*u)),stroke_fill='#FFF8DE')
        d.text((x,y),text,font=font,anchor=anchor,fill=fill)


def split_runs(runs,at):
    left=[];right=[];cursor=0
    for r in runs:
        text=r['text'];cut=max(0,min(len(text),at-cursor))
        if cut:left.append(dict(r,text=text[:cut]))
        if cut<len(text):right.append(dict(r,text=text[cut:]))
        cursor+=len(text)
    return left,right


def stack_lines(runs,boundaries=None,authored_break=None):
    text=''.join(r['text'] for r in runs)
    if authored_break is not None:
        if not isinstance(authored_break,int) or not 0<authored_break<len(text):raise ValueError('Invalid authored caption line break')
        cursor=0
        for r in runs:
            end=cursor+len(r['text'])
            if r.get('style') in ('keyword','accent') and cursor<authored_break<end:raise ValueError('Authored line break splits emphasized phrase')
            cursor=end
        return list(split_runs(runs,authored_break))
    if len(text)<7:return [runs]
    # Prefer a complete prefix before the first emphasized phrase. Never split keyword.
    total=0;candidates=[];blocked=set()
    for r in runs:
        if r.get('style') in ('keyword','accent'):
            if 2<=total<=len(text)-3:candidates.append(total)
            blocked.update(range(total+1,total+len(r['text'])))
        total+=len(r['text'])
    if not candidates:
        choices=boundaries or list(range(2,len(text)-2))
        candidates=[i for i in choices if 2<=i<=len(text)-3 and i not in blocked and text[i] not in '，。！？,!?；;']
    if not candidates:return [runs]
    split=min(candidates,key=lambda x:abs(x-len(text)*.43))
    return list(split_runs(runs,split))


def caption_sprite(painter,ev,cfg):
    u=painter.unit;pad=round(22*u);kind='pink' if cfg['kind']=='pink_stack' else 'gold'
    runs=ev.get('runs') or [dict(text=ev.get('text',''),style=ev.get('style','base'))]
    source_lines=stack_lines(runs,ev.get('word_boundaries'),ev.get('line_break')) if kind=='pink' else [runs]
    maxw=painter.w*cfg['max_width']-2*pad
    for factor in (1,.96,.92,.88,.84,.80,.76,.72,.68,.64):
        lines=[]
        for line in source_lines:
            measured=[]
            for r in line:
                kw=r.get('style') in ('keyword','accent');size=cfg['keyword_size'] if kw else cfg['size']
                f=painter.font(size*factor,'keyword' if kw else 'body');measured.append((r,f))
            lines.append(measured)
        widths=[sum(f.getlength(r['text']) for r,f in ln) for ln in lines]
        stagger=28*u if kind=='pink' and len(lines)>1 else 0
        if max(widths)+stagger<=maxw:break
    else:raise ValueError('Reference caption too long; author a phrase break')
    heights=[max(f.size for r,f in ln)*cfg['line_gap'] for ln in lines]
    w=math.ceil(max(widths)+stagger)+2*pad;h=math.ceil(sum(heights))+2*pad
    im=Image.new('RGBA',(w,h));d=ImageDraw.Draw(im);y=pad
    for i,(ln,lw,lh) in enumerate(zip(lines,widths,heights)):
        x=(pad if i==0 else w-pad-lw) if len(lines)>1 else (w-lw)/2
        for r,f in ln:
            kw=r.get('style') in ('keyword','accent')
            fill=('#F8E989' if ev.get('tone')=='warning' else '#F3A1C4') if kw else '#FFFFFF'
            if kind=='gold':fill='#54472D'
            outlined(d,(x,y+lh/2),r['text'],f,kind,fill,u)
            x+=f.getlength(r['text'])
        y+=lh
    return im,cfg


def title_sprite(painter,cfg):
    u=painter.unit;pad=round(18*u);text=painter.p['title'];kind='pink' if cfg['kind']=='pink_headline' else 'gold'
    # Use semantic punctuation, not one orphan word at the end of a line.
    split=next((i+1 for i,c in enumerate(text[:-1]) if c in '，,：:'),None)
    lines=[text[:split].rstrip('，,：:'),text[split:]] if split else [text]
    maxw=painter.w*cfg['max_width']-2*pad
    fonts=[painter.fit(line,cfg['size']*(.83 if i and kind=='pink' else 1),maxw,'title') for i,line in enumerate(lines)]
    heights=[f.size*1.2 for f in fonts];w=math.ceil(max(f.getlength(t) for t,f in zip(lines,fonts)))+2*pad;h=math.ceil(sum(heights))+2*pad
    subtitle=painter.p.get('subtitle');sf=painter.fit(subtitle,24,maxw,'body') if subtitle else None
    if sf:w=max(w,math.ceil(sf.getlength(subtitle))+2*pad);h+=sf.size+12
    im=Image.new('RGBA',(w,h));d=ImageDraw.Draw(im);y=pad
    for i,(text,f,lh) in enumerate(zip(lines,fonts,heights)):
        fill='#F3A1C4' if kind=='pink' and i==0 else '#FFFFFF'
        outlined(d,(w/2,y+lh/2),text,f,kind,fill,u,anchor='mm',title=True);y+=lh
    if sf:outlined(d,(w/2,y+sf.size/2+4),subtitle,sf,kind,'#FFFFFF',u,anchor='mm')
    return im


def sticker_sprite(painter,ev,cfg):
    u=painter.unit;kind='pink' if cfg['shape']=='pink_word' else 'gold';limit=painter.variant['design_system']['sticker']
    symbol=ev.get('symbol');extra=38*u if symbol else 0
    f=painter.fit(ev['text'],cfg['size'],painter.w*ev.get('max_width',limit['max_width'])-40*u-extra,'sticker');pad=round(18*u)
    w=math.ceil(f.getlength(ev['text'])+extra)+2*pad;h=math.ceil(f.size*1.45)+2*pad
    im=Image.new('RGBA',(w,h));d=ImageDraw.Draw(im)
    outlined(d,(pad,h/2),ev['text'],f,kind,'#F3A1C4' if kind=='pink' else '#54472D',u)
    if symbol:
        if symbol!='warning':raise ValueError('Unsupported authored reference sticker symbol')
        x=w-pad-12*u;y=h/2
        # Original procedural warning mark, not a copied licensed image or glyph.
        d.line((x,y-19*u,x,y+7*u),fill='#292224',width=max(1,round(12*u)))
        d.line((x,y-19*u,x,y+7*u),fill='#FA785B',width=max(1,round(7*u)))
        d.ellipse((x-5*u,y+13*u,x+5*u,y+23*u),fill='#FA785B',outline='#292224',width=max(1,round(2*u)))
    if cfg.get('angle'):im=im.rotate(cfg['angle'],resample=Image.Resampling.BICUBIC,expand=True)
    im=im.crop(im.getchannel('A').getbbox());factor=min(1,painter.w*ev.get('max_width',limit['max_width'])/im.width,painter.h*limit['max_height']/im.height)
    if factor<1:im=im.resize((max(1,round(im.width*factor)),max(1,round(im.height*factor))),Image.Resampling.LANCZOS)
    return im
