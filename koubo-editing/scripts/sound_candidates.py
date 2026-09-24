#!/usr/bin/env python3
"""Evidence-only soundtrack decision card from an already edited word timeline.

Do not mutate the plan or auto-apply effects. Audition source speech and the final
A/B mix before accepting any proposed asset or silence decision.
"""
import argparse, json
from pathlib import Path
from sound_events import library, STYLES

QUESTION_CHOICES=('sfx-wooden-mallet-hit','sfx-electronic-beep','sfx-short-chime')
STATEMENT_CHOICES=('sfx-electronic-beep','sfx-short-chime','sfx-wooden-mallet-hit')
PUNCTUATION='。！？!?；;'


def suggest(plan, opening_seconds=5., min_clearance=.24):
    sounds=library(); clips=plan['clips']; words=[(c,i,w) for c in clips for i,w in enumerate(c.get('words',[]))]
    style=plan.get('audio',{}).get('sound_style',STYLES.get(plan.get('template_variant'),'neutral'))
    result=[]
    for j,(clip,index,word) in enumerate(words):
        token=word['text'].strip()
        is_end=index==len(clip['words'])-1
        if not token or not (token[-1] in PUNCTUATION or is_end):continue
        opening=word['end']<=opening_seconds
        phrase=''.join(w['text'] for w in clip['words'][:index+1])
        next_start=words[j+1][2]['start'] if j+1<len(words) else plan['duration']
        clearance=max(0,next_start-word['end']); question=token[-1] in '？！?!'
        structure=any(x in phrase for x in ('三步走','第一步','第二步','第三步','先试点后推广'))
        contrast=any(x in phrase for x in ('不是','不要','但是','而是','结果','关键','居然'))
        incomplete=(len(phrase.strip())<5 and not structure) or token in ('的','地','得','一句,','一句，')
        candidate=(not incomplete) and (structure or (question and opening) or (contrast and is_end))
        anchor=word['end']; offset=.05
        choices=[]
        if candidate and clearance>=min_clearance:
            for aid in (QUESTION_CHOICES if question else STATEMENT_CHOICES):
                a=sounds.get(aid)
                if not a or a.get('selection_status')!='approved' or style not in a['styles']:continue
                role='sentence_end'
                if role not in a.get('roles',[a['role']]):continue
                start=anchor+offset-a['hit_seconds']; end=start+a['duration']
                if start>=0 and end<=next_start-.03 and end<=plan['duration']:
                    choices.append(dict(asset_id=aid,name=a['name_zh'],role=role,
                                        hit_output=round(anchor+offset,3),start_output=round(start,3),
                                        end_output=round(end,3),gain_preview=.07 if a.get('intensity')=='heavy' else .10))
        reason=('语义未闭合/短促引子，保留原声' if incomplete else
                '普通语义边界不必逐句加音' if not candidate else
                '口播间隙不足或素材会盖住下一句，保留原声' if not choices else
                '候选落点，需对照原声、画面和模板风格试听；不是自动采用')
        result.append(dict(clip_id=clip['id'],word_index=index,source_word_end=word.get('source_word_end'),
                           anchor_output=round(anchor,3),next_speech_output=round(next_start,3),
                           clearance=round(clearance,3),phrase=phrase,opening_5s=opening,
                           semantic_trigger='question' if question else 'structure' if structure else 'contrast' if contrast else 'ordinary',
                           decision='needs_editorial_review' if choices else 'leave_silent',
                           reason=reason,options=choices))
    return {'policy':'evidence_only_no_automatic_sound_events', 'source_audio_review':'pending',
            'style':style,'decisions':result,
            'review':['核实完整语义和源音频尾气/环境音','选择不超过一个语义事件音效，留白也要有理由',
                      '同画面无声/有声 A/B 试听开头、边界、密集口播和结尾；不以峰值代替听审']}


def write_cards(report,path):
    lines=['# 音效创作候选（未自动采用）','',f'- 风格约束：{report["style"]}',
           '- 本卡仅供内容决策；任何候选先听原声，再选素材做同画面 A/B。','']
    for row in report['decisions']:
        lines.extend([f'## {row["clip_id"]} / 词 {row["word_index"]} / {row["anchor_output"]:.2f}s',
                      f'- 原话：{row["phrase"]}',f'- 到下句约 {row["clearance"]:.2f}s：{row["reason"]}'])
        for a in row['options']:
            lines.append(f'- 可试听：{a["name"]}（{a["asset_id"]}），击点 {a["hit_output"]:.2f}s，'
                         f'占用 {a["start_output"]:.2f}–{a["end_output"]:.2f}s；建议预览增益 {a["gain_preview"]:.2f}')
        lines.append('')
    if not report['decisions']:lines.extend(['无符合条件的落点；保留原声，不为填充而加音效。',''])
    lines.extend(['## 交付门槛','- 逐项标记采用/放弃及理由，并听同画面 A/B。',
                  '- 核对尾音、人声清晰度、响度和画面同步；无实际试听时只可称技术预览。'])
    Path(path).write_text('\n'.join(lines)+'\n',encoding='utf8')


def main():
    from timeline import load_plan,compile_plan
    ap=argparse.ArgumentParser();ap.add_argument('plan');ap.add_argument('--out',required=True);args=ap.parse_args()
    p=compile_plan(load_plan(args.plan,check_files=False));result=suggest(p)
    out=Path(args.out);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    write_cards(result,out.with_suffix('.md'))
    print(f'{len(result["decisions"])} sound decisions (no events applied): {out}')
if __name__=='__main__':main()
