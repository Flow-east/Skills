import copy,json,sys,unittest
from pathlib import Path
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from render_template import Painter
from timeline import compile_plan
from keyword_stickers import badge,placement,paint
from font_guard import display_text,audit,inspect_font
from test_pipeline import fixture

class StickerTests(unittest.TestCase):
 def plan(self):
  p=compile_plan(fixture());p['template_variant']='orange_hook'
  p['keyword_stickers']=[dict(start=.2,end=.9,text='先别急',reason='reviewed warning',position=[.73,.095])]
  return p
 def test_independent_layer_is_transparent_outside_event(self):
  p=self.plan();a=Painter(p);im=Image.new('RGBA',(720,1280));paint(a,im,1.5)
  self.assertIsNone(im.getbbox());paint(a,im,.6);self.assertIsNotNone(im.getbbox())
 def test_badge_stays_inside_frame_and_has_transparent_border(self):
  p=self.plan();a=Painter(p);ev=p['keyword_stickers'][0];im=badge(a,ev);x,y=placement(a,ev,im)
  self.assertGreaterEqual(x,0);self.assertGreaterEqual(y,0);self.assertLessEqual(x+im.width,720);self.assertLessEqual(y+im.height,1280)
  self.assertEqual(im.getchannel('A').getextrema()[0],0)
 def test_sticker_only_text_is_in_font_guard(self):
  p=self.plan();p['keyword_stickers'][0]['text']='独立贴纸字';self.assertIn('独立贴纸字',display_text(p))
 def test_missing_sticker_glyph_blocks(self):
  p=self.plan();p['keyword_stickers'][0]['text']='坏\ufffd字';self.assertFalse(audit(Painter(p))['passed'])
 def test_no_auto_sticker_for_every_emphasis_word(self):
  p=self.plan();p['keyword_stickers']=[];p['clips'][0]['emphasis_words']=['方法'];a=Painter(p);im=Image.new('RGBA',(720,1280));paint(a,im,.6);self.assertIsNone(im.getbbox())
 def test_overlapping_and_out_of_range_events_rejected(self):
  p=self.plan();p['keyword_stickers'].append(dict(p['keyword_stickers'][0]))
  with self.assertRaises(ValueError):Painter(p)
  p=self.plan();p['keyword_stickers'][0]['end']=100
  with self.assertRaises(ValueError):Painter(p)
 def test_four_styles_are_distinct_and_cover_simplified_chinese(self):
  images=[];paths=set()
  for name in ['orange_hook','rounded_pop','ink_note','cream_serif']:
   p=self.plan();p['template_variant']=name;a=Painter(p);self.assertTrue(audit(a)['passed']);paths.add(a.font_path('keyword'));images.append(badge(a,p['keyword_stickers'][0]).tobytes())
  self.assertEqual(len(paths),4);self.assertEqual(len(set(images)),4)
 def test_collection_face_used_by_preflight_matches_renderer(self):
  p=self.plan();p['template_variant']='ink_note';a=Painter(p);a.variant['font_index']=6
  report=audit(a);self.assertEqual(report['face_indices']['body'],6);self.assertEqual(a.font(48).getname(),('Songti SC','Regular'))
