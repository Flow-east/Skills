import sys,unittest,tempfile,subprocess,json
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from timeline import compile_plan,base_filter,probe
from boundary_transitions import compile_transitions,apply
from opening_hooks import suggest


def fixture():
    return {'version':2,'fps':30,'width':128,'height':128,'source':'/tmp/unused.mp4','source_duration':2,
      'font':'/tmp/unused.ttf','template':'knowledge','clips':[
       {'id':'problem','start':0,'end':1,'reason':'真实问题','words':[{'text':'为什么会这样？','start':.1,'end':.78}]},
       {'id':'answer','start':1,'end':2,'reason':'真实答案','words':[{'text':'因为这里有条件。','start':1.18,'end':1.8}]}]}


class HookTests(unittest.TestCase):
    def test_suggest_exact_source_no_auto_reorder(self):
        p=compile_plan(fixture());rows=suggest(p)
        self.assertEqual(rows[0]['method'],'original')
        self.assertEqual(rows[0]['proposed_order'],['problem','answer'])
        self.assertTrue(all(x['status']=='needs_editorial_review' for x in rows))
        self.assertTrue(all(x['source_excerpt'] in ''.join(w['text'] for c in p['clips'] for w in c['words']) for x in rows))
    def test_frontloaded_hook_requires_payoff_and_complete_review(self):
        p=fixture();p['allow_reorder']=True;p['clips'].reverse()
        h={'method':'result_first','opening_clip_ids':['answer'],'source_excerpt':'因为这里有条件。',
           'payoff_clip_id':'problem','payoff_reason':'后段解释原先问题','reason':'结论先行',
           'semantic_review':'verified','end_of_speech_review':'verified','duplicate_policy':'moved_not_repeated'}
        p['hook_design']=h
        self.assertEqual(compile_plan(p)['hook_audit']['method'],'result_first')
        p['hook_design']=dict(h,source_excerpt='其实不需要条件')
        with self.assertRaisesRegex(ValueError,'exact text'):compile_plan(p)
        p['hook_design']=dict(h,payoff_clip_id='answer')
        with self.assertRaisesRegex(ValueError,'later payoff'):compile_plan(p)
        p['hook_design']=dict(h,end_of_speech_review='pending')
        with self.assertRaisesRegex(ValueError,'complete spoken ending'):compile_plan(p)


    def test_hook_rejects_word_end_lost_to_frame_rounding_and_dependency(self):
        p=fixture();p['allow_reorder']=True;p['clips'].reverse()
        h={'method':'result_first','opening_clip_ids':['answer'],'source_excerpt':'因为这里有条件。',
           'payoff_clip_id':'problem','payoff_reason':'后面说明问题','reason':'结论前置',
           'semantic_review':'verified','end_of_speech_review':'verified','duplicate_policy':'moved_not_repeated'}
        p['hook_design']=h
        p['clips'][0]['end']=1.98
        p['clips'][0]['words'][0]['end']=2.0
        with self.assertRaisesRegex(ValueError,'spoken ending'):
            compile_plan(p)
        p=fixture();p['allow_reorder']=True;p['clips'].reverse()
        p['clips'][0]['words'][0]['text']='所以这里有条件。'
        p['hook_design']=dict(h,source_excerpt='所以这里有条件。')
        with self.assertRaisesRegex(ValueError,'context resolution'):
            compile_plan(p)


class BoundaryTests(unittest.TestCase):
    def test_dip_real_frames_same_clock_and_visual_bridge(self):
        p=fixture();p['boundary_transitions']=[{'after_clip_id':'problem','before_clip_id':'answer',
          'kind':'dip_to_dark','frames':8,'reason':'问题进入答案','speech_clearance_verified':True}]
        q=compile_plan(p);events=q['boundary_events']
        self.assertEqual((q['frame_count'],q['duration']),(60,2.0))
        self.assertEqual((events[0]['cut_frame'],events[0]['start_frame'],events[0]['end_frame']),(30,26,34))
        im=Image.new('RGB',(128,128),'#eeeeee')
        normal=apply(im,25,events).getpixel((32,32))[0]
        near_cut=apply(im,29,events).getpixel((32,32))[0]
        at_cut=apply(im,30,events).getpixel((32,32))[0]
        recovered=apply(im,33,events).getpixel((32,32))[0]
        self.assertEqual((normal,recovered),(238,238))
        self.assertGreater(near_cut,at_cut)
    def test_no_speech_cutting_or_fake_match(self):
        p=fixture();p['boundary_transitions']=[{'after_clip_id':'problem','before_clip_id':'answer',
           'kind':'dip_to_dark','frames':8,'reason':'章节切换','speech_clearance_verified':True}]
        p['clips'][0]['words'][0]['end']=.96
        with self.assertRaisesRegex(ValueError,'crosses speech'):compile_plan(p)
        p=fixture();p['boundary_transitions']=[{'after_clip_id':'problem','before_clip_id':'answer',
           'kind':'match_cut','reason':'相同构图接续'}]
        with self.assertRaisesRegex(ValueError,'match_basis'):compile_plan(p)
        p['boundary_transitions'][0]['match_basis']='脸部比例与视线方向一致'
        self.assertEqual(compile_plan(p)['boundary_events'][0]['kind'],'match_cut')
    def test_transition_rejects_captions_without_alignment_and_overlap(self):
        p=fixture();p['clips'][0].pop('words');p['clips'][0]['caption']='问题';p['boundary_transitions']=[
          {'after_clip_id':'problem','before_clip_id':'answer','kind':'dip_to_dark','frames':8,
           'reason':'章节','speech_clearance_verified':True}]
        with self.assertRaisesRegex(ValueError,'caption-only'):compile_plan(p)
        p=fixture();p['boundary_transitions']=[
          {'after_clip_id':'answer','before_clip_id':'problem','kind':'cut','reason':'错误顺序'}]
        with self.assertRaisesRegex(ValueError,'adjacent'):compile_plan(p)

    def test_native_frame_fit_does_not_pad_and_cover_is_explicit(self):
        p=fixture();p['frame_fit']='native';native=base_filter(compile_plan(p))
        self.assertIn('scale=128:128,setsar=1',native)
        self.assertNotIn('pad=',native)
        p['frame_fit']='cover';cover=base_filter(compile_plan(p))
        self.assertIn('force_original_aspect_ratio=increase,crop=128:128',cover)

    def test_no_duration_change_in_ffmpeg_base(self):
        with tempfile.TemporaryDirectory() as d:
            d=Path(d);src=d/'source.mp4';out=d/'base.mp4';flt=d/'filter.txt'
            subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=c=red:s=128x128:r=30:d=1',
              '-f','lavfi','-i','color=c=blue:s=128x128:r=30:d=1',
              '-f','lavfi','-i','sine=frequency=440:sample_rate=48000:duration=2',
              '-filter_complex','[0:v][1:v]concat=n=2:v=1:a=0[v]',
              '-map','[v]','-map','2:a','-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac',str(src)],check=True)
            p=fixture();p['source']=str(src)
            p['boundary_transitions']=[{'after_clip_id':'problem','before_clip_id':'answer','kind':'dip_to_dark',
              'frames':8,'reason':'答案开始','speech_clearance_verified':True}]
            q=compile_plan(p);flt.write_text(base_filter(q))
            subprocess.run(['ffmpeg','-v','error','-i',str(src),'-filter_complex_script',str(flt),
              '-map','[v]','-map','[a]','-c:v','libx264','-c:a','aac',str(out)],check=True)
            meta=probe(out);v=next(x for x in meta['streams'] if x['codec_type']=='video');a=next(x for x in meta['streams'] if x['codec_type']=='audio')
            self.assertEqual(int(v['nb_frames']),60)
            self.assertLess(abs(float(a['duration'])-2),.04)

if __name__=='__main__':unittest.main()
