import copy,json,sys,unittest,tempfile
from pathlib import Path
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from render_template import Painter
from timeline import compile_plan,write_srt,caption_groups
from template_catalog import get
from design_system import caption_layout,sticker_layout,title_layout,animated,overlaps
from keyword_stickers import badge
from test_pipeline import fixture

NAMES=('orange_hook','rounded_pop','ink_note','cream_serif')
def painter(name='orange_hook',height=960):
 p=fixture();p.update(template_variant=name,height=height)
 return Painter(compile_plan(p))
def event():return dict(start=.1,end=.9,runs=[dict(text='先不要',style='base'),dict(text='批评员工',style='keyword')])

class DesignTests(unittest.TestCase):
 def test_four_layouts_differ_without_color_or_font_comparison(self):
  configs=[get(n)['design_system'] for n in NAMES]
  for section,key in [('caption','kind'),('title','kind')]:self.assertEqual(len({c[section][key] for c in configs}),4)
  # References can share a safe caption zone; structure, not forced coordinates, differentiates them.
  self.assertGreaterEqual(len({tuple(c['caption']['anchor']) for c in configs}),3)
  self.assertEqual(len({tuple(c['sticker']['anchors'][0]) for c in configs}),4)
 def test_actual_caption_boxes_have_distinct_alignment_and_positions(self):
  boxes=[caption_layout(painter(n),event())[2] for n in NAMES]
  self.assertEqual(len(set(boxes)),4)
  self.assertGreater(boxes[2][3]-boxes[2][1],boxes[3][3]-boxes[3][1])
 def test_animation_trajectories_not_just_colors(self):
  im=Image.new('RGBA',(180,90),'white');values=[]
  for n in NAMES:
   cfg=get(n)['design_system']['caption'];layer,dx,dy=animated(im,.08,1,cfg,1)
   values.append((layer.size,dx,dy))
  self.assertEqual(len(set(values)),4)
 def test_full_animation_envelope_stays_in_safe_area(self):
  for n in NAMES:
   for h in (960,1280):
    a=painter(n,h);sprite,area,box,cfg=caption_layout(a,event())
    for i in range(31):
     layer,dx,dy=animated(sprite,i/100,.9,cfg,a.unit)
     x=box[0]+(area.width-layer.width)/2+dx;y=box[1]+(area.height-layer.height)/2+dy
     self.assertGreaterEqual(x,12);self.assertGreaterEqual(y,12)
     self.assertLessEqual(x+layer.width,720-12);self.assertLessEqual(y+layer.height,h-12)
 def test_keyword_stays_atomic_and_caption_does_not_clip(self):
  from design_system import _measure
  a=painter('rounded_pop');cfg=a.variant['design_system']['caption']
  e=dict(start=0,end=1,runs=[dict(text='反复地整理这些内容',style='base'),dict(text='汇总数据',style='keyword')])
  lines=_measure(a,e['runs'],cfg,350)
  self.assertLessEqual(len(lines),2);self.assertEqual([r['text'] for ln in lines for r,f in ln if r['style']=='keyword'],['汇总数据'])
 def test_manual_position_overrides_template(self):
  a=painter();e=event();e['position']=[.5,.4]
  box=caption_layout(a,e)[2];self.assertAlmostEqual((box[1]+box[3])/2,.4*960,delta=1)
 def test_caption_fallback_resolved_for_entire_event_not_current_frame(self):
  a=painter('rounded_pop');a.p['protected_regions']=[dict(start=.5,end=1,box=[.1,.55,.9,.76])]
  e=event();box=caption_layout(a,e)[2]
  self.assertGreater(box[1],.76*960)
  self.assertIs(caption_layout(a,e),caption_layout(a,copy.deepcopy(e)))
 def test_sticker_fallback_uses_all_overlapping_caption_events(self):
  a=painter('ink_note');ev=dict(start=.1,end=.9,text='先别急',reason='warning')
  a.p['caption_events']=[dict(start=.1,end=.3,text='第一句',position=[.5,.9]),dict(start=.3,end=.9,text='第二句',position=[.5,.9])]
  box=sticker_layout(a,ev)[2];self.assertLess(box[3],.3*960)
 def test_blocked_layout_fails_instead_of_covering_face(self):
  a=painter();a.p['protected_regions']=[dict(box=[0,0,1,1])]
  with self.assertRaises(ValueError):caption_layout(a,event())
  with self.assertRaises(ValueError):sticker_layout(a,dict(start=.1,end=.9,text='警告',reason='warning'))
 def test_template_defaults_reach_srt_grouping(self):
  for n in NAMES:
   a=painter(n);self.assertEqual(a.p['caption_chars'],get(n)['design_system']['caption']['chars'])
   self.assertEqual(a.groups['first'],caption_groups(a.p['clips'][0],a.p['caption_chars']))
 def test_author_caption_chars_not_overridden(self):
  p=fixture();p.update(template_variant='rounded_pop',caption_chars=7);self.assertEqual(compile_plan(p)['caption_chars'],7)
 def test_new_layout_used_without_reference_mode(self):
  a=painter();self.assertFalse(a.p.get('reference_mode',False))
  out=a.paint(Image.new('RGB',(720,960),'#808080'),a.p['clips'][0],.5)
  self.assertTrue(any(k[0]=='design_caption_layout' for k in a.layers))
 def test_no_silent_bilingual_loss(self):
  p=fixture();p.update(template_variant='ink_note',english_map={'方法':'method'})
  with self.assertRaises(ValueError):Painter(compile_plan(p))
 def test_invalid_protected_rectangle_fails_early(self):
  p=fixture();p.update(template_variant='ink_note',protected_regions=[dict(box=[.8,.1,.1,.6])])
  with self.assertRaises(ValueError):Painter(compile_plan(p))
 def test_title_duration_is_template_default_unless_authored(self):
  for n in NAMES:
   a=painter(n);a.p['title']='普通标题';a.p['duration']=8
   im=Image.new('RGBA',(720,960));from design_system import paint_title
   paint_title(a,im,get(n)['design_system']['title']['duration']+.01);self.assertIsNone(im.getbbox())
 def test_sticker_rendered_size_respects_actual_rotated_bounds(self):
  for n in NAMES:
   a=painter(n);cfg=a.variant['design_system']['sticker'];im=badge(a,dict(text='高频重复任务'))
   self.assertLessEqual(im.width,a.w*cfg['max_width']+1);self.assertLessEqual(im.height,a.h*cfg['max_height']+1)
 def test_existing_camera_and_audio_are_not_reauthored_by_design(self):
  from camera_motion import build_track
  p=fixture();p['template_variant']='rounded_pop';p['audio']={'normalize':False};p['camera_motion']=build_track(2,[],get('orange_hook')['camera_recipe'])
  original=copy.deepcopy(p);a=Painter(compile_plan(p));self.assertEqual(a.p['camera_motion'],original['camera_motion']);self.assertEqual(a.p['audio'],original['audio'])
