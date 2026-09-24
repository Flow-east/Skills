#!/usr/bin/env python3
"""Render a second, unrelated 24fps source; verify real A/V cut order and no hard-coded content."""
import json,sys,subprocess,tempfile
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from render_template import render
root=Path(tempfile.mkdtemp(prefix='koubo-smoke-')); source=root/'source.mp4'
subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=red:s=320x568:r=24:d=2','-f','lavfi','-i','sine=frequency=300:duration=2','-f','lavfi','-i','color=blue:s=320x568:r=24:d=2','-f','lavfi','-i','sine=frequency=900:duration=2','-filter_complex','[0:v][1:a][2:v][3:a]concat=n=2:v=1:a=1[v][a]','-map','[v]','-map','[a]','-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac',str(source)],check=True)
p=dict(version=2,source=str(source),source_duration=4.,font='/System/Library/Fonts/STHeiti Medium.ttc',width=320,height=568,fps=30,template='service',title='两段声音测试',audio={'bed':'none','cues':False},clips=[
 dict(id='red',start=.2,end=.8,reason='first tone',words=[dict(text='第一段',start=.2,end=.8)]),
 dict(id='blue',start=2.2,end=2.8,reason='second tone',words=[dict(text='第二段',start=2.2,end=2.8)])])
plan=root/'plan.json'; plan.write_text(json.dumps(p,ensure_ascii=False)); render(plan,root/'render')
result=root/'render/final.mp4'
raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(result),'-vn','-ac','1','-ar','48000','-f','f32le','-'])
samples=np.frombuffer(raw,dtype='<f4'); peaks=[]
for a,b in ((.1,.5),(.7,1.1)):
 s=samples[round(a*48000):round(b*48000)]; ft=abs(np.fft.rfft(s*np.hanning(len(s)))); hz=np.fft.rfftfreq(len(s),1/48000)[ft.argmax()]; peaks.append(float(hz))
assert abs(peaks[0]-300)<5 and abs(peaks[1]-900)<5,peaks
colors=[]
for t in (.3,.9):
 raw=subprocess.check_output(['ffmpeg','-v','error','-ss',str(t),'-i',str(result),'-frames:v','1','-f','rawvideo','-pix_fmt','rgb24','-'])
 im=np.frombuffer(raw,dtype=np.uint8).reshape(568,320,3); colors.append(im[280,160].tolist())
assert colors[0][0]>200 and colors[0][2]<40 and colors[1][2]>200 and colors[1][0]<40,colors
print(json.dumps({'root':str(root),'audio_frequencies':peaks,'frame_colors':colors,'av_cut_order':'passed','input_fps':24,'output_fps':30},ensure_ascii=False))
