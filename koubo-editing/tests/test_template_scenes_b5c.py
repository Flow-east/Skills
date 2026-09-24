import copy,hashlib,sys,unittest,tempfile
from pathlib import Path
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_template_scenes import plan,painter,variant_for_kind
from template_scenes import layout,audit_layout,video_layer
from template_scenes_b5c import KINDS,MODES,title,line,panel,label
from template_contracts import validate
from template_catalog import get

def fixture(k):
    p=plan(k);p['template_delivery']='preview';e=p['scene_captions'][0]['phrases'][0];e['id']='p0';e['runs']=[dict(text='方法',role='body'),dict(text='清楚',role='keyword')];return p

def circle():return dict(kind='circle',start=0,end=4,center=[.5,.4],radius=.25,feather=.012,background='#000000',reason='synthetic chart',composition_review='No person; chart fully in window')

class B5cTests(unittest.TestCase):
    def test_contracts(self):
        for k in KINDS:validate(get(variant_for_kind(k))['_contract'],verify_assets=True)
    def test_eight_aspects(self):
        for k in KINDS:
            for h in (960,1280):
                p=fixture(k);p['height']=h;self.assertTrue(audit_layout(painter(p))['passed'])
    def test_distinct_titles(self):
        ims=[title(painter(fixture(k))) for k in KINDS];self.assertEqual(len({hashlib.sha256(i.tobytes()).hexdigest() for i in ims}),4)
    def test_mode_geometry(self):
        for k in KINDS:
            hashes=[]
            for m in MODES[k]:
                p=fixture(k);p['scene_captions'][0]['phrases'][0]['mode']=m;a=painter(p);self.assertTrue(audit_layout(a)['passed']);im=next(e['image'] for e in layout(a) if e['role']=='caption');hashes.append(hashlib.sha256(im.tobytes()).hexdigest())
            self.assertEqual(len(set(hashes)),len(hashes))
    def test_unknown_mode(self):
        for k in KINDS:
            p=fixture(k);p['scene_captions'][0]['phrases'][0]['mode']='impact'
            with self.assertRaises(ValueError):painter(p)
    def test_id_required(self):
        p=fixture('ins');p['scene_captions'][0]['phrases'][0].pop('id')
        with self.assertRaises(ValueError):painter(p)
    def test_duplicate_ids(self):
        p=fixture('tornedge');g=p['scene_captions'][0];g['phrases'].append(copy.deepcopy(g['phrases'][0]))
        with self.assertRaises(ValueError):painter(p)
    def test_single_phrase_limit(self):
        for k in ('ins','nostalgia'):
            p=fixture(k);g=p['scene_captions'][0];q=copy.deepcopy(g['phrases'][0]);q['id']='p1';g['phrases'].append(q)
            with self.assertRaises(ValueError):painter(p)
    def test_dual_phrase_clocks(self):
        for k in ('transyellow','tornedge'):
            p=fixture(k);g=p['scene_captions'][0];a=g['phrases'][0];a.update(start=.1,end=3.8,text='方法',runs=[dict(text='方法')]);q=copy.deepcopy(a);q.update(id='p1',start=1.2,end=3.8,text='清楚',runs=[dict(text='清楚',role='keyword')]);g['phrases'].append(q);a=painter(p);self.assertTrue(audit_layout(a)['passed']);es=[e for e in layout(a) if e['role']=='caption'];self.assertEqual([e['start'] for e in es],[.1,1.2]);self.assertNotEqual(es[0]['x'],es[1]['x'])
    def test_no_color_override(self):
        p=fixture('transyellow');p['scene_captions'][0]['phrases'][0]['runs'][0]['fill']='#FF0000'
        with self.assertRaises(ValueError):painter(p)
    def test_no_unimplemented_reveal(self):
        p=fixture('nostalgia');p['scene_captions'][0]['phrases'][0]['reveal_times']=[0,1]
        with self.assertRaises(ValueError):painter(p)
    def test_no_unsupported_layers(self):
        for key in ('scene_callouts','scene_identity','scene_media','scene_accents'):
            p=fixture('ins');p[key]=[dict(text='test')]
            with self.assertRaises(ValueError):painter(p)
    def test_tag_quote(self):
        p=fixture('ins');p['scene_tags']=[dict(phrase_id='p0',text='促销',start=.3,end=3.5,reason='test')]
        with self.assertRaises(ValueError):painter(p)
    def test_tag_active_clock(self):
        p=fixture('ins');p['scene_tags']=[dict(phrase_id='p0',text='清楚',start=0,end=3.5,reason='test')]
        with self.assertRaises(ValueError):painter(p)
    def test_tag_style_restriction(self):
        for extra in ({'icon':'heart'},{'orientation':'vertical'},{'side':'center'}):
            p=fixture('ins');e=dict(phrase_id='p0',text='清楚',start=.3,end=3.5,reason='test');e.update(extra);p['scene_tags']=[e]
            with self.assertRaises(ValueError):painter(p)
    def test_valid_tags(self):
        for k in KINDS:
            p=fixture(k);p['scene_tags']=[dict(phrase_id='p0',text='清楚',start=.3,end=3.5,reason='test')];self.assertTrue(audit_layout(painter(p))['passed'])
    def test_protection(self):
        p=fixture('ins');p['protected_regions']=[dict(box=[.01,.01,.99,.99])]
        with self.assertRaisesRegex(ValueError,'protected'):audit_layout(painter(p))
    def test_long_text(self):
        for k in KINDS:
            a=painter(fixture(k))
            with self.assertRaises(ValueError):line(a,[dict(text='工作流程'*40)],48)
    def test_title_long(self):
        p=fixture('ins');p['scene_title_lines']=['检查工作流程'*20]
        with self.assertRaises(ValueError):layout(painter(p))
    def test_digits_english(self):
        for k in KINDS:
            p=fixture(k);t='AI效率3.5%';p['clips'][0]['words']=[dict(text=t,start=.1,end=2)];p['scene_captions'][0]['phrases'][0].update(text=t,runs=[dict(text=t)]);a=painter(p);self.assertTrue(audit_layout(a)['passed'])
    def test_transcript_integrity(self):
        p=fixture('ins');p['scene_captions'][0]['phrases'][0]['runs']=[dict(text='内容错误')]
        with self.assertRaisesRegex(ValueError,'transcript'):painter(p)
    def test_font_preflight(self):
        for k in KINDS:
            a=painter(fixture(k))
            with tempfile.TemporaryDirectory() as d:self.assertTrue(a.font_preflight(Path(d))['passed'])
    def test_semtransparent_cards(self):
        for k in ('nostalgia','transyellow','tornedge'):
            im=panel(Image.new('RGBA',(120,60)),1,k);self.assertTrue(0<im.getpixel((60,30))[3]<255)
    def test_stable_paper_edge(self):
        a=Image.new('RGBA',(200,70));x=panel(a,1,'tornedge');y=panel(a,1,'tornedge');self.assertEqual(x.tobytes(),y.tobytes());self.assertGreater(len(set(x.getchannel('A').crop((0,0,200,3)).getdata())),1)
    def test_labels_distinct(self):
        ims=[label(painter(fixture(k)),'检查',28,250) for k in KINDS];self.assertEqual(len({hashlib.sha256(i.tobytes()).hexdigest() for i in ims}),4)
    def test_title_dark_edge(self):
        for k in KINDS:
            im=title(painter(fixture(k)));self.assertTrue(any(max(v[:3])<100 and v[3]>150 for v in im.getdata()))
    def test_circle_review_required(self):
        for k in ('transyellow','tornedge'):
            p=fixture(k);e=circle();e.pop('composition_review');p['scene_canvas']=[e]
            with self.assertRaises(ValueError):painter(p)
    def test_circle_not_for_all(self):
        for k in ('ins','nostalgia'):
            p=fixture(k);p['scene_canvas']=[circle()]
            with self.assertRaises(ValueError):painter(p)
    def test_circle_edge(self):
        for k in ('transyellow','tornedge'):
            p=fixture(k);p['scene_canvas']=[circle()];a=painter(p);im=video_layer(a,Image.new('RGB',(720,960),'white'),1);self.assertEqual(im.getpixel((360,384))[:3],(255,255,255));self.assertEqual(im.getpixel((0,0))[:3],(0,0,0));self.assertTrue(0<im.getpixel((540,384))[0]<255)
    def test_circle_clock(self):
        p=fixture('transyellow');e=circle();e.update(start=1,end=2);p['scene_canvas']=[e];a=painter(p)
        for t in (.5,2):self.assertEqual(video_layer(a,Image.new('RGB',(720,960),'white'),t).getpixel((0,0))[:3],(255,255,255))
    def test_bad_feather(self):
        for v in (0,-1,.05,float('nan'),True):
            p=fixture('tornedge');e=circle();e['feather']=v;p['scene_canvas']=[e]
            with self.assertRaises(ValueError):painter(p)
    def test_circle_no_caption_reflow(self):
        p=fixture('tornedge');a=layout(painter(p));p['scene_canvas']=[circle()];b=layout(painter(p));self.assertEqual([e['box'] for e in a],[e['box'] for e in b])

if __name__=='__main__':unittest.main()
