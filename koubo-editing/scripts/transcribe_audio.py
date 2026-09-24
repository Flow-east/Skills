#!/usr/bin/env python3
"""Explicit backend/model, offline by default; retain real failure causes and provenance."""
import argparse, importlib.util, json, os, subprocess, sys, hashlib
from pathlib import Path
from timeline import probe, srt_time


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('video',nargs='?'); ap.add_argument('--out-dir'); ap.add_argument('--backend',choices=['mlx','faster','whisper'],default='mlx')
    ap.add_argument('--model',default=os.getenv('KAIPAI_WHISPER_MODEL'))
    ap.add_argument('--language',default='zh'); ap.add_argument('--prompt',default='以下是中文口播，请转写原话，保留口误和现场沟通，不要润色。')
    ap.add_argument('--doctor',action='store_true'); ap.add_argument('--allow-download',action='store_true')
    a=ap.parse_args()
    if a.doctor:
        import shutil
        print(json.dumps({'python':sys.executable,'ffmpeg':shutil.which('ffmpeg'),'ffprobe':shutil.which('ffprobe'),'packages':{m:bool(importlib.util.find_spec(m)) for m in ['mlx_whisper','faster_whisper','whisper','PIL']},'model':a.model,'note':'Installed package does not prove GPU access; use explicit backend.'},ensure_ascii=False,indent=2)); return
    if not a.video or not a.out_dir or not a.model: ap.error('video, --out-dir and --model (or KAIPAI_WHISPER_MODEL) required')
    source=Path(a.video).resolve(); out=Path(a.out_dir).resolve()
    if not source.is_file(): ap.error('Video missing')
    local=Path(a.model).expanduser().resolve()
    if not local.exists() and not a.allow_download: ap.error('Local model missing; download is not implicit. Pass a verified local model or authorize --allow-download.')
    model=str(local) if local.exists() else a.model
    if local.exists() and a.backend=='mlx' and (not local.is_dir() or not (local/'config.json').is_file()): ap.error('MLX model requires its own model directory')
    if local.exists() and a.backend=='whisper' and local.is_dir(): ap.error('OpenAI Whisper requires a .pt checkpoint, not an MLX directory')
    out.mkdir(parents=True,exist_ok=True)
    targets=[out/'raw.json',out/'raw.srt',out/'audio.wav',out/'status.json']
    if any(p.exists() for p in targets): ap.error('Output exists; use a new run directory')
    if not a.allow_download: os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
    os.environ.setdefault('NUMBA_CACHE_DIR',str(out/'numba-cache'))
    status={'source':str(source),'backend':a.backend,'model':model,'language':a.language,'prompt':a.prompt,'status':'running'}
    (out/'status.json').write_text(json.dumps(status,ensure_ascii=False,indent=2))
    try:
        meta=probe(source); status['source_duration']=float(meta['format']['duration'])
        if not any(s['codec_type']=='audio' for s in meta['streams']): raise ValueError('Source has no audio')
        subprocess.run(['ffmpeg','-v','error','-n','-i',str(source),'-vn','-ac','1','-ar','16000',str(out/'audio.wav')],check=True)
        if a.backend=='mlx':
            import mlx_whisper
            r=mlx_whisper.transcribe(str(out/'audio.wav'),path_or_hf_repo=model,language=a.language,word_timestamps=True,temperature=0,condition_on_previous_text=False,initial_prompt=a.prompt,verbose=False)
            segments=r['segments']
        elif a.backend=='faster':
            from faster_whisper import WhisperModel
            engine=WhisperModel(model,device='cpu',compute_type='int8',local_files_only=not a.allow_download)
            it,_=engine.transcribe(str(out/'audio.wav'),language=a.language,word_timestamps=True,initial_prompt=a.prompt,condition_on_previous_text=False)
            segments=[dict(start=s.start,end=s.end,text=s.text,words=[dict(start=w.start,end=w.end,word=w.word,probability=w.probability) for w in s.words or []]) for s in it]
        else:
            import whisper
            engine=whisper.load_model(model,device='cpu',download_root=str(out/'models'))
            segments=engine.transcribe(str(out/'audio.wav'),language=a.language,word_timestamps=True,fp16=False,condition_on_previous_text=False,initial_prompt=a.prompt)['segments']
        if not segments or not any(s['text'].strip() for s in segments): raise ValueError('ASR returned empty speech')
        status.update(status='completed',segments=len(segments),audio_sha256=hashlib.sha256((out/'audio.wav').read_bytes()).hexdigest())
        (out/'raw.json').write_text(json.dumps(dict(status,video=str(source),segments=segments),ensure_ascii=False,indent=2),encoding='utf8')
        (out/'raw.srt').write_text('\n'.join(f'{i+1}\n{srt_time(s["start"])} --> {srt_time(s["end"])}\n{s["text"].strip()}\n' for i,s in enumerate(segments)),encoding='utf8')
    except Exception as e:
        status.update(status='failed',error=f'{type(e).__name__}: {e}')
        raise
    finally: (out/'status.json').write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(status,ensure_ascii=False))

if __name__=='__main__': main()
