import sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from timeline import caption_groups, write_srt
class CaptionBreakTests(unittest.TestCase):
 def test_authored_break_keeps_efficiency_together(self):
  words=[dict(text=t,start=i*.1,end=(i+1)*.1,caption_break_after=(i==8)) for i,t in enumerate('那今天我们来聊一聊员工的效率问题')]
  groups=caption_groups(dict(words=words))
  self.assertEqual([''.join(w['text'] for w in g) for g in groups],['那今天我们来聊一聊','员工的效率问题'])
 def test_srt_uses_same_group_size_as_renderer(self):
  words=[dict(text=t,start=i*.1,end=(i+1)*.1) for i,t in enumerate('甲乙丙丁戊己')]
  p=dict(caption_chars=3,clips=[dict(words=words,output_start=0,output_end=.6)])
  with tempfile.TemporaryDirectory() as d:
   out=Path(d)/'captions.srt';write_srt(p,out);s=out.read_text()
   self.assertIn('甲乙丙\n',s);self.assertIn('丁戊己\n',s)
