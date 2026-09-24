import copy,hashlib,sys,unittest
from pathlib import Path
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_template_scenes import plan,painter,variant_for_kind
from template_scenes import audit_layout,layout,video_layer
from template_scenes_b4c import KINDS,title,line,icon
from template_contracts import validate
from template_catalog import get
from font_guard import display_text

def fixture(k):
    p=plan(k);p['template_delivery']='preview';e=p['scene_captions'][0]['phrases'][0];e['id']='p0';e['runs']=[dict(text='方法',role='body'),dict(text='清楚',role='keyword')]
    if k=='elegantpink':p['scene_translations']=[dict(phrase_id='p0',source_text='方法清楚',text='Make the method clear.',language='en',start=.15,end=3.7,review_status='reviewed',reviewer='synthetic fixture')]
    return p

class B4cTests(unittest.TestCase):
    def test_contracts(self):
        for k in KINDS:validate(get(variant_for_kind(k))['_contract'],verify_assets=True)
    def test_four_distinct_title_geometries(self):
        ims=[title(painter(fixture(k))) for k in KINDS];self.assertEqual(len({i.size for i in ims}),4);self.assertEqual(len({hashlib.sha256(i.tobytes()).hexdigest() for i in ims}),4)
    def test_eight_aspects(self):
        for k in KINDS:
            for h in (960,1280):
                p=fixture(k);p['height']=h;self.assertTrue(audit_layout(painter(p))['passed'])
    def test_promo_no_forced_title(self):
        p=fixture('promo');p['title']='';p.pop('scene_title_lines');self.assertFalse(any(e['role']=='title' for e in layout(painter(p))))
    def test_elegant_white_caption_and_small_independent_translation(self):
        a=painter(fixture('elegantpink'));es=layout(a);cap=next(e for e in es if e['role']=='caption');en=next(e for e in es if e['role']=='translation');self.assertEqual(cap['image'].getpixel((0,0)),(255,255,255,255));self.assertEqual((en['start'],en['end']),(.15,3.7));self.assertLess(en['image'].height,cap['image'].height)
    def test_four_ribbons_independent_clocks(self):
        p=fixture('elegantpink');p['scene_translations']=[];p['clips'][0]['words']=[dict(text='方法要说清楚',start=.1,end=2)];p['scene_captions'][0]['phrases']=[dict(id=str(i),text=t,mode='ribbon',start=.1+i*.55,end=3.8) for i,t in enumerate(['方法','要','说','清楚'])];a=painter(p);self.assertTrue(audit_layout(a)['passed']);caps=[e for e in layout(a) if e['role']=='caption'];self.assertEqual(len(caps),4);self.assertEqual(caps[0]['image'].getpixel((0,0)),(240,0,183,255));src=Image.new('RGB',(720,960));box=tuple(map(round,caps[0]['box']));self.assertEqual(a.paint(src,a.p['clips'][0],.5).crop(box).tobytes(),a.paint(src,a.p['clips'][0],2).crop(box).tobytes())
    def test_no_silent_translation_in_ribbon(self):
        p=fixture('elegantpink');p['scene_captions'][0]['phrases'][0]['mode']='ribbon'
        with self.assertRaises(ValueError):painter(p)
    def test_missing_translation_rejected(self):
        p=fixture('elegantpink');p['scene_translations']=[]
        with self.assertRaises(ValueError):painter(p)
    def test_translation_changed_source_rejected(self):
        p=fixture('elegantpink');p['scene_translations'][0]['source_text']='错误'
        with self.assertRaises(ValueError):painter(p)
    def test_ribbon_bilingual_cannot_mix(self):
        p=fixture('elegantpink');e=p['scene_captions'][0]['phrases'][0];p['scene_captions'][0]['phrases'].append(dict(id='p1',text='方法',start=1,end=3,mode='ribbon'))
        with self.assertRaises(ValueError):painter(p)
    def test_circle_white_background_and_no_forced_inset(self):
        p=fixture('elegantpink');p['scene_canvas']=[dict(kind='circle',start=0,end=4,center=[.5,.4],radius=.28,background='#FFFFFF',reason='synthetic composition only')];a=painter(p);im=video_layer(a,Image.new('RGB',(720,960),'red'),1);self.assertEqual(im.getpixel((0,0))[:3],(255,255,255));self.assertEqual(im.getpixel((360,384))[:3],(255,0,0))
    def test_retained_list_can_outlive_phrase(self):
        p=fixture('elegantpink');p['scene_callouts']=[dict(phrase_id='p0',text='清楚',start=.3,end=3.95,slot=0,side='right',reason='retain')];a=painter(p);self.assertTrue(audit_layout(a)['passed']);self.assertEqual(next(e for e in layout(a) if e['role']=='callout')['end'],3.95)
    def test_list_slot_collision(self):
        p=fixture('elegantpink');e=dict(phrase_id='p0',text='清楚',start=.3,end=3.95,slot=0,reason='test');p['scene_callouts']=[e,copy.deepcopy(e)]
        with self.assertRaises(ValueError):painter(p)
    def test_list_anchor_pair_required(self):
        p=fixture('elegantpink');p['scene_callouts']=[dict(phrase_id='p0',text='清楚',start=.3,end=3.9,slot=0,x=.1,reason='test')]
        with self.assertRaises(ValueError):painter(p)
    def test_list_needs_semantic_anchor(self):
        p=fixture('elegantpink');p['scene_callouts']=[dict(phrase_id='p0',text='购物',start=.3,end=3.9,slot=1,reason='test')]
        with self.assertRaises(ValueError):painter(p)
    def test_original_icons_transparent_and_distinct(self):
        a=painter(fixture('promo'));ims=[icon(a,k) for k in ('megaphone','cart','heart','heart_cursor')];self.assertEqual(len({hashlib.sha256(i.tobytes()).hexdigest() for i in ims}),4)
        for im in ims:self.assertEqual(im.getchannel('A').getextrema(),(0,255))
    def test_anchored_icon_tag(self):
        p=fixture('promo');p['scene_tags']=[dict(phrase_id='p0',text='清楚',start=.3,end=3.5,reason='emphasis',icon='megaphone')];self.assertTrue(audit_layout(painter(p))['passed'])
    def test_wrong_icon_rejected(self):
        p=fixture('browngold');p['scene_tags']=[dict(phrase_id='p0',text='方法',start=.3,end=3.5,reason='test',icon='cart')]
        with self.assertRaises(ValueError):painter(p)
    def test_arc_geometry_and_long_rejection(self):
        p=fixture('hotpink');p['scene_captions'][0]['phrases'][0]['mode']='arc';a=painter(p);self.assertTrue(audit_layout(a)['passed']);im=next(e['image'] for e in layout(a) if e['role']=='caption');normal=next(e['image'] for e in layout(painter(fixture('hotpink'))) if e['role']=='caption');self.assertNotEqual(im.size,normal.size)
        p['scene_captions'][0]['phrases'][0].update(runs=[dict(text='方法清楚方法清楚方法')]);p['clips'][0]['words']=[dict(text='方法清楚方法清楚方法',start=.1,end=2)]
        with self.assertRaises(ValueError):painter(p)
    def test_bounded_comic_accents(self):
        p=fixture('hotpink');p['scene_accents']=[dict(kind='rays',start=.2,end=2,x=.04,y=.25,width=.1,height=.25,reason='margin')];self.assertTrue(audit_layout(painter(p))['passed'])
    def test_accents_cannot_cover_face(self):
        p=fixture('hotpink');p['scene_accents']=[dict(kind='rays',start=.2,end=2,x=.3,y=.3,width=.2,height=.2,reason='test')];p['protected_regions']=[dict(start=0,end=4,box=[.25,.25,.7,.7])]
        with self.assertRaisesRegex(ValueError,'protected'):audit_layout(painter(p))
    def test_accents_do_not_bypass_safe_canvas(self):
        p=fixture('hotpink');p['scene_accents']=[dict(kind='hearts',start=.2,end=2,x=.95,y=.3,width=.2,height=.2,reason='test')]
        with self.assertRaises(ValueError):audit_layout(painter(p))
    def test_old_templates_reject_new_accents(self):
        p=plan('pink');p['scene_accents']=[dict(kind='rays',start=.2,end=2)]
        with self.assertRaises(ValueError):painter(p)
    def test_reviewed_identity(self):
        p=fixture('browngold');p['scene_identity']=[dict(name='示例',detail='合成测试资料',start=.2,end=3.5,x=.06,y=.28,review_status='reviewed',source='synthetic data',reviewer='test',reason='not real identity')];self.assertIn('合成测试资料',display_text(p));self.assertTrue(audit_layout(painter(p))['passed'])
    def test_identity_rows_cannot_invent_text(self):
        p=fixture('browngold');p['scene_identity']=[dict(name='示例',detail='合成资料',detail_lines=['虚构头衔'],start=.2,end=3.5,x=.06,y=.28,review_status='reviewed',source='test',reviewer='test',reason='test')]
        with self.assertRaises(ValueError):painter(p)
    def test_identity_requires_review(self):
        p=fixture('browngold');p['scene_identity']=[dict(name='示例',detail='合成',start=.2,end=3.5,x=.06,y=.28)]
        with self.assertRaises(ValueError):painter(p)
    def test_segmentation_not_silently_supported(self):
        for k in ('browngold','hotpink'):
            p=fixture(k);p['scene_canvas']=[dict(kind='subject_outline',start=0,end=4)]
            with self.assertRaises(ValueError):painter(p)
    def test_digit_english_and_punctuation_retained(self):
        text='AI效率提升3.5%？'
        for k in ('promo','browngold','hotpink'):
            p=fixture(k);p['clips'][0]['words']=[dict(text=text,start=.1,end=2)];p['scene_captions'][0]['phrases'][0].update(text=text,runs=[dict(text=text)]);self.assertTrue(audit_layout(painter(p))['passed'])
    def test_approved_words_cannot_change(self):
        p=fixture('promo');p['scene_captions'][0]['phrases'][0]['runs']=[dict(text='方法错误')]
        with self.assertRaisesRegex(ValueError,'transcript'):painter(p)

if __name__=='__main__':unittest.main()
