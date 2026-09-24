import copy,hashlib,sys,tempfile,unittest
from pathlib import Path
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_template_scenes import plan,painter,variant_for_kind
from template_scenes import layout,audit_layout
from template_scenes_b6b import KINDS,MODES,title,line,label,panel,arc_line
from template_contracts import validate
from template_catalog import get

def fixture(k):
 p=plan(k);p['template_delivery']='preview';e=p['scene_captions'][0]['phrases'][0];e['id']='p0';e['runs']=[dict(text='方法',role='body'),dict(text='清楚',role='keyword')];return p

def tag(symbol=None):
 e=dict(phrase_id='p0',text='清楚',start=.3,end=3.5,side='right',reason='quoted test')
 if symbol:e.update(symbol=symbol,symbol_reason='semantic test reason')
 return e

class B6bTests(unittest.TestCase):
 def test_contracts(self):
  for k in KINDS:validate(get(variant_for_kind(k))['_contract'],verify_assets=True)
 def test_eight_aspects(self):
  for k in KINDS:
   for h in (960,1280):
    p=fixture(k);p['height']=h;self.assertTrue(audit_layout(painter(p))['passed'])
 def test_distinct_titles(self):
  ims=[title(painter(fixture(k))) for k in KINDS];self.assertEqual(len({hashlib.sha256(i.tobytes()).hexdigest() for i in ims}),4)
 def test_modes_distinct(self):
  for k in KINDS:
   hs=[]
   for mode in MODES[k]:
    p=fixture(k);p['scene_captions'][0]['phrases'][0]['mode']=mode;a=painter(p);self.assertTrue(audit_layout(a)['passed']);im=next(e['image'] for e in layout(a) if e['role']=='caption');hs.append(hashlib.sha256(im.tobytes()).hexdigest())
   self.assertEqual(len(hs),len(set(hs)))
 def test_unknown_modes(self):
  for k in KINDS:
   p=fixture(k);p['scene_captions'][0]['phrases'][0]['mode']='sparkle'
   with self.assertRaises(ValueError):painter(p)
 def test_ids_required_unique(self):
  p=fixture('magenta');p['scene_captions'][0]['phrases'][0].pop('id')
  with self.assertRaises(ValueError):painter(p)
  p=fixture('magenta');q=copy.deepcopy(p['scene_captions'][0]['phrases'][0]);p['scene_captions'][0]['phrases'].append(q)
  with self.assertRaises(ValueError):painter(p)
 def test_dual_phrases(self):
  for k in KINDS:
   p=fixture(k);a=p['scene_captions'][0]['phrases'][0];a.update(text='方法',runs=[dict(text='方法')]);q=copy.deepcopy(a);q.update(id='p1',text='清楚',runs=[dict(text='清楚',role='keyword')],start=1.2);p['scene_captions'][0]['phrases'].append(q);x=painter(p);self.assertTrue(audit_layout(x)['passed']);self.assertEqual(len([e for e in layout(x) if e['role']=='caption']),2)
 def test_no_color_reveal_or_fill_override(self):
  for extra in ({'color':'red'},{'pointer':'x'},{'reveal_times':[.2]}):
   p=fixture('magenta');p['scene_captions'][0]['phrases'][0].update(extra)
   with self.assertRaises(ValueError):painter(p)
  p=fixture('redfestive');p['scene_captions'][0]['phrases'][0]['runs'][0]['fill']='#f00'
  with self.assertRaises(ValueError):painter(p)
 def test_tags_quote_and_clock(self):
  p=fixture('magenta');p['scene_tags']=[dict(tag('heart'),text='促销')]
  with self.assertRaises(ValueError):painter(p)
  p=fixture('magenta');p['scene_tags']=[dict(tag('heart'),start=0)]
  with self.assertRaises(ValueError):painter(p)
 def test_symbol_requires_reason(self):
  p=fixture('magenta');e=tag('heart');e.pop('symbol_reason');p['scene_tags']=[e]
  with self.assertRaises(ValueError):painter(p)
 def test_floraltravel_no_symbol(self):
  p=fixture('floraltravel');p['scene_tags']=[tag('star')]
  with self.assertRaises(ValueError):painter(p)
 def test_symbols_supported(self):
  for k,symbol in (('magenta','heart'),('lightbulb','star'),('lightbulb','exclaim'),('redfestive','burst'),('redfestive','arrow')):
   p=fixture(k);p['scene_tags']=[tag(symbol)];self.assertTrue(audit_layout(painter(p))['passed'])
 def test_explicit_tag_anchor_pair(self):
  p=fixture('lightbulb');e=tag('star');e['x']=.1;p['scene_tags']=[e]
  with self.assertRaises(ValueError):painter(p)
  e['y']=.5;self.assertTrue(audit_layout(painter(p))['passed'])
 def test_no_external_sticker_asset(self):
  p=fixture('redfestive');e=tag('burst');e['path']='sticker.png';p['scene_tags']=[e]
  with self.assertRaises(ValueError):painter(p)
 def test_no_unsupported_layers(self):
  for key in ('scene_media','scene_accents','scene_identity','scene_callouts'):
   p=fixture('magenta');p[key]=[dict(text='x')]
   with self.assertRaises(ValueError):painter(p)
 def test_protected_region_blocks_tag(self):
  p=fixture('redfestive');p['scene_tags']=[tag('arrow')];p['protected_regions']=[dict(box=[0,0,1,1])]
  with self.assertRaisesRegex(ValueError,'protected'):audit_layout(painter(p))
 def test_long_text_rejected(self):
  for k in KINDS:
   a=painter(fixture(k))
   with self.assertRaises(ValueError):line(a,[dict(text='工作流程'*35)],50)
 def test_arc_shrinks_then_rejects_extreme(self):
  a=painter(fixture('redfestive'));im=arc_line(a,[dict(text='检查工作流程',role='body')],50,620);self.assertLessEqual(im.width,620)
  with self.assertRaises(ValueError):arc_line(a,[dict(text='检查流程'*30,role='body')],50,620)
 def test_panel_alpha_and_stability(self):
  src=Image.new('RGBA',(120,60))
  for k in KINDS:
   a=painter(fixture(k));x=panel(src,a,k);y=panel(src,a,k);self.assertEqual(x.tobytes(),y.tobytes());self.assertIsNotNone(x.getchannel('A').getbbox())
 def test_labels_distinct(self):
  hs=[]
  for k,s in (('floraltravel',None),('magenta','heart'),('lightbulb','star'),('redfestive','burst')):
   a=painter(fixture(k));hs.append(hashlib.sha256(label(a,tag(s)).tobytes()).hexdigest())
  self.assertEqual(len(hs),len(set(hs)))
 def test_keyword_changes_pixels(self):
  for k in KINDS:
   a=painter(fixture(k));x=line(a,[dict(text='方法',role='body')],40);y=line(a,[dict(text='方法',role='keyword')],40);self.assertNotEqual(hashlib.sha256(x.tobytes()).hexdigest(),hashlib.sha256(y.tobytes()).hexdigest())
 def test_digits_english_punctuation(self):
  for k in KINDS:
   p=fixture(k);t='AI效率3.5%？';p['clips'][0]['words']=[dict(text=t,start=.1,end=2)];p['scene_captions'][0]['phrases'][0].update(text=t,runs=[dict(text=t)]);self.assertTrue(audit_layout(painter(p))['passed'])
 def test_transcript_integrity(self):
  p=fixture('floraltravel');p['scene_captions'][0]['phrases'][0]['runs']=[dict(text='错误内容')]
  with self.assertRaisesRegex(ValueError,'transcript'):painter(p)
 def test_font_preflight(self):
  for k in KINDS:
   a=painter(fixture(k))
   with tempfile.TemporaryDirectory() as d:self.assertTrue(a.font_preflight(Path(d))['passed'])
 def test_canvas_effects_not_declared(self):
  for k in KINDS:
   p=fixture(k);p['scene_canvas']=[dict(kind='vignette',start=0,end=4,strength=.2,reason='test')]
   with self.assertRaises(ValueError):painter(p)

if __name__=='__main__':unittest.main()
