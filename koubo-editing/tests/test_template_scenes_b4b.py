import copy,hashlib,sys,unittest
from pathlib import Path
from PIL import Image,ImageChops
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_template_scenes import plan,painter,variant_for_kind
from template_scenes import audit_layout,layout
from template_scenes_b4b import KINDS,title,vertical
from template_contracts import validate
from template_catalog import get

def fixture(k):
    p=plan(k);p['template_delivery']='preview';e=p['scene_captions'][0]['phrases'][0];e['id']='p0';e['runs']=[dict(text='方法',role='body'),dict(text='清楚',role='keyword')]
    return p

def translation(p):
    p['scene_captions'][0]['phrases'][0]['mode']='bilingual';p['scene_translations']=[dict(phrase_id='p0',source_text='方法清楚',text='Make the method clear.',language='en',start=.15,end=3.7,review_status='reviewed',reviewer='synthetic test')]

class B4bTests(unittest.TestCase):
    def test_contract_assets(self):
        for k in KINDS:validate(get(variant_for_kind(k))['_contract'],verify_assets=True)
    def test_distinct_title_geometries(self):
        ims=[title(painter(fixture(k))) for k in KINDS];self.assertEqual(len({i.size for i in ims}),4);self.assertEqual(len({hashlib.sha256(i.tobytes()).hexdigest() for i in ims}),4)
    def test_eight_aspects(self):
        for k in KINDS:
            for h in (960,1280):
                p=fixture(k);p['height']=h;self.assertTrue(audit_layout(painter(p))['passed'])
    def test_three_phrase_stagger(self):
        for k in ('neon','warm'):
            p=fixture(k);p['clips'][0]['words']=[dict(text='方法要清楚',start=.1,end=2)];p['scene_captions'][0]['phrases']=[dict(id=str(i),text=t,start=.1+i*.7,end=3.8) for i,t in enumerate(['方法','要','清楚'])];a=painter(p);self.assertTrue(audit_layout(a)['passed']);es=[e for e in layout(a) if e['role']=='caption'];self.assertEqual(len(es),3)
            src=Image.new('RGB',(720,960));box=tuple(map(round,es[0]['box']));self.assertEqual(a.paint(src,a.p['clips'][0],.6).crop(box).tobytes(),a.paint(src,a.p['clips'][0],2).crop(box).tobytes())
    def test_three_phrase_unsupported_mono(self):
        p=fixture('mono');e=p['scene_captions'][0]['phrases'][0];p['scene_captions'][0]['phrases']=[e,copy.deepcopy(e)]
        with self.assertRaises(ValueError):painter(p)
    def test_vertical_is_tall_not_rotated_sentence(self):
        p=fixture('purple');e=p['scene_captions'][0]['phrases'][0];e.update(mode='vertical',x=.82,y=.3,reason='synthetic open right margin');a=painter(p);self.assertTrue(audit_layout(a)['passed']);im=next(e['image'] for e in layout(a) if e['role']=='caption');self.assertGreater(im.height,im.width*2)
    def test_vertical_protected_face_rejected(self):
        p=fixture('purple');e=p['scene_captions'][0]['phrases'][0];e.update(mode='vertical',x=.3,y=.3,reason='test');p['protected_regions']=[dict(start=0,end=4,box=[.2,.2,.7,.7])]
        with self.assertRaisesRegex(ValueError,'protected'):audit_layout(painter(p))
    def test_vertical_outside_canvas_rejected(self):
        p=fixture('purple');p['scene_captions'][0]['phrases'][0].update(mode='vertical',x=.98,y=.8,reason='test')
        with self.assertRaises(ValueError):audit_layout(painter(p))
    def test_vertical_needs_reason(self):
        p=fixture('purple');p['scene_captions'][0]['phrases'][0].update(mode='vertical',x=.8,y=.3)
        with self.assertRaises(ValueError):painter(p)
    def test_translation_separate_layer(self):
        p=fixture('purple');translation(p);es=layout(painter(p));e=next(e for e in es if e['role']=='translation');self.assertEqual((e['start'],e['end']),(.15,3.7))
    def test_bilingual_missing_translation_fails(self):
        p=fixture('purple');p['scene_captions'][0]['phrases'][0]['mode']='bilingual'
        with self.assertRaises(ValueError):painter(p)
    def test_normal_cannot_hide_translation(self):
        p=fixture('purple');translation(p);p['scene_captions'][0]['phrases'][0]['mode']='normal'
        with self.assertRaises(ValueError):painter(p)
    def test_stale_translation_fails(self):
        p=fixture('purple');translation(p);p['scene_translations'][0]['source_text']='别的文字'
        with self.assertRaises(ValueError):painter(p)
    def test_anchored_vertical_tag(self):
        p=fixture('mono');p['scene_tags']=[dict(phrase_id='p0',text='清楚',start=.2,end=3.5,reason='test',orientation='vertical')];self.assertTrue(audit_layout(painter(p))['passed'])
    def test_tag_hallucination_rejected(self):
        p=fixture('mono');p['scene_tags']=[dict(phrase_id='p0',text='赚钱',start=.2,end=3.5,reason='test')]
        with self.assertRaises(ValueError):painter(p)
    def test_tag_clock_rejected(self):
        p=fixture('mono');p['scene_tags']=[dict(phrase_id='p0',text='方法',start=.2,end=3.9,reason='test')]
        with self.assertRaises(ValueError):painter(p)
    def test_unique_ids(self):
        p=fixture('neon');e=copy.deepcopy(p['scene_captions'][0]['phrases'][0]);p['scene_captions'][0]['phrases'].append(e)
        with self.assertRaises(ValueError):painter(p)
    def test_unimplemented_spotlight_rejected(self):
        p=fixture('mono');p['scene_canvas']=[dict(kind='spotlight',start=0,end=4)]
        with self.assertRaises(ValueError):painter(p)
    def test_unknown_style_rejected(self):
        for k in KINDS:
            p=fixture(k);p['scene_captions'][0]['phrases'][0]['mode']='secret'
            with self.assertRaises(ValueError):painter(p)
    def test_preserves_approved_wordstream(self):
        p=fixture('warm');p['scene_captions'][0]['phrases'][0]['runs']=[dict(text='方法错误')]
        with self.assertRaisesRegex(ValueError,'transcript'):painter(p)

if __name__=='__main__':unittest.main()
