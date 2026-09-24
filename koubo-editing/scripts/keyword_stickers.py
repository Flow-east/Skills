"""Small, template-bound typographic stickers on a separate screen-fixed layer.
Semantic selection is authored; this module never promotes every highlighted word.
"""
import math
from PIL import Image,ImageDraw


def validate(painter):
    p=painter.p
    for ev in p.get('keyword_stickers',[]):
        a,b=ev.get('start'),ev.get('end');txt=ev.get('text')
        if not all(isinstance(v,(int,float)) and math.isfinite(v) for v in (a,b)) or not 0<=a<b<=p['duration']:
            raise ValueError('Keyword sticker requires valid output times')
        if not isinstance(txt,str) or not 1<=len(txt.strip())<=10:
            raise ValueError('Keyword sticker must be a short, nonempty phrase')
        if not str(ev.get('reason','')).strip():raise ValueError('Keyword sticker needs semantic reason')
        pos=ev.get('position',[.5,.105])
        if len(pos)!=2 or not all(isinstance(v,(int,float)) and math.isfinite(v) and 0<=v<=1 for v in pos):
            raise ValueError('Invalid keyword sticker position')
        if not .15<=ev.get('max_width',.46)<=.55:raise ValueError('Sticker width outside supported safe range')
        if ev.get('time_space','output')!='output':raise ValueError('Sticker time must use output clock')
        # Fail rather than silently hide a tag under another tag at the same time.
    events=sorted(p.get('keyword_stickers',[]),key=lambda e:e['start'])
    if any(a['end']>b['start'] for a,b in zip(events,events[1:])):
        raise ValueError('Overlapping keyword stickers require editorial review')


def badge(painter,ev):
    cfg=painter.variant.get('sticker_style',{})
    kind=cfg.get('shape','cutout');u=painter.unit
    if kind in ('pink_word','gold_word'):
        from reference_typography import sticker_sprite
        return sticker_sprite(painter,ev,cfg)
    font=painter.fit(ev['text'],cfg.get('size',62),painter.w*ev.get('max_width',painter.variant.get('design_system',{}).get('sticker',{}).get('max_width',.46))-70*u,'sticker')
    w=round(font.getlength(ev['text'])+70*u);h=round(font.size*(1.35 if kind=='annotation' else 1.65)+24*u)
    im=Image.new('RGBA',(w+36*round(u),h+36*round(u)));d=ImageDraw.Draw(im)
    left=12*u;top=12*u;right=left+w;bottom=top+h
    fill=cfg.get('fill',painter.theme['accent']);ink=cfg.get('ink','#181820');border=cfg.get('border','#FFFFFF')
    if kind=='cutout':
        pts=[(left+8*u,top+7*u),(right-9*u,top),(right,top+24*u),(right-5*u,bottom-5*u),(left+18*u,bottom),(left,bottom-23*u)]
        shadow=[(x+5*u,y+6*u) for x,y in pts];d.polygon(shadow,fill='#191921');d.line(shadow+[shadow[0]],fill='#191921',width=round(12*u))
        d.polygon(pts,fill=fill);d.line(pts+[pts[0]],fill=border,width=round(8*u),joint='curve')
    elif kind=='bubble':
        d.rounded_rectangle((left+4*u,top+5*u,right+4*u,bottom+5*u),radius=round(h*.4),fill='#19372C')
        d.rounded_rectangle((left,top,right,bottom),radius=round(h*.4),fill=fill,outline=border,width=round(7*u))
        d.ellipse((left+12*u,top+14*u,left+21*u,top+23*u),fill=border)
        d.ellipse((right-22*u,bottom-25*u,right-13*u,bottom-16*u),fill=border)
    elif kind=='paper':
        pts=[(left,top),(right,top),(right,bottom-8*u)]
        pts.extend((right-i*w/12,bottom-(i%2)*8*u) for i in range(13));pts.append((left,top))
        d.polygon([(x+3*u,y+4*u) for x,y in pts],fill='#342C28');d.polygon(pts,fill=fill)
        d.line((left+15*u,bottom-21*u,right-15*u,bottom-21*u),fill=cfg.get('rule','#B76549'),width=max(1,round(2*u)))
    elif kind=='annotation':
        d.line([(left+10*u,bottom-10*u),(right*.6,bottom-7*u),(right-10*u,bottom-14*u)],fill=border,width=max(1,round(3*u)))
        d.line([(left+15*u,top+9*u),(left-3*u,top+9*u),(left-3*u,top+28*u)],fill=border,width=max(1,round(3*u)))
    elif kind=='label':
        d.rectangle((left,top,right,bottom),fill=fill)
        d.line((left,top,left,bottom),fill=border,width=max(1,round(5*u)))
        d.line((left,bottom,right,bottom),fill=border,width=max(1,round(2*u)))
    elif kind=='seal':
        d.rounded_rectangle((left,top,right,bottom),radius=round(8*u),fill=fill,outline=border,width=round(3*u))
        d.rectangle((left+7*u,top+7*u,right-7*u,bottom-7*u),outline=border,width=max(1,round(u)))
    else:raise ValueError('Unknown template sticker shape: '+kind)
    d.text(((left+right)/2,(top+bottom)/2-2*u),ev['text'],font=font,anchor='mm',fill=ink,
           stroke_width=round(cfg.get('text_stroke',0)*u),stroke_fill=cfg.get('text_outline',ink))
    angle=cfg.get('angle',-3)
    if angle:im=im.rotate(angle,resample=Image.Resampling.BICUBIC,expand=True)
    bbox=im.getchannel('A').getbbox()
    im=im.crop(bbox)
    design=painter.variant.get('design_system',{}).get('sticker',{})
    if design:
        factor=min(1,painter.w*ev.get('max_width',design['max_width'])/im.width,painter.h*design.get('max_height',.14)/im.height)
        if factor<1:im=im.resize((max(1,round(im.width*factor)),max(1,round(im.height*factor))),Image.Resampling.LANCZOS)
    return im


def placement(painter,ev,layer):
    if painter.variant.get('design_system'):
        from design_system import sticker_position
        return sticker_position(painter,ev,layer,getattr(painter,'_design_time',ev['start']))
    x,y=ev.get('position',[.5,.105]);x=x*painter.w-layer.width/2;y=y*painter.h-layer.height/2
    margin=12*painter.unit
    x=max(margin,min(painter.w-margin-layer.width,x));y=max(margin,min(painter.h-margin-layer.height,y))
    if layer.width>painter.w-2*margin or layer.height>painter.h-2*margin:raise ValueError('Sticker exceeds screen safe area')
    return round(x),round(y)


def paint(painter,canvas,t):
    for i,ev in enumerate(painter.p.get('keyword_stickers',[])):
        if not ev['start']<=t<ev['end']:continue
        key=('keyword_sticker',i)
        if key not in painter.layers:painter.layers[key]=badge(painter,ev)
        sprite=painter.layers[key];age=t-ev['start'];remaining=ev['end']-t
        if painter.variant.get('design_system'):
            from design_system import paint_sticker
            paint_sticker(painter,canvas,ev,t)
            continue
        def ease(x):x=max(0,min(1,x));return 1-(1-x)**3
        opacity=min(ease(age/.16),ease(remaining/.14))
        scale=.86+.14*ease(age/.24)
        layer=sprite.resize((max(1,round(sprite.width*scale)),max(1,round(sprite.height*scale))),Image.Resampling.LANCZOS)
        layer.putalpha(layer.getchannel('A').point(lambda a:round(a*opacity)))
        x,y=placement(painter,ev,layer);canvas.alpha_composite(layer,(x,y))
