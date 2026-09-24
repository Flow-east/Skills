#!/usr/bin/env python3
"""Preview privacy style alternatives and apply an explicit user-selected style.

Preview output is not an approved privacy delivery. Applying changes style only;
run the regular full render/QA from the resulting plan after user selection.
"""
import argparse
import copy
import json
import subprocess
import tempfile
from pathlib import Path
from privacy_masking import STYLES, choose_style
from timeline import load_plan, compile_plan


def options(plan, target_id):
    targets={t['id']:t for t in plan.get('privacy_targets',[])}
    if target_id not in targets:raise ValueError('Unknown privacy target')
    target=targets[target_id]
    current={ev.get('style_id') or choose_style(target['kind'],preferred=target.get('preferred_style'),
                                                 mood=plan.get('privacy_mood','neutral'))
             for ev in plan.get('privacy_events',[]) if ev.get('target_id')==target_id}
    if not current:raise ValueError('Target has no visual privacy events')
    candidates=[key for key,v in STYLES.items() if target['kind'] in v['kinds'] and key not in current]
    return candidates[:3]


def changed_plan(plan,target_id,style,*,user_selected=False,preview_only=False):
    if user_selected == preview_only:
        raise ValueError('Specify either explicit user selection or preview-only intent')
    if target_id not in {t['id'] for t in plan.get('privacy_targets',[])}:
        raise ValueError('Unknown target')
    result=copy.deepcopy(plan)
    target=next(t for t in result['privacy_targets'] if t['id']==target_id)
    if style not in STYLES or target['kind'] not in STYLES[style]['kinds']:
        raise ValueError('Style cannot cover the target')
    for ev in result['privacy_events']:
        if ev['target_id']==target_id:
            ev['style_id']=style
            ev['style_override_confirmed']=True
    target['preferred_style']=style
    result.setdefault('privacy_revisions',[]).append({'target_id':target_id,'style_id':style,
                                                       'choice':'user_selected' if user_selected else 'preview_only'})
    compile_plan(result)  # Covers every original target/clip, or fail before writing anything.
    return result


def preview(plan_path,target_id,out_dir):
    plan=load_plan(plan_path); compiled=compile_plan(plan)
    styles=options(plan,target_id)
    if not styles:raise ValueError('No distinct alternative privacy style available')
    out=Path(out_dir).resolve();out.mkdir(parents=True,exist_ok=True)
    if any(out.iterdir()):raise ValueError('Use an empty preview directory')
    spans=[(e['start'],e['end']) for e in plan.get('privacy_events',[]) if e['target_id']==target_id]
    begin=max(0,min(a for a,b in spans)-.2);finish=min(compiled['duration'],max(b for a,b in spans)+.2)
    from render_template import render
    results=[]
    # Full rendering preserves the actual template/zoom/audio timing; only a short
    # excerpt leaves the temporary private workspace. It remains review-only.
    with tempfile.TemporaryDirectory(prefix='koubo-privacy-preview-') as temp:
        tmp=Path(temp)
        for style in styles:
            variant=changed_plan(plan,target_id,style,preview_only=True)
            plan_file=tmp/f'{style}.json';plan_file.write_text(json.dumps(variant,ensure_ascii=False))
            rendered=tmp/f'{style}-render';render(plan_file,rendered)
            path=out/f'{style}.mp4'
            subprocess.run(['ffmpeg','-v','error','-y','-ss',str(begin),'-i',str(rendered/'final.mp4'),
                            '-t',str(finish-begin),'-c:v','libx264','-crf','20','-c:a','aac',str(path)],check=True)
            results.append({'style_id':style,'label':STYLES[style]['label'],'preview':str(path),
                            'time_range':[begin,finish],'target_id':target_id})
    (out/'options.json').write_text(json.dumps({'status':'preview_only_requires_user_choice',
                                                'options':results},ensure_ascii=False,indent=2))
    return results


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    sub=ap.add_subparsers(dest='command',required=True)
    pre=sub.add_parser('preview');pre.add_argument('plan');pre.add_argument('--target-id',required=True);pre.add_argument('--out-dir',required=True)
    apply=sub.add_parser('apply');apply.add_argument('plan');apply.add_argument('--target-id',required=True)
    apply.add_argument('--style',required=True);apply.add_argument('--out-plan',required=True)
    apply.add_argument('--user-selected',action='store_true')
    a=ap.parse_args()
    if a.command=='preview':result=preview(a.plan,a.target_id,a.out_dir)
    else:
        dest=Path(a.out_plan).resolve()
        if dest.exists():raise ValueError('Do not overwrite an existing edit plan')
        new=changed_plan(load_plan(a.plan),a.target_id,a.style,user_selected=a.user_selected)
        dest.write_text(json.dumps(new,ensure_ascii=False,indent=2));result={'plan':str(dest),'status':'rerender_final_and_review'}
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
