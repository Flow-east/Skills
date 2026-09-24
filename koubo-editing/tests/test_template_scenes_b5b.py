import copy,hashlib,sys,unittest,tempfile
from pathlib import Path
from PIL import Image,ImageChops
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_template_scenes import plan,painter
from template_scenes import layout,audit_layout,video_layer
from template_scenes_b5b import KINDS,MODES,title,line,label
from template_contracts import validate
from template_catalog import get
from font_guard import inspect_font

def fixture(k):
    p=plan(k);p['template_delivery']='preview';e=p['scene_captions'][0]['phrases'][0];e['id']='p0';e['runs']=[dict(text='方法',role='body'),dict(text='清楚',role='keyword')];return p

def circle():return dict(kind='circle',start=0,end=4,center=[.5,.4],radius=.25,feather=.012,background='#000000',reason='synthetic geometry test',composition_review='No people; chart remains complete in circle')

class B5bTests(unittest.TestCase):
    def test_four_contracts(self):
        for k in KINDS:validate(get(f'ref_{k}_v1')['_contract'],verify_assets=True)
    def test_eight_aspects(self):
        for k in KINDS:
            for h in (960,1280):
                p=fixture(k);p['height']=h;self.assertTrue(audit_layout(painter(p))['passed'])
    def test_titles_distinct_geometry(self):
        ims=[title(painter(fixture(k))) for k in KINDS];self.assertEqual(len({i.size for i in ims}),4);self.assertEqual(len({hashlib.sha256(i.tobytes()).hexdigest() for i in ims}),4)
    def test_modes_distinct(self):
        for k in KINDS:
            hashes=[]
            for mode in MODES[k]:
                p=fixture(k);p['scene_captions'][0]['phrases'][0]['mode']=mode;a=painter(p);self.assertTrue(audit_layout(a)['passed']);im=next(e['image'] for e in layout(a) if e['role']=='caption');hashes.append(hashlib.sha256(im.tobytes()).hexdigest())
            self.assertEqual(len(hashes),len(set(hashes)))
    def test_unknown_mode_rejected(self):
        for k in KINDS:
            p=fixture(k);p['scene_captions'][0]['phrases'][0]['mode']='rainbow'
            with self.assertRaises(ValueError):painter(p)
    def test_unique_ids(self):
        p=fixture('ginger');p['scene_captions'][0]['phrases'][0].pop('id')
        with self.assertRaises(ValueError):painter(p)
    def test_no_unsupported_color(self):
        p=fixture('verdant');p['scene_captions'][0]['phrases'][0]['runs'][0]['fill']='#000'
        with self.assertRaises(ValueError):painter(p)
    def test_no_unsupported_underline(self):
        p=fixture('ginger');p['scene_captions'][0]['phrases'][0]['underline']='方法'
        with self.assertRaises(ValueError):painter(p)
    def test_brown_single_phrase_only(self):
        p=plan('deepbrown',True);p['template_delivery']='preview'
        with self.assertRaises(ValueError):painter(p)
    def test_retained_first_no_reentry(self):
        for k in ('ginger','blackyellow','verdant'):
            p=plan(k,True);p['template_delivery']='preview'
            for i,e in enumerate(p['scene_captions'][0]['phrases']):e['id']=str(i)
            a=painter(p);self.assertTrue(audit_layout(a)['passed']);e=next(e for e in layout(a) if e['role']=='caption');box=tuple(map(round,e['box']));im=Image.new('RGB',(720,960),'#253039');self.assertEqual(a.paint(im,a.p['clips'][0],.8).crop(box).tobytes(),a.paint(im,a.p['clips'][0],1.6).crop(box).tobytes())
    def test_third_phrase_rejected(self):
        p=fixture('ginger');p['scene_captions'][0]['phrases']*=3
        with self.assertRaises(ValueError):painter(p)
    def test_blackyellow_black_normal_plate(self):
        a=painter(fixture('blackyellow'));im=next(e['image'] for e in layout(a) if e['role']=='caption');self.assertEqual(im.getpixel((im.width//2,0)),(16,16,16,255))
    def test_blackyellow_display_alpha_glow(self):
        a=painter(fixture('blackyellow'));im=line(a,[dict(text='清楚')],51,mode='display');self.assertEqual(im.getchannel('A').getextrema(),(0,255));self.assertGreater(len(set(im.getchannel('A').getdata())),10)
    def test_brown_texture_stable(self):
        a=painter(fixture('deepbrown'));self.assertEqual(title(a).tobytes(),title(a).tobytes());im=title(a);self.assertGreater(len(set(im.getdata())),20)
    def test_ginger_title_glow_bounded(self):
        a=painter(fixture('ginger'));im=title(a);self.assertLess(im.width,720*.90);self.assertLess(im.height,200);self.assertTrue(audit_layout(a)['passed'])
    def test_long_phrase_fails(self):
        for k in KINDS:
            with self.assertRaises(ValueError):line(painter(fixture(k)),[dict(text='长句子'*30)],50)
    def test_retained_label_can_outlive_quote(self):
        for k in ('blackyellow','verdant'):
            p=fixture(k);p['scene_callouts']=[dict(phrase_id='p0',text='清楚',start=.3,end=3.95,slot=0,side='right',reason='retain')];a=painter(p);self.assertTrue(audit_layout(a)['passed']);self.assertEqual(next(e for e in layout(a) if e['role']=='callout')['end'],3.95)
    def test_label_not_in_quote_rejected(self):
        p=fixture('blackyellow');p['scene_callouts']=[dict(phrase_id='p0',text='促销',start=.3,end=3.95,slot=0,reason='test')]
        with self.assertRaises(ValueError):painter(p)
    def test_label_slot_collision(self):
        p=fixture('verdant');e=dict(phrase_id='p0',text='清楚',start=.3,end=3.95,slot=0,reason='test');p['scene_callouts']=[e,copy.deepcopy(e)]
        with self.assertRaises(ValueError):painter(p)
    def test_label_anchor_pair(self):
        p=fixture('blackyellow');p['scene_callouts']=[dict(phrase_id='p0',text='清楚',start=.3,end=3.95,slot=0,x=.1,reason='test')]
        with self.assertRaises(ValueError):painter(p)
    def test_label_wrong_template(self):
        p=fixture('ginger');p['scene_callouts']=[dict(text='清楚')]
        with self.assertRaises(ValueError):painter(p)
    def test_tag_quote_and_icon(self):
        for extra in ({'text':'促销'},{'icon':'heart'},{'start':0}):
            p=fixture('deepbrown');e=dict(phrase_id='p0',text='清楚',start=.3,end=3.5,reason='quote');e.update(extra);p['scene_tags']=[e]
            with self.assertRaises(ValueError):painter(p)
    def test_protected_region_blocks_label(self):
        p=fixture('blackyellow');p['scene_callouts']=[dict(phrase_id='p0',text='清楚',start=.3,end=3.95,slot=0,x=.4,y=.4,reason='test')];p['protected_regions']=[dict(box=[.3,.3,.7,.6])]
        with self.assertRaisesRegex(ValueError,'protected'):audit_layout(painter(p))
    def test_circle_requires_composition_review(self):
        p=fixture('verdant');e=circle();e.pop('composition_review');p['scene_canvas']=[e]
        with self.assertRaises(ValueError):painter(p)
    def test_circle_soft_edge_center_and_corners(self):
        p=fixture('verdant');p['scene_canvas']=[circle()];a=painter(p);im=video_layer(a,Image.new('RGB',(720,960),'white'),1);self.assertEqual(im.getpixel((360,384))[:3],(255,255,255));self.assertEqual(im.getpixel((0,0))[:3],(0,0,0));self.assertTrue(0<im.getpixel((540,384))[0]<255)
    def test_circle_does_not_activate_outside_interval(self):
        p=fixture('verdant');e=circle();e.update(start=1,end=2);p['scene_canvas']=[e];a=painter(p);src=Image.new('RGB',(720,960),'white');self.assertEqual(video_layer(a,src,.5).getpixel((0,0))[:3],(255,255,255));self.assertEqual(video_layer(a,src,2).getpixel((0,0))[:3],(255,255,255))
    def test_bad_feather_rejected(self):
        for v in (-1,0,.05,float('nan'),True):
            p=fixture('verdant');e=circle();e['feather']=v;p['scene_canvas']=[e]
            with self.assertRaises(ValueError):painter(p)
    def test_old_circle_feather_rejected(self):
        p=plan('pink');p['scene_canvas']=[circle()]
        with self.assertRaises(ValueError):painter(p)
    def test_circle_cannot_be_silently_used_elsewhere(self):
        p=fixture('blackyellow');p['scene_canvas']=[circle()]
        with self.assertRaises(ValueError):painter(p)
    def test_traditional_text_no_conversion(self):
        text='檢查員工效率與工作流程'
        p=fixture('blackyellow');p['clips'][0]['words']=[dict(text=text,start=.1,end=2)];p['scene_captions'][0]['phrases'][0].update(text=text,runs=[dict(text=text)]);p['scene_title_lines']=['檢查工作流程'];p['title']='檢查工作流程';a=painter(p)
        with tempfile.TemporaryDirectory() as d:self.assertTrue(a.font_preflight(Path(d))['passed'])
        self.assertEqual(a.p['scene_captions'][0]['phrases'][0]['runs'][0]['text'],text);self.assertTrue(audit_layout(a)['passed'])
    def test_traditional_sample_each_role_covered(self):
        a=painter(fixture('blackyellow'))
        for role in ('title','body','keyword','sticker'):self.assertTrue(inspect_font(a.font_path(role),'寶寶推薦耐高溫抗摔檢查複製資料',a.font_index(role),a.font_weight(role))['passed'])
    def test_digits_english_punctuation(self):
        for k in KINDS:
            p=fixture(k);t='AI效率提升3.5%？';p['clips'][0]['words']=[dict(text=t,start=.1,end=2)];p['scene_captions'][0]['phrases'][0].update(text=t,runs=[dict(text=t)]);self.assertTrue(audit_layout(painter(p))['passed'])
    def test_white_title_has_dark_edge_on_bright_background(self):
        a=painter(fixture('blackyellow'));im=title(a);pixels=[v for v in im.getdata() if v[3]>200];self.assertTrue(any(max(v[:3])<90 for v in pixels));self.assertTrue(any(min(v[:3])>220 for v in pixels))
    def test_circle_geometry_does_not_modify_caption_layout(self):
        p=fixture('verdant');plain=layout(painter(p));p['scene_canvas']=[circle()];window=layout(painter(p));self.assertEqual([e['box'] for e in plain],[e['box'] for e in window]);self.assertEqual([e['image'].tobytes() for e in plain],[e['image'].tobytes() for e in window])
    def test_wrong_transcript_rejected(self):
        p=fixture('ginger');p['scene_captions'][0]['phrases'][0]['runs']=[dict(text='方法错误')]
        with self.assertRaisesRegex(ValueError,'transcript'):painter(p)
    def test_media_not_silently_ignored(self):
        p=fixture('verdant');p['scene_media']=[dict(path='missing')]
        with self.assertRaises(ValueError):painter(p)

if __name__=='__main__':unittest.main()
