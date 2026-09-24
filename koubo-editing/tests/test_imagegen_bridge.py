import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from PIL import Image, ImageDraw, ImageChops

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from imagegen_bridge import grant, check, revoke, record_cost, discover, video_id, _read
from illustrations import audit
from render_template import Painter
from timeline import compile_plan
from test_template_scenes import plan as scene_plan


class ConsentTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.store=Path(self.tmp.name)/'config'/'consent.json'
        self.video='a'*64
        self.args=dict(skill='generic-imagegen',service='provider-A',categories=['prompt'])

    def test_video_grants_then_permanent_and_revoke(self):
        for i in range(3):
            v=hex(i+1)[2:]*64
            g=grant(self.store,**self.args,scope='video',video=v)
            self.assertEqual(check(self.store,**self.args,video=v,estimated_minor=0)['id'],g['id'])
            self.assertIsNone(check(self.store,**self.args,video='f'*64,estimated_minor=0))
        g=grant(self.store,**self.args,scope='permanent')
        self.assertEqual(check(self.store,**self.args,video='f'*64,estimated_minor=0)['id'],g['id'])
        revoke(self.store,g['id'])
        self.assertIsNone(check(self.store,**self.args,video='f'*64,estimated_minor=0))
        self.assertEqual(self.store.stat().st_mode & 0o777,0o600)
        self.assertNotIn('api_key',self.store.read_text())

    def test_reauthorize_for_provider_data_or_cost(self):
        g=grant(self.store,**self.args,scope='permanent',max_per_call_minor=25,max_total_minor=50,currency='CNY')
        self.assertIsNone(check(self.store,skill='generic-imagegen',service='provider-B',categories=['prompt'],estimated_minor=0))
        self.assertIsNone(check(self.store,**dict(self.args,categories=['video_frame']),estimated_minor=0))
        self.assertIsNone(check(self.store,**self.args,estimated_minor=26,currency='CNY'))
        self.assertIsNone(check(self.store,**self.args,estimated_minor=20,currency='USD'))
        self.assertEqual(check(self.store,**self.args,estimated_minor=20,currency='CNY')['id'],g['id'])
        record_cost(self.store,g['id'],20)
        self.assertIsNone(check(self.store,**self.args,estimated_minor=31,currency='CNY'))
        revoke(self.store,g['id'],categories=['prompt'])
        with self.assertRaises(ValueError):revoke(self.store,g['id'],categories=['video_frame'])

    def test_actual_overage_is_recorded_and_revokes_grant(self):
        g=grant(self.store,**self.args,scope='permanent',max_per_call_minor=25,
                max_total_minor=50,currency='CNY')
        with self.assertRaisesRegex(ValueError,'recorded'):
            record_cost(self.store,g['id'],30)
        row=_read(self.store)['grants'][0]
        self.assertEqual(row['used_minor'],30)
        self.assertTrue(row['revoked'])
        self.assertIsNone(check(self.store,**self.args,estimated_minor=1,currency='CNY'))

    def test_video_hash_and_discovery_no_execution(self):
        source=Path(self.tmp.name)/'source.mp4';source.write_bytes(b'test')
        self.assertEqual(video_id(source),hashlib.sha256(b'test').hexdigest())
        skill=Path(self.tmp.name)/'skills'/'picture';skill.mkdir(parents=True)
        (skill/'SKILL.md').write_text('---\nname: picture\ndescription: Generate raster images and cutouts\n---\nRead conditions before use.\n')
        self.assertEqual([r['name'] for r in discover([Path(self.tmp.name)/'skills'])],['picture'])
        self.assertEqual(len(_read(self.store)['grants']),0)

    def test_invalid_or_missing_consent(self):
        self.assertIsNone(check(self.store,**self.args,estimated_minor=0))
        with self.assertRaises(ValueError):grant(self.store,**self.args,scope='video',video='not-sha')
        with self.assertRaises(ValueError):grant(self.store,skill='x',service='y',categories=['unknown'],scope='permanent')
        with self.assertRaises(ValueError):grant(self.store,**self.args,scope='permanent',max_per_call_minor=1)


class IllustrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.file=Path(self.tmp.name)/'sticker.png'
        im=Image.new('RGBA',(64,64));ImageDraw.Draw(im).ellipse((6,6,58,58),fill='#e82c54')
        im.save(self.file)
        self.ev={'id':'object-1','path':str(self.file),'sha256':hashlib.sha256(self.file.read_bytes()).hexdigest(),
                 'start':1.1,'end':2.1,'time_space':'output','x':.76,'y':.28,'width':.12,
                 'reason':'具体物体示意','source':{'kind':'local'}}

    def plan(self):
        p=scene_plan('pink');p['illustrations']=[dict(self.ev)]
        return p

    def test_scene_overlay_and_audit(self):
        p=compile_plan(self.plan());painter=Painter(p)
        self.assertEqual(audit(painter.illustrations)[0]['sha256'],self.ev['sha256'])
        bg=Image.new('RGB',(720,960),'#39424e')
        early=painter.paint(bg,p['clips'][0],.5)
        visible=painter.paint(bg,p['clips'][0],1.5)
        x0,y0,x1,y1=painter.illustrations[0]['box']
        self.assertIsNotNone(ImageChops.difference(early.crop((x0,y0,x1,y1)),visible.crop((x0,y0,x1,y1))).getbbox())

    def test_generated_asset_metadata_with_local_fixture(self):
        # A synthetic cutout tests the renderer contract; no remote generation is claimed.
        p=self.plan()
        p['illustrations'][0]['source']={'kind':'generated','skill':'test-fixture',
                                          'service':'local-mock','grant_id':'fixture-only'}
        result=Painter(compile_plan(p))
        self.assertEqual(audit(result.illustrations)[0]['source']['service'],'local-mock')

    def test_unsafe_or_false_asset_rejected(self):
        for patch in ({'sha256':'0'*64},{'x':.98},{'x':.35,'y':.75},{'source':{'kind':'generated','skill':'x'}},
                      {'x':.4,'y':.74}):
            p=self.plan();p['illustrations'][0].update(patch)
            with self.subTest(patch=patch):
                with self.assertRaises(ValueError):Painter(compile_plan(p))
        img=Image.new('RGB',(64,64),'#e82c54');img.save(self.file)
        p=self.plan();p['illustrations'][0]['sha256']=hashlib.sha256(self.file.read_bytes()).hexdigest()
        with self.assertRaisesRegex(ValueError,'transparency'):Painter(compile_plan(p))

    def test_protected_region_blocks(self):
        p=self.plan();p['protected_regions']=[dict(start=0,end=4,box=[.7,.2,.97,.6])]
        with self.assertRaisesRegex(ValueError,'protected'):Painter(compile_plan(p))


if __name__=='__main__':unittest.main()
