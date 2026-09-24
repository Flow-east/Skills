#!/usr/bin/env python3
"""Optional ASS sidecar. The primary renderer uses Pillow and does not require libass."""
import argparse
from pathlib import Path
from timeline import load_plan, compile_plan, caption_groups


def stamp(t):
    t=round(t*100); h,t=divmod(t,360000); m,t=divmod(t,6000); s,t=divmod(t,100)
    return f'{h}:{m:02}:{s:02}.{t:02}'


def safe(text): return str(text).replace('\\','／').replace('{','｛').replace('}','｝').replace('\n',' ')


def build(p):
    w=p.get('width',720); h=p.get('height',1280); size=round(43*w/720)
    rows=[f'''[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Base,Heiti SC,{size},&H0042CFFF,&H00FFFFFF,&H00181116,&H00000000,0,0,0,0,100,100,0,0,1,3,0,2,{round(.06*w)},{round(.06*w)},{round(.09*h)},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
''']
    for c in p['clips']:
        groups=caption_groups(c)
        if not groups: groups=[[dict(text=c['caption'],start=c['output_start'],end=c['output_end'])]]
        for i,g in enumerate(groups):
            a=g[0]['start']; b=groups[i+1][0]['start'] if i+1<len(groups) else c['output_end']
            text=r'{\fad(70,60)\fscx94\fscy94\t(0,130,\fscx100\fscy100)}'
            for j,x in enumerate(g):
                end=g[j+1]['start'] if j+1<len(g) else b
                duration=max(0,round((end-a)*100)-round((x['start']-a)*100))
                text+=f'{{\\kf{duration}}}'+safe(x['text'])
            rows.append(f'Dialogue: 0,{stamp(a)},{stamp(b)},Base,,0,0,0,,{text}\n')
    return ''.join(rows)

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('plan'); ap.add_argument('--out',required=True); a=ap.parse_args(); out=Path(a.out)
    if out.exists(): ap.error('Output exists')
    out.write_text(build(compile_plan(load_plan(a.plan))),encoding='utf8'); print(out.resolve())
