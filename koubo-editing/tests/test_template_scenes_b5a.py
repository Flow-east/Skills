import copy,hashlib,json,sys,tempfile,unittest
from pathlib import Path
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_template_scenes import plan,painter,variant_for_kind
from template_scenes import layout,audit_layout,texts
from template_scenes_b5a import KINDS,title,line,paper
from template_contracts import validate
from template_catalog import get

def fixture(k):
    p=plan(k);p['template_delivery']='preview';e=p['scene_captions'][0]['phrases'][0];e['id']='p0';e['runs']=[dict(text='方法',role='body'),dict(text='清楚',role='keyword')];return p

def media_entry(path):
    return dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),phrase_id='p0',start=.3,end=3.7,x=.28,y=.30,width=.4,height=.32,fit='contain',review_status='reviewed',privacy_status='reviewed',privacy_review='synthetic chart; no people or private data',source='unit test original',rights='original geometric asset',reviewer='test',reason='illustrate the spoken method')

class B5aTests(unittest.TestCase):
    def test_contracts_and_assets(self):
        for k in KINDS:validate(get(variant_for_kind(k))['_contract'],verify_assets=True)
    def test_eight_aspects(self):
        for k in KINDS:
            for h in (960,1280):
                p=fixture(k);p['height']=h;self.assertTrue(audit_layout(painter(p))['passed'])
    def test_four_distinct_titles(self):
        ims=[title(painter(fixture(k))) for k in KINDS];self.assertEqual(len({hashlib.sha256(i.tobytes()).hexdigest() for i in ims}),4);self.assertEqual(len({i.size for i in ims}),4)
    def test_multiple_modes_distinct(self):
        from template_scenes_b5a import MODES
        for k in KINDS:
            hashes=[]
            for mode in MODES[k]:
                p=fixture(k);p['scene_captions'][0]['phrases'][0]['mode']=mode;es=layout(painter(p));im=next(e['image'] for e in es if e['role']=='caption');hashes.append(hashlib.sha256(im.tobytes()).hexdigest())
            self.assertEqual(len(hashes),len(set(hashes)),k)
    def test_bad_modes_rejected(self):
        for k in KINDS:
            p=fixture(k);p['scene_captions'][0]['phrases'][0]['mode']='official_magic'
            with self.assertRaises(ValueError):painter(p)
    def test_unique_phrase_ids_required(self):
        p=fixture('mint');p['scene_captions'][0]['phrases'][0].pop('id')
        with self.assertRaises(ValueError):painter(p)
    def test_retained_phrase_no_reentry(self):
        for k in KINDS:
            p=plan(k,True);p['template_delivery']='preview'
            for i,e in enumerate(p['scene_captions'][0]['phrases']):e['id']=str(i)
            a=painter(p);es=[e for e in layout(a) if e['role']=='caption'];self.assertEqual(len(es),2);self.assertTrue(audit_layout(a)['passed']);box=tuple(map(round,es[0]['box']));im=Image.new('RGB',(720,960),'#303030');self.assertEqual(a.paint(im,a.p['clips'][0],.8).crop(box).tobytes(),a.paint(im,a.p['clips'][0],1.5).crop(box).tobytes())
    def test_third_phrase_rejected(self):
        p=fixture('orangeline');p['scene_captions'][0]['phrases']*=3
        with self.assertRaises(ValueError):painter(p)
    def test_mint_underline_bound_to_quote(self):
        p=fixture('mint');p['scene_captions'][0]['phrases'][0]['underline']='清楚';self.assertTrue(audit_layout(painter(p))['passed']);p['scene_captions'][0]['phrases'][0]['underline']='虚构'
        with self.assertRaises(ValueError):painter(p)
    def test_underline_wrong_template(self):
        p=fixture('colorful');p['scene_captions'][0]['phrases'][0]['underline']='清楚'
        with self.assertRaises(ValueError):painter(p)
    def test_mint_card_is_green_not_white(self):
        p=fixture('mint');p['scene_captions'][0]['phrases'][0]['mode']='card';im=next(e['image'] for e in layout(painter(p)) if e['role']=='caption');self.assertEqual(im.getpixel((im.width//2,0)),(120,216,157,255))
    def test_torn_paper_deterministic_alpha(self):
        a=painter(fixture('tornred'));im=paper(a,'清楚',49,600);self.assertEqual(im.tobytes(),paper(a,'清楚',49,600).tobytes());self.assertEqual(im.getchannel('A').getextrema(),(0,255));self.assertGreater(len(set(im.getchannel('A').getdata())),2)
    def test_torn_paper_long_string_rejected(self):
        with self.assertRaises(ValueError):paper(painter(fixture('tornred')),'特别长的句子'*9,49,500)
    def test_fitting_keeps_readable_size(self):
        for k in KINDS:
            with self.assertRaises(ValueError):line(painter(fixture(k)),[dict(text='很长的句子'*20)],45)
    def test_explicit_fill_rejected(self):
        p=fixture('mint');p['scene_captions'][0]['phrases'][0]['runs'][0]['fill']='#FF0000'
        with self.assertRaises(ValueError):painter(p)
    def test_feature_retained_after_phrase(self):
        p=fixture('colorful');p['scene_callouts']=[dict(phrase_id='p0',text='清楚',start=.3,end=3.95,slot=0,side='right',reason='retain')];a=painter(p);self.assertTrue(audit_layout(a)['passed']);self.assertEqual(next(e for e in layout(a) if e['role']=='callout')['end'],3.95)
    def test_feature_requires_quote(self):
        p=fixture('colorful');p['scene_callouts']=[dict(phrase_id='p0',text='购买',start=.3,end=3.95,slot=0,reason='retain')]
        with self.assertRaises(ValueError):painter(p)
    def test_feature_slot_collision(self):
        p=fixture('colorful');e=dict(phrase_id='p0',text='清楚',start=.3,end=3.95,slot=0,reason='retain');p['scene_callouts']=[e,copy.deepcopy(e)]
        with self.assertRaises(ValueError):painter(p)
    def test_feature_anchor_pair(self):
        p=fixture('colorful');p['scene_callouts']=[dict(phrase_id='p0',text='清楚',start=.3,end=3.95,slot=0,x=.1,reason='retain')]
        with self.assertRaises(ValueError):painter(p)
    def test_feature_wrong_template(self):
        p=fixture('mint');p['scene_callouts']=[dict(text='清楚')]
        with self.assertRaises(ValueError):painter(p)
    def test_tag_needs_anchor_and_no_arbitrary_icon(self):
        for extra in ({'text':'购买'},{'icon':'cart'}):
            p=fixture('tornred');e=dict(text='清楚',phrase_id='p0',start=.3,end=2,reason='anchor');e.update(extra);p['scene_tags']=[e]
            with self.assertRaises(ValueError):painter(p)
    def test_media_review_and_provenance(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'a.png';Image.new('RGB',(200,100),'orange').save(f);p=fixture('tornred');p['scene_media']=[media_entry(f)];a=painter(p);self.assertTrue(audit_layout(a)['passed']);self.assertEqual(a.scene_media_assets[0]['sha256'],hashlib.sha256(f.read_bytes()).hexdigest());a.font_preflight(Path(d));self.assertEqual(len(json.loads((Path(d)/'font_qa.json').read_text())['scene_media_assets']),1)
    def test_media_review_fields_required(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'a.png';Image.new('RGB',(20,10),'orange').save(f)
            for field in ('rights','privacy_review','privacy_status','review_status','source','reviewer','reason'):
                p=fixture('tornred');e=media_entry(f);e.pop(field);p['scene_media']=[e]
                with self.assertRaises(ValueError):painter(p)
    def test_media_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'a.png';Image.new('RGB',(20,10)).save(f);p=fixture('tornred');e=media_entry(f);e['sha256']='0'*64;p['scene_media']=[e]
            with self.assertRaisesRegex(ValueError,'hash'):painter(p)
    def test_media_keeps_full_image_not_cropped(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'a.png';Image.new('RGB',(200,100),'orange').save(f);p=fixture('tornred');p['scene_media']=[media_entry(f)];im=next(e['image'] for e in layout(painter(p)) if e['role']=='illustration');self.assertEqual(im.getpixel((im.width//2,2))[:3],(247,244,239));self.assertEqual(im.getpixel((im.width//2,im.height//2))[:3],(255,165,0));p['scene_media'][0]['fit']='cover'
            with self.assertRaises(ValueError):painter(p)
    def test_media_cannot_cover_protected_region(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'a.png';Image.new('RGB',(200,100)).save(f);p=fixture('tornred');p['scene_media']=[media_entry(f)];p['protected_regions']=[dict(box=[.3,.3,.6,.6],start=0,end=4)]
            with self.assertRaisesRegex(ValueError,'protected'):audit_layout(painter(p))
    def test_media_bounds_and_clock(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'a.png';Image.new('RGB',(20,10)).save(f)
            for extra in ({'width':1.1},{'start':0},{'end':4},{'x':.9}):
                p=fixture('tornred');e=media_entry(f);e.update(extra);p['scene_media']=[e]
                with self.assertRaises(ValueError):audit_layout(painter(p))
    def test_media_legacy_rejected_not_silently_dropped(self):
        for k in ('mint','pink','browngold'):
            p=fixture(k);p['scene_media']=[dict(path='missing')]
            with self.assertRaises(ValueError):painter(p)
    def test_digits_english_punctuation_preserved(self):
        for k in KINDS:
            p=fixture(k);text='AI效率提升3.5%？';p['clips'][0]['words']=[dict(text=text,start=.1,end=2)];p['scene_captions'][0]['phrases'][0].update(text=text,runs=[dict(text=text)]);self.assertTrue(audit_layout(painter(p))['passed'])
    def test_paper_dash_keeps_full_height_surface(self):
        a=painter(fixture('tornred'));im=paper(a,'查一下',49,600);alpha=im.getchannel('A');cols=[]
        for x in range(im.width):
            bbox=alpha.crop((x,0,x+1,im.height)).getbbox()
            if bbox:cols.append(bbox[3]-bbox[1])
        # Each tile has a full-height white backing even for the flat 一 glyph.
        self.assertGreater(sum(v>im.height*.75 for v in cols)/len(cols),.75)
    def test_media_loaded_snapshot_stable_if_file_changes_after_validation(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'a.png';Image.new('RGB',(200,100),'orange').save(f);p=fixture('tornred');p['scene_media']=[media_entry(f)];a=painter(p);Image.new('RGB',(200,100),'blue').save(f);im=next(e['image'] for e in layout(a) if e['role']=='illustration');self.assertEqual(im.getpixel((im.width//2,im.height//2))[:3],(255,165,0))
            with self.assertRaises(ValueError):painter(p)
    def test_media_collision_not_silently_allowed(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'a.png';Image.new('RGB',(200,100),'orange').save(f);p=fixture('tornred');p['scene_media']=[media_entry(f),media_entry(f)]
            with self.assertRaisesRegex(ValueError,'collide'):audit_layout(painter(p))
    def test_wrong_transcript_rejected(self):
        p=fixture('mint');p['scene_captions'][0]['phrases'][0]['runs']=[dict(text='方法错误')]
        with self.assertRaisesRegex(ValueError,'transcript'):painter(p)
    def test_unsupported_subject_outline_rejected(self):
        p=fixture('tornred');p['scene_canvas']=[dict(kind='subject_outline',start=0,end=4)]
        with self.assertRaises(ValueError):painter(p)

if __name__=='__main__':unittest.main()
