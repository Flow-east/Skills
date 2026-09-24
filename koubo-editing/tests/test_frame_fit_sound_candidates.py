import sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from frame_fit import audit
from timeline import compile_plan
from sound_candidates import suggest

class FrameFitTests(unittest.TestCase):
    def setUp(self):self.source={'width':720,'height':960,'sample_aspect_ratio':'1:1'}
    def test_mismatch_requires_explicit_choice_before_render(self):
        p={'width':360,'height':640}
        with self.assertRaisesRegex(ValueError,'no silent padding'):audit(p,self.source)
        p['frame_fit']='contain'
        with self.assertRaisesRegex(ValueError,'frame_fit_reason'):audit(p,self.source)
        p['frame_fit_reason']='用户明确要求留边展示完整画面'
        self.assertTrue(audit(p,self.source)['mismatch'])
        p['frame_fit']='cover';self.assertEqual(audit(p,self.source)['mode'],'cover')
        p['frame_fit']='native'
        with self.assertRaisesRegex(ValueError,'matching source'):audit(p,self.source)
    def test_native_and_old_matching_plan(self):
        p={'width':720,'height':960,'frame_fit':'native'}
        self.assertFalse(audit(p,self.source)['mismatch'])
        p.pop('frame_fit')
        self.assertTrue(audit(p,self.source)['legacy_default'])
    def test_sar_and_rotation_are_display_aspect(self):
        s=dict(self.source,sample_aspect_ratio='2:1')
        self.assertFalse(audit({'width':720,'height':480,'frame_fit':'native'},s)['mismatch'])
        s=dict(self.source,side_data_list=[{'rotation':90}])
        self.assertFalse(audit({'width':960,'height':720,'frame_fit':'native'},s)['mismatch'])

class SoundCandidatesTests(unittest.TestCase):
    def plan(self,gap=.4):
        return compile_plan({'version':2,'source':'/tmp/x.mp4','source_duration':4,'font':'/tmp/f.ttf',
          'width':720,'height':960,'fps':30,'template':'knowledge','audio':{'cues':False},
          'clips':[{'id':'hook','start':0,'end':2,'reason':'真实问题','words':[
               {'text':'什么?','start':.1,'end':.4},{'text':'做AI转型不要先买工具?','start':.9,'end':1.5}]},
               {'id':'body','start':2,'end':4,'reason':'解释','words':[
               {'text':'企业做AI转型先试点后推广','start':2+gap,'end':3.2}]}]})
    def test_short_interjection_not_auto_sfx(self):
        report=suggest(self.plan()); rows=report['decisions'];self.assertEqual(rows[0]['decision'],'leave_silent')
        self.assertTrue(rows[1]['options']);self.assertEqual(rows[1]['semantic_trigger'],'question')
        self.assertEqual(report['policy'],'evidence_only_no_automatic_sound_events')
    def test_gap_blocks_overlay_and_never_mutates_plan(self):
        p=self.plan(.05);p['clips'][0]['words'][-1]['end']=1.9;before=p.get('sound_events');rows=suggest(p)['decisions']
        self.assertEqual(rows[1]['decision'],'leave_silent');self.assertIs(p.get('sound_events'),before)

if __name__=='__main__': unittest.main()
