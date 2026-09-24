#!/usr/bin/env python3
"""One-command conservative reference edit: local ASR -> pause plan -> render.
Editorial retakes/chatter remain reviewable rather than being guessed away.
"""
import argparse,json,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent

def main():
 ap=argparse.ArgumentParser();ap.add_argument('video');ap.add_argument('--out-dir',required=True);ap.add_argument('--title',default='');ap.add_argument('--font',default='/System/Library/Fonts/STHeiti Medium.ttc');ap.add_argument('--model',default=None);ap.add_argument('--backend',choices=['mlx','faster','whisper'],default='mlx');ap.add_argument('--template',choices=['auto','list-cards','knowledge','service'],default='auto');ap.add_argument('--template-variant',default='mint_clean',help='已验证模板变体ID');ap.add_argument('--remove-high-confidence-fillers',action='store_true',help='仅删除句中且有明显停顿的高置信填充词');args=ap.parse_args()
 out=Path(args.out_dir).resolve(); out.mkdir(parents=True,exist_ok=True); asr=out/'transcript'
 cmd=[sys.executable,str(HERE/'transcribe_audio.py'),args.video,'--out-dir',str(asr),'--backend',args.backend]
 if args.model: cmd+=['--model',args.model]
 subprocess.run(cmd,check=True)
 raw=asr/'raw.json'
 plan=out/'auto_plan.json'
 plan_cmd=[sys.executable,str(HERE/'auto_plan.py'),str(raw),'--out',str(plan),'--font',args.font,'--title',args.title,'--template',args.template,'--template-variant',args.template_variant]
 if args.remove_high_confidence_fillers: plan_cmd.append('--remove-high-confidence-fillers')
 subprocess.run(plan_cmd,check=True)
 render=out/'render'; subprocess.run([sys.executable,str(HERE/'render_template.py'),str(plan),'--out-dir',str(render)],check=True)
 print(json.dumps({'transcript':str(raw),'plan':str(plan),'video':str(render/'final.mp4'),'qa':str(render/'qa.json')},ensure_ascii=False))
if __name__=='__main__': main()
