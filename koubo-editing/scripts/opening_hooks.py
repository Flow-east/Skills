#!/usr/bin/env python3
"""Evidence-bound opening suggestions and selected-hook contract; never rewrite speech.

Heuristics propose candidates from the *actual* aligned clips. The editor must
confirm promise/payoff, conditions and sentence completion before selection.
"""
import argparse,json,re
from pathlib import Path

QUESTION=('为什么','怎么','如何','能不能','是否','到底','哪里','哪个','哪些','吗','？','?')
RESULT=('结果','最后','结论','关键','核心','实际上','其实','答案','发现','做到','效果','现在')
DEPENDENT=('所以','因此','但是','不过','刚才','上面','上述','这','那','它','他们','这个','那个','第一','第二','第三')


def text(c):return ''.join(w['text'] for w in c.get('words',[])) or c.get('caption','')


def suggest(p):
    clips=p.get('clips',[])
    if not clips:return []
    original=[c['id'] for c in clips]
    candidates=[{'method':'original','opening_clip_ids':[original[0]],'proposed_order':original,
                 'source_excerpt':text(clips[0]),'source_interval':[clips[0]['source_start'],clips[0]['source_end']],
                 'why':'原开头基线；不为变化而重排','risks':[],'status':'needs_editorial_review'}]
    for method,keys in [('question_first',QUESTION),('result_first',RESULT)]:
        found=next((c for c in clips[1:] if any(k in text(c) for k in keys) and text(c).strip()),None)
        if found is None:continue
        risks=['必须指定正文兑现片段并核对事实/条件；不能仅凭关键词判定可前置']
        if any(text(found).startswith(k) for k in DEPENDENT):
            risks.append('可能依赖前文指代、转折或步骤；通常不宜直接前置')
        candidates.append({'method':method,'opening_clip_ids':[found['id']],
                           'proposed_order':[found['id']]+[x for x in original if x!=found['id']],
                           'source_excerpt':text(found),
                           'source_interval':[found['source_start'],found['source_end']],
                           'why':'真实口播片段候选；只移动片段，不生成新的事实或口播',
                           'risks':risks,'status':'needs_editorial_review'})
    return candidates


def verify(p):
    h=p.get('hook_design')
    if h is None:return None
    if not isinstance(h,dict) or h.get('method') not in ('original','question_first','result_first','highlights'):
        raise ValueError('hook_design requires a known method')
    clips=p['clips'];ids=[c['id'] for c in clips];opening=h.get('opening_clip_ids')
    if not isinstance(opening,list) or not opening or opening!=ids[:len(opening)] or len(opening)!=len(set(opening)):
        raise ValueError('Hook opening_clip_ids must be a unique output prefix')
    evidence=''.join(text(c) for c in clips[:len(opening)])
    quote=str(h.get('source_excerpt','')).strip()
    if not quote or quote not in evidence:
        raise ValueError('Hook excerpt must be exact text from the opening source clips')
    if not str(h.get('reason','')).strip():raise ValueError('Hook needs an editorial reason')
    if h.get('semantic_review')!='verified' or h.get('end_of_speech_review')!='verified':
        raise ValueError('Hook must verify meaning and complete spoken ending')
    if h['method']!='original':
        if not p.get('allow_reorder'):raise ValueError('Frontloaded hook requires allow_reorder')
        payoff=h.get('payoff_clip_id')
        if payoff not in ids[len(opening):]:raise ValueError('Hook promise must be answered in a later payoff clip')
        if not str(h.get('payoff_reason','')).strip():raise ValueError('Hook needs explanation of the payoff')
        if h.get('duplicate_policy') not in ('moved_not_repeated','intentional_reprise'):
            raise ValueError('Hook needs an explicit duplicate policy')
        if h['duplicate_policy']=='intentional_reprise' and not str(h.get('reprise_reason','')).strip():
            raise ValueError('Repeated hook requires a semantic reason')
    for c in clips[:len(opening)]:
        if c.get('words') and c['words'][-1].get('source_word_end',c['source_end'])>c['source_end']+.005:
            raise ValueError('Hook spoken ending extends beyond kept source clip')
    if h['method']!='original' and h['duplicate_policy']=='moved_not_repeated':
        for first in clips[:len(opening)]:
            for later in clips[len(opening):]:
                if min(first['source_end'],later['source_end'])-max(first['source_start'],later['source_start'])>.05:
                    raise ValueError('Moved hook still duplicates source footage in the body')
    if h['method']!='original' and any(quote.startswith(k) for k in DEPENDENT) and not str(h.get('dependency_resolution','')).strip():
        raise ValueError('Dependent hook requires explicit context resolution')
    return {'method':h['method'],'opening_clip_ids':opening,'excerpt':quote,
            'payoff_clip_id':h.get('payoff_clip_id'),'review':'editor_verified_not_a_retention_metric'}


def write_cards(rows,path):
    lines=['# 开头候选（仅供内容决策，未自动改动时间轴）','',
           '每项都来自原始逐词片段。先看开头承诺能否在正文兑现、条件/指代是否完整，再决定是否前置。没有好钩子就保留原开头。','']
    for i,c in enumerate(rows,1):
        a,b=c['source_interval']
        lines.extend([f'## 候选 {i}：{c["method"]}',f'- 原话：{c["source_excerpt"]}',
          f'- 源时间：{a:.2f}–{b:.2f}s；建议输出顺序：{", ".join(c["proposed_order"])}',
          f'- 依据：{c["why"]}',f'- 风险：{"；".join(c["risks"]) if c["risks"] else "仍需复核首句完整性"}',
          '- 正文回应片段：**待编辑者填写**；前置片段在正文移动/有意重复：**待复核**',''])
    lines.extend(['## 选定后验收','- 源原话不改写；条件、否定、指代、前后语义完整。',
      '- 句尾口型与尾音未被剪断；无意重复被处理。',
      '- 正文明确兑现开场问题/承诺；音效及转场不抢口播。',''])
    Path(path).write_text('\n'.join(lines),encoding='utf8')


def main():
    from timeline import load_plan,compile_plan
    ap=argparse.ArgumentParser();ap.add_argument('plan');ap.add_argument('--out',required=True);args=ap.parse_args()
    p=compile_plan(load_plan(args.plan,check_files=False));out=Path(args.out);out.parent.mkdir(parents=True,exist_ok=True)
    rows=suggest(p);out.write_text(json.dumps(rows,ensure_ascii=False,indent=2));write_cards(rows,out.with_suffix('.md'))
    print(f'{len(rows)} evidence-bound candidates: {out}')
if __name__=='__main__':main()
