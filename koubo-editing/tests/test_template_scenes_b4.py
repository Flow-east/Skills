import copy,hashlib,json,sys,tempfile,unittest
from pathlib import Path
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_template_scenes import plan,painter,variant_for_kind
from template_scenes import audit_layout,layout,texts
from template_scenes_b4 import KINDS,line,title,hand,bulb,tech_rail,pointer_sprite,identity_sprite
from template_contracts import validate
from template_catalog import get
from font_guard import display_text,audit


def fixture(k):
    p=plan(k);p['template_delivery']='preview'
    e=p['scene_captions'][0]['phrases'][0];e['id']='p0';e['runs']=[dict(text='方法',role='body'),dict(text='清楚',role='keyword')]
    if k=='green':
        e['mode']='compact';p['scene_translations']=[dict(phrase_id='p0',source_text='方法清楚',text='Make the method clear.',language='en',start=.15,end=3.7,review_status='reviewed',reviewer='test fixture')]
    return p

class B4Tests(unittest.TestCase):
    def test_four_contract_assets(self):
        for k in KINDS:validate(get(variant_for_kind(k))['_contract'],verify_assets=True)
    def test_four_distinct_typography_geometries(self):
        ims=[title(painter(fixture(k))) for k in KINDS]
        self.assertEqual(len({hashlib.sha256(i.tobytes()).hexdigest() for i in ims}),4);self.assertEqual(len({i.size for i in ims}),4)
    def test_eight_aspect_layouts(self):
        for k in KINDS:
            for h in (960,1280):
                p=fixture(k);p['height']=h;self.assertTrue(audit_layout(painter(p))['passed'])
    def test_gradient_color_varies_in_solid_glyph(self):
        a=painter(fixture('tech'));im=line(a,[dict(text='科技',role='title')],60,'title')
        colors={px[:3] for px in im.getdata() if px[3]==255};self.assertGreater(len(colors),40)
    def test_pointer_tracks_target_not_fixed_x(self):
        a=painter(fixture('shine'));im=line(a,[dict(text='方法',role='body'),dict(text='清楚',role='keyword')],42)
        left=pointer_sprite(a,dict(pointer='方法'),im);right=pointer_sprite(a,dict(pointer='清楚'),im)
        lb=left.getchannel('A').crop((0,im.height,left.width,left.height)).getbbox();rb=right.getchannel('A').crop((0,im.height,right.width,right.height)).getbbox();self.assertLess(lb[0],rb[0])
    def test_pointer_wrong_or_ambiguous_word_rejected(self):
        for value in ('不存在','方清'):
            p=fixture('shine');p['scene_captions'][0]['phrases'][0]['pointer']=value
            with self.assertRaises(ValueError):painter(p)
        p=fixture('shine');p['clips'][0]['words']=[dict(text='方法方法',start=.1,end=2)];e=p['scene_captions'][0]['phrases'][0];e['text']='方法方法';e['runs']=[dict(text='方法方法')];e['pointer']='方法'
        with self.assertRaises(ValueError):painter(p)
    def test_pointer_safe_on_paper(self):
        p=fixture('science');e=p['scene_captions'][0]['phrases'][0];e.update(mode='paper',pointer='清楚');self.assertTrue(audit_layout(painter(p))['passed'])
    def test_original_icons_have_real_alpha(self):
        for f in (hand,bulb):
            im=f(1);self.assertEqual(im.getchannel('A').getextrema(),(0,255));self.assertIsNotNone(im.getbbox())
    def test_tech_rail_survives_caption_gap(self):
        p=fixture('tech');a=painter(p);es=layout(a);rail=next(e for e in es if e['role']=='caption_surface');self.assertEqual((rail['start'],rail['end']),(0,4));self.assertEqual(rail['animation'],'steady')
        src=Image.new('RGB',(720,960));box=tuple(map(round,rail['box']));self.assertEqual(a.paint(src,a.p['clips'][0],.02).crop(box).tobytes(),a.paint(src,a.p['clips'][0],3.95).crop(box).tobytes())
    def test_tech_containment_does_not_disable_collisions(self):
        p=fixture('tech');a=painter(p);self.assertTrue(audit_layout(a)['passed']);es=layout(a);cap=next(e for e in es if e['role']=='caption');cap['box']=(0,0,720,960)
        with self.assertRaisesRegex(ValueError,'escapes'):audit_layout(a)
    def test_rail_protected_region_still_blocks(self):
        p=fixture('tech');p['protected_regions']=[dict(start=0,end=4,box=[.1,.85,.9,.97])]
        with self.assertRaisesRegex(ValueError,'protected'):audit_layout(painter(p))
    def test_green_display_needs_no_translation(self):
        p=fixture('green');p['scene_captions'][0]['phrases'][0]['mode']='display';p['scene_translations']=[];self.assertTrue(audit_layout(painter(p))['passed'])
    def test_green_translation_cannot_silently_hide_in_display(self):
        p=fixture('green');p['scene_captions'][0]['phrases'][0]['mode']='display'
        with self.assertRaises(ValueError):painter(p)
    def test_green_compact_translation_required(self):
        p=fixture('green');p['scene_translations']=[]
        with self.assertRaises(ValueError):painter(p)
    def test_retained_callout_has_independent_clock(self):
        p=fixture('green');p['scene_callouts']=[dict(phrase_id='p0',text='方法',start=.4,end=3.95,slot=0,side='right',reason='retain concept')];a=painter(p);e=next(e for e in layout(a) if e['role']=='callout');self.assertEqual(e['end'],3.95);self.assertTrue(audit_layout(a)['passed'])
    def test_retained_callout_cannot_invent_or_enter_after_source(self):
        for text,start in [('不存在',.5),('方法',3.9)]:
            p=fixture('green');p['scene_callouts']=[dict(phrase_id='p0',text=text,start=start,end=3.99,slot=0,side='right',reason='test')]
            with self.assertRaises(ValueError):painter(p)
    def test_callout_same_slot_overlap_rejected(self):
        p=fixture('green');p['scene_callouts']=[dict(phrase_id='p0',text='方法',start=.4,end=3.9,slot=0,reason='test')]*2
        with self.assertRaisesRegex(ValueError,'slot'):painter(p)
    def test_identity_requires_provenance(self):
        for k in ('tech','science'):
            p=fixture(k);p['scene_identity']=[dict(name='示例',detail='测试资料',start=.1,end=.8,x=.05,y=.3)]
            with self.assertRaisesRegex(ValueError,'source'):painter(p)
    def test_identity_all_text_preflighted(self):
        p=fixture('tech');p['scene_identity']=[dict(name='测试',detail='测试资料',start=.1,end=.8,x=.05,y=.3,review_status='reviewed',source='synthetic test data, not a real person',reviewer='unit test',reason='test card')]
        a=painter(p);self.assertTrue(audit_layout(a)['passed']);self.assertIn('测试资料',display_text(p));self.assertTrue(audit(a)['passed'])
        p['scene_identity'][0]['detail']='错误\ufffd';self.assertFalse(audit(painter(p))['passed'])
    def test_identity_protection_blocks(self):
        p=fixture('science');p['scene_identity']=[dict(name='测试',detail='测试资料',start=.1,end=.8,x=.1,y=.3,review_status='reviewed',source='synthetic',reviewer='test',reason='test')];p['protected_regions']=[dict(start=0,end=4,box=[.1,.2,.8,.6])]
        with self.assertRaises(ValueError):audit_layout(painter(p))
    def test_old_templates_reject_new_layers(self):
        for field in ('scene_callouts','scene_identity'):
            p=plan('pink');p[field]=[dict(text='not silently ignored')]
            with self.assertRaises(ValueError):painter(p)
    def test_long_text_stops_not_truncates(self):
        for k in KINDS:
            with self.assertRaisesRegex(ValueError,'too long'):line(painter(fixture(k)),[dict(text='方法'*80)],42)
    def test_bulb_tag_and_vertical_bounds(self):
        for tag in [dict(icon='bulb'),dict(orientation='vertical')]:
            p=fixture('shine');p['scene_tags']=[dict(start=.4,end=1,text='清楚',phrase_id='p0',side='right',reason='test',**tag)];self.assertTrue(audit_layout(painter(p))['passed'])
    def test_full_animation_ink_safe(self):
        for k in KINDS:
            a=painter(fixture(k));src=Image.new('RGB',(720,960))
            for t in (.001,.101,.15,.3,1,3.79,3.99):
                b=a.paint(src,a.p['clips'][0],t).getbbox()
                if b:self.assertTrue(b[0]>=12 and b[1]>=12 and b[2]<=708 and b[3]<=948,(k,t,b))

if __name__=='__main__':unittest.main()
