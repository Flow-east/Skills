from unittest.mock import patch
import sys, unittest, math, copy
from pathlib import Path
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from camera_motion import validate,zoom_at,crop_box,apply,audit,build_track

def track():
 return dict(time_space='output',anchor=[.5,.42],keyframes=[dict(time=0.,zoom=1.),dict(time=1.,zoom=1.08),dict(time=2.,zoom=1.08),dict(time=3.,zoom=1.)])
class CameraTests(unittest.TestCase):
 def test_monotonic_ease_and_hold(self):
  p=track();z=[zoom_at(p,i/100) for i in range(101)]
  self.assertTrue(all(a<=b for a,b in zip(z,z[1:])));self.assertAlmostEqual(zoom_at(p,1.5),1.08)
 def test_zero_velocity_at_hold_boundaries(self):
  p=track();e=1e-4
  for t in [0,1,2,3]:self.assertLess(abs(zoom_at(p,t+e)-zoom_at(p,t-e))/(2*e),1e-6)
 def test_global_clock_no_cut_reset(self):
  r=audit(track(),3.,30,[1.5]);self.assertEqual(r['cut_boundaries'][0]['zoom_at_cut'],1.08)
 def test_anchor_is_fixed_and_crop_stays_inside(self):
  w,h=720,960;ax,ay=.46,.42
  for z in [1.,1.03,1.15]:
   x,y,r,b=crop_box((w,h),z,[ax,ay])
   self.assertAlmostEqual((ax*w-x)*z,ax*w);self.assertAlmostEqual((ay*h-y)*z,ay*h)
   self.assertTrue(0<=x<r<=w and 0<=y<b<=h)
 def test_source_box_is_not_integer_quantized(self):
  a=crop_box((720,960),1.0300,[.5,.42]);b=crop_box((720,960),1.0301,[.5,.42])
  self.assertNotEqual(a,b);self.assertLess(abs(a[0]-b[0]),1)
 def test_float_sampling_render_dimensions_and_no_black_border(self):
  im=Image.new('RGB',(720,960),(70,90,120));out=apply(im,track(),.35)
  self.assertEqual(out.size,im.size);self.assertEqual(out.getextrema(),im.getextrema())
 def test_reject_malformed_tracks(self):
  for field,value in [('time_space','source'),('anchor',[float('nan'),.5]),('curve','bounce')]:
   p=track();p[field]=value
   with self.assertRaises(ValueError):validate(p,3.)
  for t,z in [(float('nan'),1),(1,1.2),(-1,1),(0,1),(4,1)]:
   p=track();p['keyframes'][1]=dict(time=t,zoom=z)
   with self.assertRaises(ValueError):validate(p,3.)
 def test_explicit_track_overrides_legacy_zoom_in_painter(self):
  from render_template import Painter
  from timeline import compile_plan
  from test_pipeline import fixture
  p=compile_plan(fixture());p['clips'][0]['words']=[];p['clips'][0]['zoom']=1.15
  p['camera_motion']=dict(time_space='output',anchor=[.5,.42],keyframes=[dict(time=0,zoom=1),dict(time=p['duration'],zoom=1)])
  painter=Painter(p);im=Image.new('RGB',(720,1280),'white');im.putpixel((50,50),(0,0,0))
  self.assertEqual(painter.paint(im,p['clips'][0],.5).tobytes(),im.tobytes())

class CameraStateTests(unittest.TestCase):
 def recipe(self):
  return dict(levels=dict(normal=1.,medium=1.12,close=1.23),max_zoom=1.25,transitions=dict(punch=dict(seconds=.3),glide=dict(seconds=1.2)))
 def test_close_level_does_not_auto_return(self):
  p=build_track(10,[dict(start=1,level='close',kind='punch',reason='warning')],self.recipe())
  self.assertEqual(zoom_at(p,8),1.23);self.assertEqual(zoom_at(p,10),1.23)
 def test_return_only_when_authored(self):
  p=build_track(10,[dict(start=1,level='close',reason='warning'),dict(start=6,level='normal',kind='glide',reason='explanation')],self.recipe())
  self.assertEqual(zoom_at(p,5),1.23);self.assertEqual(zoom_at(p,8),1.)
 def test_explicit_cut_holds_then_changes_without_preramp(self):
  p=build_track(10,[dict(start=4,level='close',kind='cut',reason='source cut')],self.recipe())
  self.assertEqual(zoom_at(p,3.999),1.);self.assertEqual(zoom_at(p,4),1.23)
  self.assertEqual(audit(p,10,30,[4])['authored_cuts'],[4])
 def test_distinct_quick_and_slow_transitions(self):
  a=build_track(10,[dict(start=1,level='close',kind='punch',reason='warning')],self.recipe())
  b=build_track(10,[dict(start=1,level='close',kind='glide',reason='conclusion')],self.recipe())
  self.assertEqual(zoom_at(a,1.31),1.23);self.assertLess(zoom_at(b,1.31),1.1)
 def test_close_motion_does_not_overshoot(self):
  p=build_track(5,[dict(start=1,level='close',reason='warning')],self.recipe())
  self.assertTrue(all(1<=zoom_at(p,i/120)<=1.23 for i in range(600)))
 def test_bad_limits_and_overlaps_rejected(self):
  with self.assertRaises(ValueError):build_track(5,[dict(start=1,zoom=1.4,reason='bad')],self.recipe())
  with self.assertRaises(ValueError):build_track(5,[dict(start=1,level='close',kind='glide',reason='one'),dict(start=1.5,level='normal',reason='two')],self.recipe())
  p=track();p['max_zoom']=float('nan')
  with self.assertRaises(ValueError):validate(p,3)
 def test_keyword_caption_layer_is_screen_fixed(self):
  from render_template import Painter
  from timeline import compile_plan
  from test_pipeline import fixture
  p=compile_plan(fixture());p['reference_mode']=True
  plain=Painter(p);p2=copy.deepcopy(p);p2['camera_motion']=build_track(p2['duration'],[dict(start=0,level='close',reason='test')],self.recipe());tight=Painter(p2)
  a=Image.new('RGBA',(720,1280));b=a.copy()
  plain._active_clip=p['clips'][0];tight._active_clip=p2['clips'][0]
  plain.captions(a,p['clips'][0],.5);tight.captions(b,p2['clips'][0],.5)
  self.assertEqual(a.tobytes(),b.tobytes())

 def test_auto_plan_does_not_reintroduce_per_clip_zoom(self):
  import tempfile,json
  from auto_plan import build
  from test_pipeline import FONT
  raw=dict(video='/tmp/source.mp4',source_duration=5,segments=[dict(words=[dict(word='先看问题',start=.1,end=1),dict(word='再找方法',start=3,end=4)])])
  with tempfile.TemporaryDirectory() as d:
   with patch('timeline.probe',return_value={'streams':[{'codec_type':'video','width':720,'height':1280}]}):
    p=build(raw,Path(d)/'plan.json',FONT,template_variant='orange_hook')
  self.assertTrue(all(c['zoom']==1 for c in p['clips']))
  self.assertEqual(p['camera_motion']['policy'],'hold_until_next_authored_decision')
  self.assertTrue(all(k['zoom']==1 for k in p['camera_motion']['keyframes']))
