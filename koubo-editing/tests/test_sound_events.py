import sys, unittest
from unittest.mock import patch
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from timeline import compile_plan
from sound_events import compile_events, add_events, LIB
import numpy as np

class SoundEventsTest(unittest.TestCase):
    def setUp(self):
        # Legacy regression cases explicitly approve Kenney only inside tests.
        # Actual catalog keeps Kenney rejected and new common assets selectable.
        import sound_events
        self._patch=patch.object(sound_events,'library',return_value={
            k:dict(v,selection_status='approved') for k,v in sound_events.library().items()})
        self._patch.start()
    def tearDown(self):
        self._patch.stop()
    def plan(self):
        p=dict(fps=30,template='knowledge',source='unused',source_duration=5,font='unused',
          allow_reorder=True,audio={'cues':False,'bed':'none'},clips=[
            dict(id='late',start=3,end=4,reason='hook',caption='X',words=[{'text':'结论','start':3.2,'end':3.5}]),
            dict(id='first',start=0,end=1,reason='detail',caption='Y',words=[{'text':'前提','start':.3,'end':.6}]),
            dict(id='repeat',start=3,end=4,reason='repeat',caption='Z',words=[{'text':'结论','start':3.2,'end':3.5}])])
        return compile_plan(p)
    def event(self,id='one',clip='late',word=0,asset='kenney-pluck-002',role='keyword'):
        return dict(id=id,clip_id=clip,word_index=word,asset_id=asset,role=role,reason='确认的重点词')
    def test_reorder_and_duplicate_source_instance(self):
        p=self.plan();p['sound_events']=[self.event(),self.event('two','repeat')]
        e=compile_events(p)
        self.assertAlmostEqual(e[0]['anchor_output'],.5)
        self.assertAlmostEqual(e[1]['anchor_output'],2.5)
        self.assertNotEqual(e[0]['start_output'],e[1]['start_output'])
        samples=np.zeros(round(p['duration']*48000),dtype=np.float32)
        self.assertEqual(len(add_events(samples,p)),2)
        self.assertGreater(abs(samples).max(),0)
    def test_close_events_rejected(self):
        p=self.plan();p['sound_events']=[self.event(),dict(self.event('two'),offset=.12)]
        with self.assertRaisesRegex(ValueError,'Overlapping'): compile_events(p)
    def test_boundary_and_bad_anchor(self):
        p=self.plan();p['sound_events']=[dict(self.event(),source_time=3.01,word_index=None)]
        with self.assertRaises(ValueError): compile_events(p)
        p['sound_events']=[dict(self.event(),word_index=10)]
        with self.assertRaises(ValueError): compile_events(p)
        p['sound_events']=[dict(id='start',clip_id='late',source_time=3.01,asset_id='kenney-open-002',role='transition',reason='进入话题')]
        with self.assertRaisesRegex(ValueError,'clip lead/tail'): compile_events(p)
    def test_missing_asset_hash_and_style(self):
        p=self.plan();p['sound_events']=[self.event()];p['audio']['sound_style']='bright'
        with self.assertRaisesRegex(ValueError,'not allowed'): compile_events(p)
        p['audio']['sound_style']='neutral'
        import sound_events
        self._patch.stop()
        original=sound_events.LIB
        try:
            sound_events.LIB=Path('/no/such/assets')
            with self.assertRaisesRegex(ValueError,'Missing sound catalog'): compile_events(p)
        finally: sound_events.LIB=original
    def test_modified_asset_hash_is_rejected(self):
        p=self.plan();p['sound_events']=[self.event()]
        import sound_events
        real=sound_events.library()
        altered={k:dict(v) for k,v in real.items()}
        altered['kenney-pluck-002']['sha256']='0'*64
        with patch.object(sound_events,'library',return_value=altered):
            with self.assertRaisesRegex(ValueError,'modified sound asset'): compile_events(p)
    def test_catalog_retains_rejected_kenney_and_74_new_assets(self):
        import hashlib, wave
        self._patch.stop()
        from sound_events import library
        lib=library()
        rejected=[a for a in lib.values() if a['selection_status']=='rejected_by_user']
        approved=[a for a in lib.values() if a['selection_status']=='approved']
        self.assertEqual((len(rejected),len(approved)),(6,74))
        self.assertIn('Creative Commons Zero',(LIB/'Kenney-License.txt').read_text())
        for a in rejected:
            self.assertEqual(a['source_url'],'https://kenney.nl/assets/interface-sounds')
        for a in approved:
            self.assertEqual(a['license'],'CC0 1.0')
            self.assertTrue(a['source_url'].startswith('https://freesound.org/people/'))
            self.assertIn(a['role'],a['roles'])
            self.assertEqual(hashlib.sha256((LIB/a['source_file']).read_bytes()).hexdigest(),a['source_sha256'])
            self.assertGreaterEqual(len(a['selection_guidance']),10)
        for a in lib.values():
            self.assertEqual(hashlib.sha256((LIB/a['file']).read_bytes()).hexdigest(),a['sha256'])
            with wave.open(str(LIB/a['file'])) as wav:
                self.assertEqual((wav.getframerate(),wav.getnchannels(),wav.getsampwidth()),(48000,1,2))
                self.assertAlmostEqual(wav.getnframes()/48000,a['duration'],places=6)

    def test_new_asset_multiple_semantic_roles_and_style(self):
        self._patch.stop()
        p=self.plan()
        p['sound_events']=[self.event(asset='common-005',role='sentence_end')]
        events=compile_events(p)
        self.assertEqual(events[0]['asset_id'],'common-005')
        self.assertEqual(events[0]['role'],'sentence_end')
        samples=np.zeros(round(p['duration']*48000),dtype=np.float32)
        add_events(samples,p)
        self.assertGreater(abs(samples).max(),0)
        p['audio']['sound_style']='minimal'
        with self.assertRaisesRegex(ValueError,'not allowed'): compile_events(p)

    def test_user_rejected_stock_cannot_render(self):
        self._patch.stop()
        p=self.plan();p['sound_events']=[self.event()]
        with self.assertRaisesRegex(ValueError,'not approved'): compile_events(p)
    def test_legacy_no_events(self):
        p=self.plan();p.pop('audio'); self.assertEqual(compile_events(p),[])
        p['sound_events']=[self.event()]
        with self.assertRaisesRegex(ValueError,'cues=false'): compile_events(p)
    def test_tail_rejected_and_gain_limit(self):
        p=self.plan();p['sound_events']=[dict(self.event('end','repeat'),source_time=3.99,word_index=None)]
        with self.assertRaises(ValueError): compile_events(p)
        p['sound_events']=[dict(self.event(),gain=.21)]
        with self.assertRaisesRegex(ValueError,'gain'): compile_events(p)
if __name__=='__main__': unittest.main()
