import json,sys,unittest
from pathlib import Path
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from reference_typography import stack_lines,caption_sprite,title_sprite,sticker_sprite
from render_template import Painter
from timeline import compile_plan
from design_system import caption_layout
from test_pipeline import fixture

def painter(name):
 p=fixture();p.update(template_variant=name,height=960,title='员工效率不高，先别急着批评')
 return Painter(compile_plan(p))

class ReferenceTypeTests(unittest.TestCase):
 def test_authored_split_keeps_verb_particle_and_all_text(self):
  runs=[dict(text='先',style='base'),dict(text='不要急',style='keyword'),dict(text='着去',style='base'),dict(text='批评',style='keyword')]
  lines=stack_lines(runs,authored_break=5)
  self.assertEqual([''.join(r['text'] for r in ln) for ln in lines],['先不要急着','去批评'])
 def test_no_keyword_internal_split(self):
  with self.assertRaises(ValueError):stack_lines([dict(text='汇总数据',style='keyword')],authored_break=2)
 def test_stack_preserves_every_character(self):
  runs=[dict(text='员工的',style='base'),dict(text='效率',style='keyword'),dict(text='问题。',style='base')]
  lines=stack_lines(runs)
  self.assertEqual(len(lines),2);self.assertEqual(''.join(r['text'] for ln in lines for r in ln),'员工的效率问题。')
 def test_pink_and_gold_are_naked_type_not_panels(self):
  for n in ('ink_note','cream_serif'):
   a=painter(n);cfg=a.variant['design_system']['caption'];im,_=caption_sprite(a,dict(text='员工效率问题'),cfg)
   alpha=im.getchannel('A');coverage=sum(1 for x in alpha.getdata() if x)/ (im.width*im.height)
   self.assertLess(coverage,.65)
 def test_warning_palette_changes_only_authored_tone(self):
  a=painter('ink_note');cfg=a.variant['design_system']['caption'];e=dict(runs=[dict(text='先不要急',style='keyword')])
  pink=caption_sprite(a,e,cfg)[0];gold=caption_sprite(a,dict(e,tone='warning'),cfg)[0]
  self.assertNotEqual(pink.tobytes(),gold.tobytes());self.assertEqual(pink.size,gold.size)
 def test_explicit_warning_symbol_not_added_to_every_sticker(self):
  a=painter('cream_serif');cfg=a.variant['sticker_style']
  plain=sticker_sprite(a,dict(text='先别急'),cfg);warning=sticker_sprite(a,dict(text='先别急',symbol='warning'),cfg)
  self.assertNotEqual(plain.tobytes(),warning.tobytes())
  with self.assertRaises(ValueError):sticker_sprite(a,dict(text='先别急',symbol='unknown'),cfg)
 def test_gold_uses_chinese_sans_not_old_serif(self):
  a=painter('cream_serif');self.assertIn('STHeiti',a.font_path());self.assertEqual(a.font_index(),0)
 def test_pink_uses_songti_not_rejected_handwriting(self):
  a=painter('ink_note');self.assertIn('Songti',a.font_path());self.assertNotIn('WenKai',a.font_path())
 def test_semantic_break_and_tone_reach_render_event(self):
  p=fixture();p.update(template_variant='ink_note',caption_line_breaks={'方法清楚':2},caption_tones={'方法清楚':'warning'})
  a=Painter(compile_plan(p));e=a._auto_events(a.p['clips'][0])[0]
  self.assertEqual(e['line_break'],2);self.assertEqual(e['tone'],'warning')
