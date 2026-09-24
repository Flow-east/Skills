#!/usr/bin/env python3
"""Plan-driven animated cards, timed captions, sticker animation and muxed audio.
No source-specific text/times/paths. ffmpeg needs only basic video/audio filters.
"""
import argparse, json, math, subprocess, sys, wave
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageColor
from timeline import load_plan, compile_plan, base_filter, write_srt, caption_groups, probe


def run(cmd, log):
    with Path(log).open('ab') as f: subprocess.run(cmd,stdout=f,stderr=f,check=True)


def ease(t): return 1-(1-max(0,min(1,t)))**3


def color(hex_value,alpha=255): return (*ImageColor.getrgb(hex_value),alpha)


class Painter:
    def __init__(self,p):
        self.p=p; self.w=p['width']; self.h=p['height']; self.unit=self.w/720; self._active_clip=None
        themes=json.loads((Path(__file__).resolve().parent.parent/'assets/themes.json').read_text())
        self.theme=dict(themes[p['template']]); self.fonts={};
        profiles=json.loads((Path(__file__).resolve().parent.parent/'assets/style_profiles.json').read_text())
        self.profile=dict(profiles.get(p.get('style_profile',''),{}))
        self.variant={}
        if p.get('template_variant'):
            from template_catalog import get as get_template
            self.variant=get_template(p['template_variant'])
            # A selected template is authoritative; legacy profile cannot overwrite it.
            self.profile.update({k:self.variant[k] for k in
                ('accent','text','stroke','base_size','keyword_size','enter') if k in self.variant})
        for k in ('accent','text','stroke'):
            if k in self.profile: self.theme[k]=self.profile[k]
        if p.get('camera_motion') is not None:
            from camera_motion import validate
            validate(p['camera_motion'],p['duration'])
        from design_system import validate as validate_design
        validate_design(self)
        from template_scenes import validate as validate_scenes
        validate_scenes(self)
        from keyword_stickers import validate as validate_stickers
        validate_stickers(self)
        self.layers={}; self.sprites={}; self.design_boxes=[]
        self.groups={c['id']:caption_groups(c,p.get('caption_chars',13)) for c in p['clips']}
        for c in p['clips']:
            for st in c.get('stickers',[]):
                q=Path(st['path']); im=Image.open(q).convert('RGBA'); alpha=im.getchannel('A')
                if alpha.getextrema()[0]==255: raise ValueError(f'Sticker is opaque: {q}; do not claim transparency')
                bbox=alpha.getbbox()
                if not bbox: raise ValueError('Empty sticker')
                self.sprites[str(q)]=im.crop(bbox)
        from illustrations import load as load_illustrations
        self.illustrations=load_illustrations(self)
        self.privacy=p['_privacy']

    def font_path(self,role='body'):
        path=Path(self.variant.get(role+'_font',self.variant.get('font',self.p['font'])))
        return str(path if path.is_absolute() else Path(__file__).resolve().parent.parent/path)

    def font_index(self,role='body'):
        return int(self.variant.get(role+'_font_index',self.variant.get('font_index',0)))

    def font_weight(self,role='body'):
        return self.variant.get(role+'_font_weight',self.variant.get('font_weight'))

    def font(self,size,role='body'):
        px=max(12,round(size*self.unit)); path=self.font_path(role)
        index=self.font_index(role);weight=self.font_weight(role);key=(px,role,path,index,weight)
        if key not in self.fonts:
            from font_guard import configure_weight
            self.fonts[key]=configure_weight(ImageFont.truetype(path,px,index=index),weight)
        return self.fonts[key]

    def font_preflight(self,output_dir):
        from font_guard import audit, sha256
        if self.variant.get('_contract'):
            from template_contracts import validate
            validate(self.variant['_contract'],verify_assets=True)
        report=audit(self)
        root=Path(__file__).resolve().parent.parent
        provenance={str(path.relative_to(root)):sha256(path) for path in
            [*sorted((root/'scripts').glob('*.py')),*sorted((root/'assets').rglob('*.json'))]}
        report.update(template=self.variant,theme=self.theme,skill_root=str(root),files=provenance)
        (Path(output_dir)/'font_qa.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
        if not report['passed']:
            failures=[f"{r['font']}: {''.join(r['missing']+r['invalid'])}" for r in report['fonts'] if not r['passed']]
            raise ValueError('FONT_COVERAGE_FAILED: '+ '; '.join(failures))
        return report

    def fit(self,text,size,max_width,role='body'):
        f=self.font(size,role)
        while f.getlength(text)>max_width and size>14:
            size-=1; f=self.font(size,role)
        if f.getlength(text)>max_width: raise ValueError('Text cannot fit within safe area')
        return f

    def panel(self,key,kind,c=None):
        if key in self.layers: return self.layers[key]
        u=self.unit; theme=self.theme; pw=round(self.w*.86)
        if kind=='title':
            ph=round(185*u); im=Image.new('RGBA',(pw,ph)); d=ImageDraw.Draw(im)
            d.rounded_rectangle((0,0,pw-1,ph-1),radius=round(24*u),fill=color(theme['panel'],238))
            d.rounded_rectangle((round(22*u),round(22*u),round(28*u),ph-round(22*u)),radius=3,fill=color(theme['accent']))
            if self.p.get('eyebrow'): d.text((pw/2,43*u),self.p['eyebrow'],font=self.fit(self.p['eyebrow'],22,pw-55*u,'title'),anchor='mm',fill=color(theme['secondary']))
            title=self.p.get('title','')
            d.text((pw/2,104*u),title,font=self.fit(title,57,pw-60*u,'title'),anchor='mm',fill=color(theme['accent']),stroke_width=round(u),stroke_fill=color(theme['accent']))
            if self.p.get('subtitle'): d.text((pw/2,151*u),self.p['subtitle'],font=self.fit(self.p['subtitle'],22,pw-40*u,'body'),anchor='mm',fill=color(theme['text']))
        else:
            ph=round(156*u); im=Image.new('RGBA',(pw,ph)); d=ImageDraw.Draw(im); card=c['card']
            d.rounded_rectangle((0,0,pw-1,ph-1),radius=round(23*u),fill=color(theme['panel'],238),outline=color(theme['accent'],120),width=round(2*u))
            d.rounded_rectangle((18*u,18*u,77*u,72*u),radius=round(12*u),fill=color(theme['accent']))
            d.text((47*u,45*u),f'{c["index"]:02}',font=self.font(29),anchor='mm',fill=color(theme['panel']))
            d.text((96*u,43*u),card['label'],font=self.fit(card['label'],27,pw-120*u,'body'),anchor='lm',fill=color(theme['secondary']))
            d.text((28*u,109*u),card['value'],font=self.fit(card['value'],60,pw-64*u,'keyword'),anchor='lm',fill=color(theme['accent']),stroke_width=round(u),stroke_fill=color(theme['accent']))
        self.layers[key]=im; return im

    def overlay(self,canvas,layer,x,y,age,remaining,scale_in=False):
        opacity=min(ease(age/.14),ease(remaining/.10))
        if opacity<=0: return
        scale=(.86+.14*ease(age/.2)) if scale_in else 1.
        dx=round(layer.width*(1-scale)/2); dy=round(20*self.unit*(1-ease(age/.18)))
        if scale!=1: layer=layer.resize((max(1,round(layer.width*scale)),max(1,round(layer.height*scale))),Image.Resampling.LANCZOS)
        if opacity<1:
            layer=layer.copy(); layer.putalpha(layer.getchannel('A').point(lambda n: round(n*opacity)))
        canvas.alpha_composite(layer,(round(x)+dx,round(y)+dy))

    def _draw_text(self, canvas, text, x, y, size, fill, stroke='#17121C', sw=3,
                   anchor='mm', shadow=None, italic=False):
        d=ImageDraw.Draw(canvas); f=self.fit(text,size,self.w*.92,'body')
        px=max(1,round(sw*self.unit))
        if shadow:
            sx,sy=shadow
            d.text((x+sx*self.unit,y+sy*self.unit),text,font=f,anchor=anchor,
                   fill=color(shadow[2] if len(shadow)>2 else '#000000',180),stroke_width=px,
                   stroke_fill=color('#000000',150))
        d.text((x,y),text,font=f,anchor=anchor,fill=color(fill),stroke_width=px,
               stroke_fill=color(stroke))

    def _event_pos(self, ev, c=None):
        pos=ev.get('position')
        coords={'top_left':(.16,.18),'top_center':(.5,.18),'top_right':(.84,.18),
                'middle_left':(.24,.52),'middle_center':(.5,.52),'middle_right':(.76,.52),
                'lower_left':(.22,.78),'lower_center':(.5,.78),'lower_right':(.78,.78)}
        if isinstance(pos,list): return pos[0]*self.w,pos[1]*self.h
        if not pos and c and c.get('focus'):
            fx=c['focus'][0]; pos='lower_right' if fx<.38 else ('lower_left' if fx>.62 else 'lower_center')
        q=coords.get(pos,coords['lower_center']); return q[0]*self.w,q[1]*self.h

    def rich_caption(self, canvas, ev, t):
        if self.variant.get('design_system'):
            from design_system import paint_caption
            return paint_caption(self,canvas,ev,t)
        a,b=float(ev['start']),float(ev['end'])
        if not a<=t<b: return
        age=t-a; left=b-t; enter=ev.get('enter','pop')
        op=min(ease(age/float(ev.get('in_ms',160)/1000)),ease(left/float(ev.get('out_ms',100)/1000)))
        if op<=0:return
        x,y=self._event_pos(ev, self._active_clip); runs=ev.get('runs')
        if not runs:
            runs=[{'text':ev.get('text',''),'style':'keyword' if ev.get('style')=='keyword' else 'base'}]
        # Wrap rich-text runs into up to two lines instead of shrinking a long sentence into illegibility.
        forced_lines=None
        if ev.get('layout')=='scenario_choice' and len(runs)>=2:
            # Keep the scenario label above the answer, matching the reference samples.
            split=max(1,len(runs)-1)
            top=[dict(r, size=float(r.get('size',40))*.78) for r in runs[:split]]
            bottom=[dict(r, size=float(r.get('size',52))*1.12) for r in runs[split:]]
            forced_lines=[top,bottom]
            ev=dict(ev); ev['line_gap']=ev.get('line_gap',1.05); ev['max_width']=ev.get('max_width',.82)
        measured=[]
        for r in runs:
            size=float(r.get('size',ev.get('size',43))); role='keyword' if r.get('style') in ('keyword','accent') else 'body'; f=self.fit(r.get('text',''),size,self.w*.92,role); measured.append((r,f))
        maxw=self.w*float(ev.get('max_width',.86)); lines=[]; cur=[]; width=0
        for r,f in measured:
            rw=f.getlength(r.get('text',''))
            if cur and width+rw>maxw and len(lines)<1: lines.append(cur); cur=[]; width=0
            cur.append((r,f)); width+=rw
        if cur: lines.append(cur)
        if forced_lines is not None:
            # Keep the scenario label above the answer, but retain measured fonts.
            split=max(1,len(measured)-1)
            lines=[measured[:split], measured[split:]]
        x,y=self._event_pos(ev, self._active_clip)
        line_gap=float(ev.get('line_gap',1.08)); total_h=sum(max((f.size for r,f in ln), default=1)*line_gap for ln in lines)
        max_line_w=max((sum(f.getlength(r.get('text','')) for r,f in ln) for ln in lines),default=1)
        safe_w=self.w*float(ev.get('max_width',.86))
        fit_scale=min(1.0,safe_w/max(1,max_line_w))
        # Final safe-area clamp includes stroke/extrusion and the optional English line.
        pad=max(10*self.unit, float(ev.get('stroke',3))*self.unit+5*self.unit)
        x=min(self.w-pad-max_line_w*fit_scale/2, max(pad+max_line_w*fit_scale/2, x))
        english=ev.get('english')
        english_h=0
        if english:
            ef=self.fit(english.get('text',''),float(english.get('size',22)),self.w*.72,'body')
            english_h=ef.size*.9
        half_h=(total_h*fit_scale+english_h+pad)/2
        y=min(self.h-pad-half_h, max(pad+half_h, y))
        scale=((.90+.10*ease(age/.18)) if enter in ('pop','scale') else 1)*fit_scale
        yy=y-(10*self.unit*(1-ease(age/.18))) if enter in ('pop','rise') else y
        layer=Image.new('RGBA',(self.w,self.h)); ld=ImageDraw.Draw(layer)
        line_y=yy-total_h/2
        for line in lines:
            line_w=sum(f.getlength(r.get('text','')) for r,f in line); xx=x-line_w/2
            for r,f in line:
                txt=r.get('text',''); sty=r.get('style','base'); fill=r.get('fill', self.theme['accent'] if sty in ('keyword','accent') else self.theme['text'])
                default_sw=self.variant.get('keyword_stroke_width' if sty in ('keyword','accent') else 'stroke_width',3)
                sw=float(r.get('stroke',ev.get('stroke',default_sw))); px=max(1,round(sw*self.unit))
                if self.variant.get('shadow') and sty in ('keyword','accent'):
                    ld.text((xx+3*self.unit,line_y+4*self.unit),txt,font=f,anchor='lm',fill=color('#241A1A'),stroke_width=px+1,stroke_fill=color('#241A1A'))
                if r.get('extrude',ev.get('extrude',False)):
                    ld.text((xx+3*self.unit,line_y+4*self.unit),txt,font=f,anchor='lm',fill=color(r.get('extrude_fill','#261B27')),stroke_width=px,stroke_fill=color('#261B27'))
                ld.text((xx,line_y),txt,font=f,anchor='lm',fill=color(fill),stroke_width=px,stroke_fill=color(r.get('stroke_fill',self.theme.get('stroke','#17121C'))))
                if r.get('underline'):
                    ld.line((xx,line_y+f.size*.58,xx+f.getlength(txt),line_y+f.size*.58),fill=color(fill),width=max(1,round(self.unit*2)))
                xx+=f.getlength(txt)
            line_y+=max(f.size for r,f in line)*line_gap
        # Lightweight procedural accents model the samples' rays/sparkles without external assets.
        effect=ev.get('effect')
        if effect in ('sparkle','burst','rays'):
            ed=ImageDraw.Draw(layer); seed=sum(ord(ch) for ch in ''.join(r.get('text','') for r in runs)); count=8 if effect!='rays' else 6
            import random
            rng=random.Random(seed); radius=float(ev.get('effect_radius',85))*self.unit
            for k in range(count):
                ang=2*math.pi*k/count + rng.uniform(-.12,.12); rr=radius*(.65+rng.random()*.35)
                sx=x + math.cos(ang)*rr; sy=y + math.sin(ang)*rr*.45
                if effect=='rays':
                    ex=x + math.cos(ang)*(rr+18*self.unit); ey=y + math.sin(ang)*(rr+18*self.unit)*.45
                    ed.line((sx,sy,ex,ey),fill=color(ev.get('effect_color',self.theme['accent']),round(190*op)),width=max(1,round(2*self.unit)))
                else:
                    r=(3+2*rng.random())*self.unit; ed.ellipse((sx-r,sy-r,sx+r,sy+r),fill=color(ev.get('effect_color',self.theme['accent']),round(210*op)))
        if scale!=1: layer=layer.resize((round(self.w*scale),round(self.h*scale)),Image.Resampling.LANCZOS)
        if op<1: layer.putalpha(layer.getchannel('A').point(lambda n: round(n*op)))
        canvas.alpha_composite(layer,(round((1-scale)*self.w/2),round((1-scale)*self.h/2)))
        # English is an independent, optional companion track rather than a forced translation.
        en=ev.get('english')
        if en and (en.get('start',a)<=t<en.get('end',b)):
            ed=ImageDraw.Draw(canvas)
            premium=self.p.get('template')=='service' or self.p.get('bilingual_style')=='premium'
            esize=float(en.get('size',18 if premium else 22)); ef=self.fit(en.get('text',''),esize,self.w*.72,'body')
            ex,ey=x,y+total_h/2+ef.size*(.72 if premium else .8)
            ealpha=170 if premium else 220
            ed.text((ex,ey),en['text'],font=ef,anchor='mm',fill=color(en.get('fill','#FFFFFF'),round(ealpha*op)),stroke_width=max(1,round(self.unit)),stroke_fill=color(self.theme.get('stroke','#17121C'),round(180*op)))

    def _auto_events(self, c):
        """Build conservative phrase events from authored words; semantic emphasis stays explicit."""
        events=[]; words=c.get('words',[]); keys=set(c.get('emphasis_words',[]))
        if not words: return events
        groups=caption_groups(c,self.p.get('caption_chars',13))
        for gi,g in enumerate(groups):
            runs=[]; joined=''.join(w['text'] for w in g); hit_ranges=[]
            for key in keys:
                at=joined.find(str(key))
                if at>=0: hit_ranges.append((at,at+len(str(key))))
            cursor=0
            for w in g:
                txt=w['text']; span=(cursor,cursor+len(txt)); cursor=span[1]
                emphasized=bool(w.get('emphasis')) or any(span[0]<e and span[1]>a for a,e in hit_ranges)
                runs.append({'text':txt,'style':'keyword' if emphasized else 'base',
                             'size':self.profile.get('keyword_size',66) if emphasized else self.profile.get('base_size',52),
                             'fill':self.theme['accent'] if emphasized else self.theme['text'],
                             'extrude':emphasized and bool(w.get('extrude',False))})
            # ASR tokens may be single characters, not typographic wrap boundaries.
            # Keep contiguous styled phrases atomic so a keyword is never split mid-word.
            merged=[]
            for r in runs:
                style={k:v for k,v in r.items() if k!='text'}
                if merged and {k:v for k,v in merged[-1].items() if k!='text'}==style:
                    merged[-1]['text']+=r['text']
                else:
                    merged.append(dict(r))
            runs=merged
            ev={'start':g[0]['start'],'end':(g[-1]['end'] if g[-1].get('end') else g[0]['start']+.8),
                'position':c.get('caption_position') or self.variant.get('layout_position', ('lower_left','lower_center','lower_right')[gi%3]),'runs':runs,
                'enter':c.get('caption_enter',self.profile.get('enter','pop')),
                'template_position':not bool(c.get('caption_position'))}
            ev['word_boundaries']=[]; cursor=0
            for word in g[:-1]:
                cursor+=len(word['text']); ev['word_boundaries'].append(cursor)
            ev['tone']=c.get('caption_tone','neutral')
            phrase=''.join(w['text'] for w in g)
            if phrase in self.p.get('caption_line_breaks',{}):ev['line_break']=self.p['caption_line_breaks'][phrase]
            ev['tone']=self.p.get('caption_tones',{}).get(phrase,ev['tone'])
            translation=self.p.get('english_map',{}).get(phrase)
            if translation: ev['english']={'text':translation,'start':ev['start']+.12,'end':ev['end'],'size':22}
            events.append(ev)
        return events

    def captions(self,canvas,c,t):
        events=c.get('caption_events') or self.p.get('caption_events')
        if not events and (self.p.get('reference_mode') or self.variant.get('design_system')):
            events=self._auto_events(c)
        if events:
            for ev in events:
                self.rich_caption(canvas,ev,t)
            return
        groups=self.groups[c['id']]
        for i,g in enumerate(groups):
            a=g[0]['start']; b=groups[i+1][0]['start'] if i+1<len(groups) else c['output_end']
            if not a<=t<b: continue
            text=''.join(w['text'] for w in g); f=self.fit(text,43,self.w*.88)
            total=f.getlength(text); x=(self.w-total)/2; y=self.h*self.theme['subtitle_y']
            d=ImageDraw.Draw(canvas); stroke=max(1,round(3*self.unit))
            for j,w in enumerate(g):
                end=g[j+1]['start'] if j+1<len(g) else b; active=w['start']<=t<end
                d.text((round(x),round(y)),w['text'],font=f,anchor='lm',fill=color(self.theme['accent'] if active else self.theme['text']),stroke_width=stroke,stroke_fill=(17,15,24,255)); x+=f.getlength(w['text'])
            return
        if not groups and c.get('caption',''):
            self._draw_text(canvas,c['caption'],self.w/2,self.h*self.theme['subtitle_y'],43,self.theme['text'])

    def paint(self,im,c,t):
        self._active_clip=c
        self.design_boxes=[]
        if self.p.get('camera_motion') is not None:
            from camera_motion import apply as apply_camera
            im=apply_camera(im,self.p['camera_motion'],t)
        else:
            # Legacy plans retain their look; new edits should author one output-clock track.
            z=c.get('zoom',1.)
            if z>1:
                z=1+(z-1)*ease((t-c['output_start'])/.4); cw=self.w/z; ch=self.h/z; fx,fy=c.get('focus',[.5,.5])
                x=max(0,min(self.w-cw,fx*self.w-cw/2)); y=max(0,min(self.h-ch,fy*self.h-ch/2))
                im=im.crop((round(x),round(y),round(x+cw),round(y+ch))).resize((self.w,self.h),Image.Resampling.LANCZOS)
        if self.variant.get('scene_system'):
            from template_scenes import paint as paint_scene
            from illustrations import paint as paint_illustrations
            return paint_illustrations(paint_scene(self,im,t),self.illustrations,t)
        canvas=im.convert('RGBA')
        # Optional canvas state events: circle portrait, dark surround, or blurred-band layouts.
        for ev in (c.get('viewport_events',[]) + self.p.get('viewport_events',[])):
            if not ev.get('start',0)<=t<ev.get('end',0): continue
            kind=ev.get('kind')
            if kind=='dim':
                shade=Image.new('RGBA',(self.w,self.h),(0,0,0,int(255*float(ev.get('alpha',.28))))); canvas=Image.alpha_composite(canvas,shade)
            elif kind=='circle':
                mask=Image.new('L',(self.w,self.h)); md=ImageDraw.Draw(mask); cx,cy=ev.get('center',[.5,.42]); rad=ev.get('radius',.34); md.ellipse(((cx-rad)*self.w,cy*self.h-rad*self.w,(cx+rad)*self.w,cy*self.h+rad*self.w),fill=255); circ=Image.new('RGBA',(self.w,self.h),ev.get('background','#F8F0DF')); circ.alpha_composite(canvas); circ.putalpha(mask); canvas=Image.alpha_composite(Image.new('RGBA',(self.w,self.h),ev.get('background','#F8F0DF')),circ)
            elif kind=='blur_band':
                from PIL import ImageFilter
                original=canvas.copy(); blurred=original.filter(ImageFilter.GaussianBlur(round(18*self.unit)))
                canvas=blurred; band_h=ev.get('band_height',.46)*self.h; top=round((self.h-band_h)/2)
                canvas.alpha_composite(original.crop((0,top,self.w,top+round(band_h))),(0,top))
        from privacy_masking import paint as paint_privacy
        canvas=paint_privacy(canvas,self.privacy,t,self.p['fps'])
        tdur=self.p.get('title_duration',2.0)
        if self.variant.get('design_system'):
            from design_system import paint_title
            paint_title(self,canvas,t)
        elif self.p.get('title') and t<tdur:
            if self.p.get('reference_mode'):
                title=self.p['title']; d=ImageDraw.Draw(canvas); op=min(ease(t/.18),ease((tdur-t)/.12))
                tf=self.fit(title,50,self.w*.82,'title'); x=self.w*.09; y=self.h*.10
                d.rounded_rectangle((x-12*self.unit,y-tf.size*.55,x+tf.getlength(title)+18*self.unit,y+tf.size*.58),radius=8*self.unit,fill=color(self.theme['accent'],round(235*op)))
                d.text((x,y),title,font=tf,anchor='lm',fill=color('#17121C',round(255*op)),stroke_width=max(1,round(2*self.unit)),stroke_fill=color('#FFFFFF',round(220*op)))
                if self.p.get('subtitle'):
                    sf=self.fit(self.p['subtitle'],24,self.w*.7,'body'); d.text((x,y+tf.size*.72),self.p['subtitle'],font=sf,anchor='lm',fill=color('#FFFFFF',round(240*op)),stroke_width=max(1,round(self.unit)),stroke_fill=color('#17121C',round(220*op)))
            else:
                layer=self.panel(('title',),'title'); self.overlay(canvas,layer,(self.w-layer.width)/2,self.h*.075,t,tdur-t,True)
        card=c.get('card')
        if card:
            layer=self.panel(('card',c['id']),'card',c); y=self.h*self.theme['card_y']; dur=c['output_end']-t
            self.overlay(canvas,layer,(self.w-layer.width)/2,y,t-c['output_start'],dur,True)
            # Progress is a consistent visual rhythm, tied to clip duration rather than global seconds.
            d=ImageDraw.Draw(canvas); x=self.w*.07; progress=(t-c['output_start'])/(c['output_end']-c['output_start'])
            d.rounded_rectangle((x,y+layer.height-4*self.unit,x+layer.width*max(.001,progress),y+layer.height),radius=round(2*self.unit),fill=color(self.theme['accent']))
        self.captions(canvas,c,t)
        from keyword_stickers import paint as paint_keyword_stickers
        paint_keyword_stickers(self,canvas,t)
        for st in c.get('stickers',[]):
            a=c['output_start']+st['start']-c['source_start']; b=c['output_start']+st['end']-c['source_start']
            if not a<=t<b: continue
            sprite=self.sprites[st['path']]; sw=round(self.w*st['width']); sh=round(sw*sprite.height/sprite.width)
            if self.h*st['y']+sh>self.h: raise ValueError('Sticker exceeds lower edge')
            self.overlay(canvas,sprite.resize((sw,sh),Image.Resampling.LANCZOS),self.w*st['x'],self.h*st['y'],t-a,b-t,True)
        from illustrations import paint as paint_illustrations
        return paint_illustrations(canvas,self.illustrations,t)


def audio_design(p,out,theme):
    """Original restrained pulse bed and short cue tones, not copied music or a stock library."""
    import numpy as np
    sr=48000; n=round(p['duration']*sr); mix=np.zeros(n,dtype=np.float32); rng=np.random.default_rng(17)
    if p.get('audio',{}).get('bed')=='original-pulse':
        bpm=p['audio'].get('bpm',100); beat=60/bpm; gain=theme['music_gain']
        for pos in np.arange(0,p['duration'],beat):
            x=np.arange(round(.18*sr))/sr; kick=np.sin(2*np.pi*(55*x+2*(1-np.exp(-30*x))))*np.exp(-22*x)
            a=round(pos*sr); end=min(n,a+len(x)); mix[a:end]+=gain*kick[:end-a]
            a=round((pos+beat/2)*sr)
            if a<n:
                length=min(n-a,round(.035*sr)); x=np.arange(length)/sr
                mix[a:a+length]+=gain*.22*rng.standard_normal(length)*np.exp(-100*x)
    cues=[]
    if p.get('audio',{}).get('cues',True):
        for c in p['clips']:
            if not c.get('card'): continue
            pos=c['output_start']+c['card'].get('at',c['source_start'])-c['source_start']; cues.append(pos)
            x=np.arange(round(.12*sr))/sr; tone=(np.sin(2*np.pi*660*x)+.4*np.sin(2*np.pi*990*x))*np.exp(-32*x)*(1-np.exp(-180*x))
            a=round(pos*sr); end=min(n,a+len(x)); mix[a:end]+=theme['sfx_gain']*tone[:end-a]
    from sound_events import add_events
    events=add_events(mix,p)
    if events:
        (Path(out).parent/'sound_events.json').write_text(json.dumps(events,ensure_ascii=False,indent=2),encoding='utf8')
    preclip_peak=float(abs(mix).max())
    clipped_samples=int((abs(mix)>.25).sum())
    mix=np.clip(mix,-.25,.25)
    with wave.open(str(out),'wb') as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(sr); f.writeframes((mix*32767).astype('<i2').tobytes())
    return {'kind':p.get('audio',{}).get('bed','none'),'cue_times':cues,'peak':float(abs(mix).max()),'origin':'explicit catalog assets; see sound_events.json' if events else 'legacy synthesized cue/bed or silence','events':len(events),'event_log':'sound_events.json' if events else None,'preclip_peak':preclip_peak,'clipped_samples':clipped_samples,'listening_review':'pending' if events else 'not_applicable'}


def render(plan_path,output_dir):
    p=compile_plan(load_plan(plan_path)); output_dir=Path(output_dir).resolve()
    from sound_events import compile_events
    compile_events(p)  # Fail before expensive render when an explicitly requested sound is invalid.
    from boundary_transitions import compile_transitions, apply as apply_boundary, audit as audit_boundaries
    boundary_events=compile_transitions(p)
    output_dir.mkdir(parents=True,exist_ok=True)
    if any(output_dir.iterdir()): raise ValueError('Use an empty output directory; completed renders are never overwritten')
    p['width']=p.get('width',720); p['height']=p.get('height',1280)
    number=0
    for c in p['clips']:
        if c.get('card'): number+=1
        c['index']=number
    state={'status':'running','plan':str(Path(plan_path).resolve())}; status=output_dir/'status.json'
    def save(): status.write_text(json.dumps(state,ensure_ascii=False,indent=2))
    save(); decoder=encoder=None
    try:
        meta=probe(p['source'])
        source_video=next((s for s in meta['streams'] if s['codec_type']=='video'),None)
        if source_video is None: raise ValueError('No video in source')
        from frame_fit import audit as audit_frame_fit
        p['frame_fit_audit']=audit_frame_fit(p,source_video)
        if not any(s['codec_type']=='audio' for s in meta['streams']): raise ValueError('No audio in source')
        if abs(float(meta['format']['duration'])-p['source_duration'])>.15: raise ValueError('Plan source duration does not match media')
        # Outdoor interviewer/subject levels can differ by >10dB. Balance clips before mixing cues.
        import numpy as np
        for c in p['clips']:
            if p.get('audio',{}).get('normalize',True):
                pcm=subprocess.check_output(['ffmpeg','-v','error','-ss',str(c['source_start']),'-i',p['source'],'-t',str(c['source_end']-c['source_start']),'-vn','-ac','1','-ar','16000','-f','f32le','-'])
                samples=np.frombuffer(pcm,dtype='<f4'); rms=float(np.sqrt(np.mean(samples*samples))) if len(samples) else 0.
                if not np.isfinite(rms) or rms<=0: raise ValueError('Empty/invalid source audio in kept clip')
                peak=float(abs(samples).max()); gain=min(3.,max(.5,.075/max(.001,rms)),.9/max(.001,peak))
                c['audio_gain']=gain; c['measured_rms']=rms
        painter=Painter(p)
        font_qa=painter.font_preflight(output_dir)
        if painter.variant.get('scene_system'):
            from template_scenes import audit_layout
        else:
            from design_system import audit_layout
        layout_qa=audit_layout(painter)
        if layout_qa is not None:
            (output_dir/'layout_qa.json').write_text(json.dumps(layout_qa,ensure_ascii=False,indent=2))
        if not p['_privacy']['targets']:
            (output_dir/'compiled_plan.json').write_text(json.dumps(p,ensure_ascii=False,indent=2),encoding='utf8')
        # For privacy jobs, keep the editable source plan outside the deliverable folder.
        # It may contain original names, raw transcript and private match terms.
        if p.get('hook_audit'):
            (output_dir/'hook_audit.json').write_text(json.dumps(p['hook_audit'],ensure_ascii=False,indent=2))
        if boundary_events:
            (output_dir/'transition_qa.json').write_text(json.dumps(audit_boundaries(boundary_events),ensure_ascii=False,indent=2))
        filters=output_dir/'base_filter.txt'; filters.write_text(base_filter(p)); base=output_dir/'base.mp4'; log=output_dir/'render.log'
        run(['ffmpeg','-v','error','-n','-i',p['source'],'-filter_complex_script',str(filters),'-map','[v]','-map','[a]','-c:v','libx264','-crf','18','-preset','fast','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k',str(base)],log)
        w=p['width']; h=p['height']; fps=p.get('fps',30); silent=output_dir/'visual.mp4'
        with log.open('ab') as lf:
            decoder=subprocess.Popen(['ffmpeg','-v','error','-i',str(base),'-map','0:v','-pix_fmt','rgb24','-f','rawvideo','-'],stdout=subprocess.PIPE,stderr=lf)
            encoder=subprocess.Popen(['ffmpeg','-v','error','-n','-f','rawvideo','-pix_fmt','rgb24','-s',f'{w}x{h}','-r',str(fps),'-i','-','-an','-c:v','libx264','-crf','19','-preset','fast','-pix_fmt','yuv420p',str(silent)],stdin=subprocess.PIPE,stderr=lf)
            ci=0
            review_frames=set()
            for c in p['clips']:
                events=c.get('caption_events') or painter._auto_events(c)
                for e in events:
                    review_frames.add(min(p['frame_count']-1,max(0,round((e['start']+e['end'])/2*fps))))
            for g in p.get('scene_captions',[]):
                for e in g['phrases']:
                    review_frames.add(min(p['frame_count']-1,max(0,round((e['start']+e['end'])/2*fps))))
            for ev in boundary_events:
                if ev['kind']=='dip_to_dark':
                    review_frames.update(range(ev['start_frame'],ev['end_frame']))
                else:
                    review_frames.update(f for f in (ev['cut_frame']-1,ev['cut_frame']) if 0<=f<p['frame_count'])
            from privacy_masking import audit as privacy_audit
            privacy_qa=privacy_audit(p['_privacy'],p)
            if p['_privacy']['targets']:
                review_frames.update(privacy_qa['risk_frames'])
            for frame in range(p['frame_count']):
                raw=decoder.stdout.read(w*h*3)
                if len(raw)!=w*h*3: raise RuntimeError(f'Decoder ended at frame {frame}; expected {p["frame_count"]}')
                while frame>=p['clips'][ci]['output_frame_end']: ci+=1
                image=painter.paint(Image.frombytes('RGB',(w,h),raw),p['clips'][ci],frame/fps)
                image=apply_boundary(image,frame,boundary_events)
                if frame in review_frames:
                    image.save(output_dir/f'frame_{frame:05}.jpg',quality=90)
                encoder.stdin.write(image.tobytes())
            if decoder.stdout.read(1): raise RuntimeError('Base video contains more frames than compiled timeline')
            decoder.stdout.close(); encoder.stdin.close()
            if decoder.wait()!=0 or encoder.wait()!=0: raise RuntimeError('Decoder or encoder failed; see render.log')
        score=output_dir/'sound.wav'; sound=audio_design(p,score,painter.theme)
        final=output_dir/'final.mp4'
        run(['ffmpeg','-v','error','-n','-i',str(silent),'-i',str(base),'-i',str(score),'-filter_complex','[1:a][2:a]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95:level=false[a]','-map','0:v','-map','[a]','-c:v','copy','-c:a','aac','-b:a','192k','-movflags','+faststart',str(final)],log)
        if p['_privacy']['targets']:
            base.unlink()  # Never leave an unmasked A/V intermediate in a privacy delivery folder.
        if painter.variant.get('scene_system'):
            from template_scenes import write_srt as write_scene_srt
            write_scene_srt(p,output_dir/'captions.srt')
            if p.get('scene_translations'):
                from scene_bilingual import write_srt as write_translation_srt
                write_translation_srt(p,output_dir/'captions.en.srt')
                (output_dir/'translations.json').write_text(json.dumps(p['scene_translations'],ensure_ascii=False,indent=2),encoding='utf8')
        else:
            write_srt(p,output_dir/'captions.srt')
        verified=probe(final); streams=verified['streams']; v=next(s for s in streams if s['codec_type']=='video'); a=next(s for s in streams if s['codec_type']=='audio')
        if abs(float(v.get('duration',0))-float(a.get('duration',0)))>2/fps: raise RuntimeError('A/V duration mismatch')
        if abs(float(v['duration'])-p['duration'])>1/fps: raise RuntimeError('Wrong output duration')
        if int(v.get('nb_frames',0))!=p['frame_count']: raise RuntimeError('Unexpected frame count')
        run(['ffmpeg','-v','error','-i',str(final),'-f','null','-'],output_dir/'decode_check.log')
        qa={'duration':p['duration'],'frame_count':p['frame_count'],'video_duration':float(v['duration']),'audio_duration':float(a['duration']),'width':v['width'],'height':v['height'],'audio_present':True,'decode_passed':True,'sound':sound,'font_coverage_passed':font_qa['passed'],'font_qa':'font_qa.json','visual_review':'pending','frame_fit_audit':p['frame_fit_audit'],'semantic_review':p.get('review',{})}
        if p['_privacy']['targets']:
            # Computer checks cannot prove the sensitive object was correctly located.
            from privacy_masking import scan_text
            privacy_qa['text_scan']=scan_text(p,output_dir)
            if privacy_qa['text_scan']['status']=='failed':
                privacy_qa['coverage']='failed_text_leak'
                (output_dir/'privacy_qa.json').write_text(json.dumps(privacy_qa,ensure_ascii=False,indent=2))
                for unsafe in ('final.mp4','visual.mp4','captions.srt','captions.en.srt','translations.json'):
                    (output_dir/unsafe).unlink(missing_ok=True)
                for frame_path in output_dir.glob('frame_*.jpg'):
                    frame_path.unlink()
                raise ValueError('Sensitive term remains in delivered text; unsafe render removed')
            (output_dir/'privacy_qa.json').write_text(json.dumps(privacy_qa,ensure_ascii=False,indent=2))
            qa['privacy']='privacy_qa.json'
        if layout_qa is not None:qa['layout_qa']='layout_qa.json'
        if painter.illustrations:
            from illustrations import audit as audit_illustrations
            qa['illustrations']=audit_illustrations(painter.illustrations)
        if p.get('hook_audit'):qa['hook_audit']='hook_audit.json'
        if boundary_events:
            qa['transition_qa']='transition_qa.json'
            qa['transition_visual_review']='pending'
        if p.get('camera_motion') is not None:
            from camera_motion import audit as audit_camera
            camera_qa=audit_camera(p['camera_motion'],p['duration'],fps,[c['output_start'] for c in p['clips'][1:]])
            (output_dir/'camera_qa.json').write_text(json.dumps(camera_qa,ensure_ascii=False,indent=2))
            qa['camera_qa']='camera_qa.json'
        (output_dir/'qa.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2))
        state.update(status='rendered_awaiting_review',file=str(final),qa=qa); save()
        print(json.dumps(state,ensure_ascii=False))
    except Exception as e:
        state.update(status='failed',error=f'{type(e).__name__}: {e}'); save()
        for proc in (decoder,encoder):
            if proc and proc.poll() is None: proc.terminate(); proc.wait()
        if p['_privacy']['targets']:
            (output_dir/'base.mp4').unlink(missing_ok=True)
        raise

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('plan'); ap.add_argument('--out-dir',required=True); a=ap.parse_args(); render(a.plan,a.out_dir)
