#!/usr/bin/env python3
"""Create a conservative reference-style plan from an aligned transcript.
It groups speech by pauses; it does not decide retakes or rewrite content.
"""
import argparse,json
from pathlib import Path
from content_analyzer import analyze as analyze_content

def build(raw, out, font, width=None,height=None,fps=30,title='',template='auto',english_map=None,shot_type='wide',remove_high_confidence_fillers=False,template_variant='mint_clean'):
    source=raw.get('source',raw.get('video')); dur=float(raw.get('source_duration',0))
    words=[{'text':w.get('word',w.get('text','')),'start':float(w['start']),'end':float(w['end'])}
           for seg in raw.get('segments',[]) for w in seg.get('words',[]) if str(w.get('word',w.get('text',''))).strip()]
    if not source or not words: raise ValueError('aligned transcript with source and words required')
    if not dur: dur=max(w['end'] for w in words)
    from timeline import probe as probe_source
    from frame_fit import audit as audit_frame_fit, source_display_ratio
    source_video=next((s for s in probe_source(source)['streams'] if s['codec_type']=='video'),None)
    if source_video is None: raise ValueError('No video in source')
    ratio,_,_,_=source_display_ratio(source_video)
    if width is None and height is None: width=720
    if width is None: width=round((height*float(ratio))/2)*2
    if height is None: height=round((width/float(ratio))/2)*2
    clips=[]
    review_candidates=[]
    filler={'嗯','啊','哦','好的','好','对','行','可以','等一下','再来一遍'}
    structural={'那个','我想想','然后是','最后一个，是'}
    high_conf=[]
    def add_candidate(a,b,token,reason,confident=True):
        item={'start':float(a),'end':max(float(b),float(a)+.08),'token':token,
              'reason':reason,'high_confidence':confident,'category':'filler' if token in filler else 'structural'}
        review_candidates.append(item)
        if confident: high_conf.append(item)
    for i,w in enumerate(words):
        token=w['text'].strip('，。！？,.!? 、 ')
        if token not in filler: continue
        prev_gap=w['start']-(words[i-1]['end'] if i else w['start'])
        next_gap=(words[i+1]['start']-w['end']) if i+1<len(words) else 0
        confident=(i>0 and i+1<len(words) and (prev_gap>=.18 or next_gap>=.18) and
                   (token not in {'对','好的','好'} or (prev_gap>=.30 and next_gap>=.18)))
        add_candidate(w['start'],w['end'],token,'高置信填充词，可自动删除' if confident else '疑似现场回应/填充词，需结合音频和上下文复核，不自动删除',confident)
    # Structural filler detection: words that can be removed without changing the
    # recommendation grammar. Keep only contextually safe forms, never global-delete.
    for i,w in enumerate(words):
        token=w['text'].strip('，。！？,.!? 、 ')
        if token=='那个' and i+1<len(words):
            nxt=words[i+1]['text'].strip('，。！？,.!? 、 ')
            if nxt in {'调研','代码','产品','功能','方案','问题'}:
                add_candidate(w['start'],w['end'],'那个','结构性垫词；删除后“场景+选+模型”句式完整',True)
        if token=='我想' and i+1<len(words) and words[i+1]['text'].strip('，。！？,.!? 、 ')=='想':
            add_candidate(w['start'],words[i+1]['end'],'我想想','思考准备语，不承载推荐信息',True)
        if token=='然后' and i+1<len(words) and words[i+1]['text'].strip('，。！？,.!? 、 ')=='是':
            add_candidate(w['start'],words[i+1]['end'],'然后是','转场连接词，可由卡片转场替代',True)
        if token=='最后' and i+2<len(words) and words[i+1]['text'].strip('，。！？,.!? 、 ')=='一个' and words[i+2]['text'].strip('，。！？,.!? 、 ')=='是':
            add_candidate(w['start'],words[i+2]['end'],'最后一个，是','结构提示可选保留；“是”及长停顿可删除',False)
    removed=[]
    if remove_high_confidence_fillers:
        removed=[dict(x,reason='自动删除：高置信填充词') for x in high_conf]
        words=[w for w in words if not any(w['start'] < r['end'] and w['end'] > r['start'] for r in removed)]
    groups=[]; cur=[]
    for w in words:
        if cur and w['start']-cur[-1]['end']>.72:
            groups.append(cur);cur=[]
        cur.append(w)
    if cur:groups.append(cur)
    # Repeated phrase candidates: report possible retakes, never delete automatically.
    for i in range(len(groups)):
        left=''.join(w['text'] for w in groups[i])
        for j in range(i+1,len(groups)):
            right=''.join(w['text'] for w in groups[j])
            common=''
            for n in range(min(len(left),len(right)),3,-1):
                found=next((left[k:k+n] for k in range(len(left)-n+1) if left[k:k+n] in right),None)
                if found: common=found; break
            if common:
                review_candidates.append({'start':groups[j][0]['start'],'end':groups[j][-1]['end'],'reason':f'与前段重复短语“{common}”，可能是重录或重复表达，需结合画面/上下文复核'})
                break
    for i,g in enumerate(groups):
        a=max(0,g[0]['start']-.03); b=min(dur,g[-1]['end']+.03)
        clips.append({'id':f'auto_{i+1:03}','start':a,'end':b,'reason':'保留连续口播；自动按停顿分组，未替代人工重录判断','words':g})
    # Explicitly split around auto-removed intervals so timeline validation cannot
    # reintroduce deleted audio through a clip that still spans the filler.
    if removed:
        split=[]
        for c in clips:
            pieces=[(c['start'],c['end'])]
            for r in removed:
                nxt=[]
                for a,b in pieces:
                    if r['end']<=a or r['start']>=b: nxt.append((a,b)); continue
                    if a<r['start']: nxt.append((a,min(b,r['start'])))
                    if r['end']<b: nxt.append((max(a,r['end']),b))
                pieces=nxt
            for j,(a,b) in enumerate(pieces,1):
                q=dict(c); q['id']=c['id']+f'_p{j}' if len(pieces)>1 else c['id']; q['start']=a; q['end']=b
                q['words']=[w for w in c['words'] if w['end']>a and w['start']<b]
                if q['words']: split.append(q)
        clips=split
    alltext=''.join(w['text'] for w in words)
    if not title:
        title_group=next((g for g in groups if any(x in ''.join(w['text'] for w in g) for x in ['如何','怎么','为什么','哪个','哪些','能不能','是否'])), groups[0] if groups else [])
        first=''.join(w['text'] for w in title_group)
        first=first.replace('，','').replace('。','').replace(',','').replace('.','').replace('Ｂ','').replace('B','')
        # Avoid turning a speaker self-introduction into the topic title.
        if '姐姐' in first[:8]: first=first[first.find('姐姐')+2:]
        # Stop a question-style title before the first concrete example/recommendation.
        cutpoints=[first.find(x, max(0, first.find('如何')+2)) for x in ['选','推荐','适合','比如']]
        cutpoints=[x for x in cutpoints if x>0]
        if cutpoints: first=first[:min(cutpoints)+1]
        first=first.strip(' ：:、-')
        title=first[:14] + ('…' if len(first)>14 else '')
    if template=='auto':
        template='list-cards' if any(x in alltext for x in ['第一','第二','第三','几个','步骤','清单']) else ('service' if any(x in alltext for x in ['服务','课程','客户','信任']) else 'knowledge')
    profile={'list-cards':'contrast','knowledge':'mint','service':'premium'}.get(template,'mint')
    from template_catalog import get as get_template
    variant=get_template(template_variant)
    # ASR grouping is not camera editing. Start neutral; Codex authors semantic states.
    zoom=1.0
    for c in clips:
        c['zoom']=zoom; c['focus']=[.5,.45]
    content_analysis=analyze_content(words)
    p={'version':2,'source':source,'source_duration':dur,'font':font,'width':width,'height':height,'fps':fps,
       'template':template,'frame_fit':'native','style_profile':profile,'template_variant':template_variant,'shot_type':shot_type,'reference_mode':True,'auto_semantics':True,'auto_viewport':True,
       'title':title,'title_duration':1.6 if title else 0,'audio':{'bed':'none','cues':False,'normalize':True},'clips':clips,
       'removed':removed,
       'content_analysis':content_analysis,
       'english_map':english_map or {},'review':{'status':'auto-preview' if not removed else 'auto-preview-with-high-confidence-filler-removal','note':'自动按停顿分组；高置信填充词仅在显著停顿且处于句中时删除，现场沟通、重录、专名和事实内容仍需人工复核','review_candidates':review_candidates}}
    from timeline import compile_plan
    from camera_motion import build_track
    p['camera_motion']=build_track(compile_plan(p)['duration'],[],variant.get('camera_recipe',{}))
    p['review']['camera_motion']='neutral_baseline_needs_authored_semantic_decisions'
    audit_frame_fit(p,source_video)  # Auto plans do not silently pad or crop; caller chooses matching dimensions.

    Path(out).parent.mkdir(parents=True,exist_ok=True)
    from opening_hooks import suggest as suggest_hooks, write_cards as write_hook_cards
    hook_candidates=suggest_hooks(compile_plan(p))
    hook_file=Path(out).with_name(Path(out).stem+'_hook_candidates.json')
    hook_file.write_text(json.dumps(hook_candidates,ensure_ascii=False,indent=2),encoding='utf8')
    write_hook_cards(hook_candidates,hook_file.with_suffix('.md'))
    p['review']['hook_candidates_file']=hook_file.name
    p['review']['hook_selection']='needs_editorial_review_no_automatic_reorder'
    from sound_candidates import suggest as suggest_sounds, write_cards as write_sound_cards
    sound_candidates=suggest_sounds(compile_plan(p))
    sound_file=Path(out).with_name(Path(out).stem+'_sound_candidates.json')
    sound_file.write_text(json.dumps(sound_candidates,ensure_ascii=False,indent=2),encoding='utf8')
    write_sound_cards(sound_candidates,sound_file.with_suffix('.md'))
    p['review']['sound_candidates_file']=sound_file.name
    p['review']['sound_selection']='needs_editorial_review_no_automatic_audio'
    Path(out).write_text(json.dumps(p,ensure_ascii=False,indent=2),encoding='utf8')
    report=Path(out).with_name(Path(out).stem+'_review.md')
    lines=['# 自动剪辑复核报告','',f'- 片段数：{len(clips)}',f'- 自动删除高置信填充词：{len(removed)} 个' ,f'- 逐词数量：{len(words)}',f'- 模式：reference_mode（开拍式预览）',f'- 模板变体：{template_variant}（绑定字体、配色与镜头语言）','', '## 待复核候选']
    if review_candidates:
        for i,r in enumerate(review_candidates,1): lines.append(f'{i}. `{r["start"]:.2f}s–{r["end"]:.2f}s`：{r["reason"]}')
    else: lines.append('暂无自动候选。')
    lines += ['', '## 开头候选（未自动采用）', f'- {len(hook_candidates)} 种真实口播片段候选，见 `{hook_file.with_suffix('.md').name}` 与 `{hook_file.name}`；前置必须人工核查原意、句尾和正文兑现。', '', '## 音效候选（未自动采用）', f'- {len(sound_candidates["decisions"])} 个经逐词间隙初筛的音效/留白决策，见 `{sound_file.with_suffix(".md").name}`。必须先听原声及 A/B；不能按标点逐句加声。', '', '## 内容分析摘要', f'- 内容单元：{len(content_analysis["units"])} 个', f'- 删除候选：{len(content_analysis["deletion_candidates"])} 个', '', '## 交付前检查', '- 试听候选区间，确认是否为现场沟通或重录。', '- 校对品牌名、数字和专有名词。', '- 确认字幕没有遮挡脸部、嘴部和关键手势。', '- 确认语义贴纸确有必要后再调用 Nexora。', '- 自动预览不会替代人工语义剪辑决定。']
    report.write_text('\n'.join(lines)+'\n',encoding='utf8')
    return p
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('transcript');ap.add_argument('--out',required=True);ap.add_argument('--font',required=True);ap.add_argument('--title',default='');ap.add_argument('--template',choices=['auto','list-cards','knowledge','service'],default='auto');ap.add_argument('--english-json',default=None,help='JSON mapping of exact Chinese phrase to verified English') ;ap.add_argument('--shot-type',choices=['wide','medium','close'],default='wide');ap.add_argument('--template-variant',default='mint_clean',help='已验证模板变体ID，可用 template_catalog.py 查看');ap.add_argument('--remove-high-confidence-fillers',action='store_true',help='仅自动删除句中、带明显停顿的高置信填充词');a=ap.parse_args()
    build(json.loads(Path(a.transcript).read_text()),a.out,a.font,template=a.template,english_map=json.loads(Path(a.english_json).read_text()) if a.english_json else None,shot_type=a.shot_type,remove_high_confidence_fillers=a.remove_high_confidence_fillers,template_variant=a.template_variant);print(Path(a.out).resolve())
