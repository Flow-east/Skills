import copy, json, subprocess, sys, tempfile, unittest
import numpy as np
from pathlib import Path
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from timeline import compile_plan, base_filter
from render_template import Painter, render
from privacy_masking import STYLES, audit, choose_style, scan_text
from privacy_revision import options, changed_plan
from test_template_scenes import plan as scene_plan


class PrivacyTests(unittest.TestCase):
    def plan(self,kind='pink'):
        p=scene_plan(kind)
        p['privacy_targets']=[dict(id='person-name',kind='text',origin='user',status='confirmed',
                                   reason='name on display',modalities=['video'],
                                   visible=[dict(clip_id='t',start=.5,end=2.)])]
        p['privacy_events']=[dict(id='mask-name',target_id='person-name',clip_id='t',start=.5,end=2.,
                                  motion='static',box=[.72,.21,.15,.055])]
        return p

    def test_empty_and_style_catalog(self):
        plain=scene_plan('pink');compiled=compile_plan(plain)
        self.assertEqual(compiled['_privacy']['events'],[])
        self.assertEqual(Painter(compiled).privacy['events'],[])
        self.assertEqual(choose_style('face'),'face-patch')
        self.assertEqual(choose_style('text',mood='editorial'),'paper-strip')
        self.assertGreaterEqual(len(STYLES),3)

    def test_mask_opaque_with_scene_and_legacy(self):
        for template in ('pink','legacy'):
            p=self.plan()
            if template=='legacy':
                for k in ('template_variant','scene_captions','scene_canvas','scene_tags','scene_title_lines'):
                    p.pop(k,None)
            c=compile_plan(p); painter=Painter(c); frame=Image.new('RGB',(720,960),'#FF0000')
            before=painter.paint(frame,c['clips'][0],.2)
            during=painter.paint(frame,c['clips'][0],.8)
            self.assertNotEqual(before.getpixel((570,230)),during.getpixel((570,230)))
            self.assertNotEqual(during.getpixel((570,230)),(255,0,0))
            self.assertEqual(audit(c['_privacy'],c)['coverage'],'pending_encoded_visual_review')

    def test_gap_must_fail_and_clip_instance(self):
        p=self.plan();p['privacy_events'][0]['end']=1.9
        with self.assertRaisesRegex(ValueError,'uncovered'):compile_plan(p)
        p=self.plan();p['clips'].append(dict(p['clips'][0],id='repeat'))
        p['allow_reorder']=True
        p['privacy_targets'][0]['visible'].append(dict(clip_id='repeat',start=4.5,end=5.))
        with self.assertRaisesRegex(ValueError,'uncovered'):compile_plan(p)

    def test_motion_keyframes_and_invalid_tracking(self):
        p=self.plan();e=p['privacy_events'][0];e.pop('box');e['motion']='keyframes'
        e['end']=.7;p['privacy_targets'][0]['visible'][0]['end']=.7
        e['keyframes']=[{'time':.5,'box':[.6,.2,.1,.08]}, {'time':.6,'box':[.64,.2,.1,.08]},
                        {'time':.7,'box':[.7,.2,.1,.08]}]
        c=compile_plan(p);self.assertEqual(c['_privacy']['events'][0]['motion'],'keyframes')
        p['privacy_events'][0]['keyframes'][1]['time']=.5
        with self.assertRaisesRegex(ValueError,'ordered'):compile_plan(p)
        p=self.plan();p['privacy_events'][0]['occlusion']='automatic'
        with self.assertRaisesRegex(ValueError,'not supported'):compile_plan(p)

    def test_pending_and_user_style(self):
        p=self.plan();p['privacy_targets'][0]['status']='pending'
        self.assertEqual(compile_plan(p)['_privacy']['confirmation'],'pending')
        p=self.plan();p['privacy_targets'][0]['preferred_style']='paper-strip';p['privacy_events'][0]['style_id']='cloud'
        with self.assertRaisesRegex(ValueError,'silently'):compile_plan(p)
        p['privacy_events'][0]['style_override_confirmed']=True
        self.assertEqual(compile_plan(p)['_privacy']['events'][0]['style_id'],'cloud')

    def test_review_alternatives_only_change_style(self):
        p=self.plan();choices=options(p,'person-name')
        self.assertGreaterEqual(len(choices),2)
        with self.assertRaisesRegex(ValueError,'explicit user selection'):
            changed_plan(p,'person-name',choices[0])
        alternative=changed_plan(p,'person-name',choices[0],user_selected=True)
        self.assertEqual(alternative['clips'],p['clips'])
        self.assertEqual(alternative['privacy_targets'][0]['visible'],p['privacy_targets'][0]['visible'])
        self.assertEqual(alternative['privacy_events'][0]['box'],p['privacy_events'][0]['box'])
        self.assertEqual(alternative['privacy_events'][0]['style_id'],choices[0])
        self.assertNotIn('privacy_revisions',p)

    def test_audio_and_caption_redaction(self):
        p=self.plan();p['privacy_targets'][0]['modalities']=['video','audio','text']
        p['privacy_targets'][0]['text_review']='redacted';p['privacy_targets'][0]['match_terms']=['方法']
        p['privacy_targets'][0]['audible']=[dict(clip_id='t',source_start=.5,source_end=.9)]
        with self.assertRaisesRegex(ValueError,'audio redaction'):compile_plan(p)
        p['audio_redactions']=[dict(target_id='person-name',clip_id='t',source_start=.5,source_end=.9)]
        c=compile_plan(p)
        self.assertNotIn('方法',''.join(w['text'] for w in c['clips'][0]['words']))
        self.assertIn('volume=0:enable=',base_filter(c))
        self.assertEqual(c['clips'][0]['words'][0]['text'],'[已隐藏]')
        p['clips'].append(dict(p['clips'][0],id='repeat'))
        p['allow_reorder']=True
        p['privacy_targets'][0]['audible'].append(dict(clip_id='repeat',source_start=.5,source_end=.9))
        with self.assertRaisesRegex(ValueError,'every audible clip instance'):
            compile_plan(p)
        p['clips'].pop();p['privacy_targets'][0]['audible'].pop()
        with tempfile.TemporaryDirectory() as d:
            out=Path(d);(out/'captions.srt').write_text('方法\n')
            self.assertEqual(scan_text(c,out)['status'],'failed')

    def test_actual_render_no_raw_intermediate(self):
        with tempfile.TemporaryDirectory() as d:
            d=Path(d);src=d/'source.mp4'
            subprocess.run(['ffmpeg','-y','-v','error','-f','lavfi','-i','color=red:s=720x960:r=30:d=4',
                            '-f','lavfi','-i','sine=frequency=400:duration=4','-c:v','libx264','-pix_fmt','yuv420p',
                            '-c:a','aac',str(src)],check=True)
            p=self.plan();p['source']=str(src);p['source_duration']=4.;p['audio']={'cues':False,'bed':'none','normalize':False}
            p['privacy_targets'][0]['modalities']=['video','audio','text']
            p['privacy_targets'][0]['text_review']='redacted';p['privacy_targets'][0]['match_terms']=['方法']
            p['privacy_targets'][0]['audible']=[dict(clip_id='t',source_start=.5,source_end=.9)]
            p['audio_redactions']=[dict(target_id='person-name',clip_id='t',source_start=.5,source_end=.9)]
            plan=d/'plan.json';plan.write_text(json.dumps(p,ensure_ascii=False))
            out=d/'render';render(plan,out)
            self.assertTrue((out/'final.mp4').is_file());self.assertFalse((out/'base.mp4').exists())
            self.assertFalse((out/'compiled_plan.json').exists())
            qa=json.loads((out/'privacy_qa.json').read_text())
            self.assertEqual(qa['text_scan']['status'],'requires_visual_and_audio_review')
            self.assertFalse(qa['public_delivery_allowed'])
            self.assertEqual(qa['audio_redactions'],1)
            self.assertNotIn('方法',(out/'captions.srt').read_text())
            pcm=subprocess.check_output(['ffmpeg','-v','error','-i',str(out/'final.mp4'),'-vn',
                                         '-ac','1','-ar','16000','-f','f32le','-'])
            samples=np.frombuffer(pcm,dtype='<f4')
            muted=float(np.sqrt(np.mean(samples[round(.56*16000):round(.82*16000)]**2)))
            audible=float(np.sqrt(np.mean(samples[round(1.1*16000):round(1.4*16000)]**2)))
            self.assertLess(muted,audible*.05)

    def test_split_sensitive_text_aborts_delivery(self):
        with tempfile.TemporaryDirectory() as d:
            d=Path(d);src=d/'source.mp4'
            subprocess.run(['ffmpeg','-y','-v','error','-f','lavfi','-i','color=red:s=720x960:r=30:d=4',
                            '-f','lavfi','-i','sine=frequency=400:duration=4','-c:v','libx264',
                            '-pix_fmt','yuv420p','-c:a','aac',str(src)],check=True)
            p=self.plan();p['source']=str(src);p['source_duration']=4
            for key in ('template_variant','scene_captions','scene_canvas','scene_tags','scene_title_lines'):
                p.pop(key,None)
            p['clips'][0]['words']=[{'text':'方','start':.1,'end':.5},
                                      {'text':'法','start':.5,'end':1.},
                                      {'text':'清楚','start':1.,'end':2.}]
            p['privacy_targets'][0]['modalities']=['video','text']
            p['privacy_targets'][0]['text_review']='redacted'
            p['privacy_targets'][0]['match_terms']=['方法']
            plan=d/'plan.json';plan.write_text(json.dumps(p,ensure_ascii=False))
            out=d/'render'
            with self.assertRaisesRegex(ValueError,'Sensitive term'):
                render(plan,out)
            self.assertFalse((out/'final.mp4').exists())
            self.assertFalse((out/'visual.mp4').exists())
            self.assertFalse((out/'captions.srt').exists())
            self.assertFalse((out/'base.mp4').exists())
            self.assertEqual(json.loads((out/'privacy_qa.json').read_text())['coverage'],'failed_text_leak')

    def test_tail_hold_and_final_mask(self):
        p=self.plan();p['tail_hold_frames']=15
        p['privacy_targets'][0]['visible'].append(dict(clip_id='t',start=3.9,end=4.5))
        p['privacy_events'].append(dict(id='tail',target_id='person-name',clip_id='t',
                                        start=3.9,end=4.5,motion='static',box=[.72,.21,.15,.055]))
        c=compile_plan(p);self.assertEqual(c['frame_count'],135)
        self.assertEqual(c['_privacy']['events'][-1]['end_frame'],135)
        p['privacy_events'][-1]['end']=4.0
        with self.assertRaisesRegex(ValueError,'uncovered'):compile_plan(p)

    def test_face_and_untrusted_style(self):
        p=self.plan();p['privacy_targets'][0]['kind']='face';p['privacy_events'][0]['style_id']='cloud'
        with self.assertRaisesRegex(ValueError,'Invalid privacy style'):compile_plan(p)
        p['privacy_events'][0]['style_id']='face-patch'
        self.assertEqual(compile_plan(p)['_privacy']['events'][0]['style_id'],'face-patch')
        self.assertGreaterEqual(len(options(p,'person-name')),2)


if __name__=='__main__':unittest.main()
