import copy,hashlib,json,sys,unittest
from pathlib import Path
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_template_scenes import plan,painter,variant_for_kind
from template_scenes import audit_layout,layout,texts
from template_scenes_b3b import KINDS,BILINGUAL,line,title,news_tiles
from template_contracts import validate
from template_catalog import get
from font_guard import inspect_font


def fixture(k,stack=False):
    p=plan(k,stack);p['template_delivery']='preview'
    if k in BILINGUAL:
        p['scene_translations']=[]
        for j,e in enumerate(p['scene_captions'][0]['phrases']):
            e['id']=str(j);p['scene_translations'].append(dict(phrase_id=str(j),source_text=texts(e),text='Make the method clear.',language='en',start=e['start'],end=e['end'],review_status='reviewed',reviewer='test fixture'))
    return p

class B3bTests(unittest.TestCase):
    def test_seven_contracts_validate(self):
        for k in KINDS:validate(get(variant_for_kind(k))['_contract'],verify_assets=True)
    def test_seven_different_title_geometries(self):
        ims=[title(painter(fixture(k))) for k in KINDS]
        self.assertEqual(len({hashlib.sha256(i.tobytes()).hexdigest() for i in ims}),7)
        self.assertGreaterEqual(len({i.size for i in ims}),6)
    def test_fourteen_aspect_layouts(self):
        for k in KINDS:
            for h in (960,1280):
                p=fixture(k);p['height']=h;self.assertTrue(audit_layout(painter(p))['passed'])
    def test_unsupported_state_fails(self):
        for k in KINDS:
            p=fixture(k);p['scene_captions'][0]['phrases'][0]['mode']='auto_magic'
            with self.assertRaises(ValueError):painter(p)
    def test_arbitrary_colors_fail(self):
        p=fixture('navy');p['scene_captions'][0]['phrases'][0]['runs']=[dict(text='方法清楚',fill='#000000')]
        with self.assertRaises(ValueError):painter(p)
    def test_navy_three_phrases_independent(self):
        p=fixture('navy');p['clips'][0]['words']=[dict(text='方法要清楚',start=.1,end=3)]
        p['scene_captions'][0]['phrases']=[dict(text=t,start=a,end=3.8) for t,a in [('方法',.1),('要',1),('清楚',2)]]
        es=[e for e in layout(painter(p)) if e['role']=='caption']
        self.assertEqual([e['start'] for e in es],[.1,1,2]);self.assertEqual(len({e['y'] for e in es}),3)
        self.assertTrue(audit_layout(painter(p))['passed'])
        p['template_variant']='tpl-luxury-gold'
        with self.assertRaises(ValueError):painter(p)
    def test_news_tiles_have_transparent_gaps(self):
        a=painter(fixture('news'));im=news_tiles(a,dict(text='清楚'));cols=[im.getchannel('A').crop((x,0,x+1,im.height)).getbbox() for x in range(im.width)]
        self.assertIn(None,cols[1:-1]);self.assertGreater(im.width/im.height,1.5)
    def test_blue_label_is_smaller_than_display(self):
        p=fixture('vividblue');a=painter(p);normal=next(e for e in layout(a) if e['role']=='caption')
        p['scene_captions'][0]['phrases'][0]['mode']='label';label=next(e for e in layout(painter(p)) if e['role']=='caption')
        self.assertLess(label['image'].height,normal['image'].height)
    def test_crispred_tags_quote_live_phrase(self):
        p=fixture('crispred');p['scene_tags']=[dict(text='+60%',start=.3,end=1,reason='cannot invent metric')]
        with self.assertRaisesRegex(ValueError,'quote'):painter(p)
        p['scene_tags'][0]['text']='清楚';self.assertTrue(audit_layout(painter(p))['passed'])
        p['scene_tags'][0]['end']=3.9
        with self.assertRaisesRegex(ValueError,'quote'):painter(p)
    def test_news_tag_geometry_differs_from_crispred(self):
        values=[]
        for k in ('news','crispred'):
            p=fixture(k);p['scene_tags']=[dict(text='清楚',start=.3,end=1,reason='test')]
            values.append(next(e['image'].size for e in layout(painter(p)) if e['role']=='tag'))
        self.assertNotEqual(*values)
    def test_required_translation_never_silently_dropped(self):
        for k in BILINGUAL:
            p=fixture(k);p['scene_translations']=[]
            with self.assertRaises(ValueError):painter(p)
    def test_nonbilingual_rejects_translation(self):
        p=fixture('biyellow');p['template_variant']='tpl-news-blue'
        with self.assertRaises(ValueError):painter(p)
    def test_long_text_blocks_instead_of_tiny_font(self):
        for k in KINDS:
            with self.assertRaisesRegex(ValueError,'too long'):line(painter(fixture(k)),[dict(text='方法'*80)],50)
    def test_numeric_english_traditional_glyphs(self):
        for k in KINDS:
            a=painter(fixture(k))
            for role in ('title','body','keyword','sticker'):
                self.assertTrue(inspect_font(a.font_path(role),'AI/SOP 效率30%，3.5小时',weight=a.font_weight(role))['passed'])
                report=inspect_font(a.font_path(role),'AI/SOP 效率30%，3.5小時',weight=a.font_weight(role))
                if Path(a.font_path(role)).name=='SmileySans-Oblique.ttf':
                    self.assertFalse(report['passed']);self.assertIn('時',report['missing'])
                else:self.assertTrue(report['passed'])
    def test_no_default_video_reframing(self):
        from template_scenes import video_layer
        src=Image.new('RGB',(720,960),'red')
        for k in KINDS:self.assertEqual(video_layer(painter(fixture(k)),src,1).convert('RGB').tobytes(),src.tobytes())
    def test_soft_entry_envelopes_safe_and_staggered(self):
        for k in ('luxury','navy','crispred','vividblue'):
            a=painter(fixture(k,True));es=[e for e in layout(a) if e['role']=='caption'];self.assertNotEqual(es[0]['x'],es[1]['x']);self.assertTrue(audit_layout(a)['passed'])
    def test_bright_title_persists_when_not_overridden(self):
        p=fixture('brightyellow');p.pop('title_duration');e=next(e for e in layout(painter(p)) if e['role']=='title');self.assertEqual(e['end'],4)
    def test_raster_bounds_over_animation_phases(self):
        for k in KINDS:
            a=painter(fixture(k));src=Image.new('RGB',(720,960))
            for t in (.101,.14,.22,.5,3.74,3.79):
                b=a.paint(src,a.p['clips'][0],t).getbbox()
                if b:self.assertTrue(b[0]>=12 and b[1]>=12 and b[2]<=708 and b[3]<=948,(k,t,b))

if __name__=='__main__':unittest.main()
