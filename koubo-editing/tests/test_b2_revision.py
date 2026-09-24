import json,sys,unittest
from pathlib import Path
from PIL import Image,ImageChops
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_template_scenes import plan,painter
from template_scenes import audit_layout,layout,paint,write_srt
from template_scenes_b2 import ornament
from template_catalog import get

class B2RevisionTests(unittest.TestCase):
 def test_ink_reveals_caption_in_order_not_title(self):
  a=painter(plan('ink'));entries=layout(a)
  self.assertTrue(any(e['animation']=='ink_write' for e in entries if e['role']=='caption'))
  c=next(e for e in entries if e['role']=='caption');im=Image.new('RGB',(a.w,a.h),'#999999')
  early=paint(a,im,c['start']+.15).crop(c['box']);later=paint(a,im,c['start']+.8).crop(c['box'])
  self.assertIsNotNone(ImageChops.difference(early,later).getbbox())
 def test_redyellow_takeover_one_anchor_and_short_overlap(self):
  p=plan('redyellow',stack=True);p['scene_takeover']=True;a=painter(p)
  self.assertTrue(audit_layout(a)['passed']);c=[e for e in layout(a) if e['role']=='caption']
  self.assertAlmostEqual(c[0]['end'],p['scene_captions'][0]['phrases'][1]['start']+.16)
  self.assertLess(abs(c[0]['y']-c[1]['y']),25)
 def test_bounded_ornaments_do_not_force_other_content(self):
  for kind,marker,x,y in [('latte','cursor',.83,.65),('variety','hearts',.85,.68)]:
   p=plan(kind);p['scene_ornaments']=[dict(start=2.4 if kind=='latte' else 2.65,end=2.9 if kind=='latte' else 3.25,
                            kind=marker,x=x,y=y,reason='仅适配当前语义节点')]
   a=painter(p);self.assertTrue(audit_layout(a)['passed']);self.assertTrue(any(e['role']=='ornament' for e in layout(a)))
   self.assertTrue(ornament(a,marker).getchannel('A').getbbox())
   p['scene_ornaments'][0]['kind']='unsupported'
   with self.assertRaisesRegex(ValueError,'unsupported'):painter(p)
 def test_variety_uses_licensed_rounder_condensed_font(self):
  c=get('tpl-taiwan-variety')['_contract'];self.assertIn('ZCOOLQingKeHuangYou',c['typography']['body']['file'])
  a=painter(plan('variety'))
  self.assertIn('ZCOOLQingKeHuangYou',a.font_path('body'))

if __name__=='__main__':unittest.main()
