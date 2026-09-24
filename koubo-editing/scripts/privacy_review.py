#!/usr/bin/env python3
"""Export unscaled encoded privacy intervals for continuous human A/V review."""
import argparse
import json
import subprocess
from pathlib import Path


def export(render_dir,out_dir):
    source=Path(render_dir)/'final.mp4';qa_path=Path(render_dir)/'privacy_qa.json'
    if not source.is_file() or not qa_path.is_file():raise ValueError('Rendered privacy MP4 and QA required')
    qa=json.loads(qa_path.read_text());out=Path(out_dir).resolve()
    out.mkdir(parents=True,exist_ok=True)
    if any(out.iterdir()):raise ValueError('Use an empty private review directory')
    clips=[]
    for i,span in enumerate(qa.get('review_ranges',[])+qa.get('audio_review_ranges',[]),start=1):
        start,end=span['start'],span['end'];name=f'privacy-review-{i:02}.mp4';path=out/name
        subprocess.run(['ffmpeg','-v','error','-y','-ss',str(start),'-i',str(source),'-t',str(end-start),
                        '-c:v','libx264','-crf','17','-c:a','aac',str(path)],check=True)
        clips.append({'target_id':span['target_id'],'clip_id':span['clip_id'],'range':[start,end],'file':str(path)})
    (out/'review.json').write_text(json.dumps({'status':'human_review_required','clips':clips},ensure_ascii=False,indent=2))
    return clips


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('render_dir');ap.add_argument('--out-dir',required=True)
    args=ap.parse_args();print(json.dumps(export(args.render_dir,args.out_dir),ensure_ascii=False,indent=2))
