from unittest.mock import patch
import copy, importlib.util, json, math, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from timeline import compile_plan, load_plan, base_filter, caption_groups, write_srt
from make_cut_plan import make_plan
from render_template import Painter

FONT='/System/Library/Fonts/STHeiti Medium.ttc'
def fixture():
    return dict(version=2,source='/tmp/input.mp4',font=FONT,source_duration=10.,fps=30,width=720,height=1280,template='knowledge',clips=[
        dict(id='first',start=.1,end=1.1,reason='speech',words=[dict(text='方法',start=.1,end=.45),dict(text='清楚',start=.45,end=1.)]),
        dict(id='second',start=8.,end=9.,reason='skip retake and chatter',words=[dict(text='练习',start=8.,end=8.6)])])
class TimelineTests(unittest.TestCase):
    def validate(self,p):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'p.json'; f.write_text(json.dumps(p)); return load_plan(f,check_files=False)
    def test_removed_speech_cannot_be_merged_back(self):
        p=fixture(); p['removed']=[dict(start=.5,end=.7,reason='chatter')]
        with self.assertRaises(ValueError): self.validate(p)
    def test_second_unrelated_template_not_hardcoded(self):
        p=fixture(); p['template']='service'; p['title']='课程介绍'
        self.validate(p)
    def test_frame_audio_video_mapping(self):
        p=compile_plan(self.validate(fixture())); self.assertEqual(p['frame_count'],60)
        self.assertEqual(p['clips'][1]['output_start'],1.)
        self.assertEqual(p['clips'][1]['words'][0]['start'],1.)
        filters=base_filter(p)
        self.assertIn('trim=start_frame=240:end_frame=270',filters)
        self.assertIn('atrim=start=8.000000000:end=9.000000000',filters)
    def test_no_reintroduction_of_deleted_chatter(self):
        p=fixture(); raw={'video':'/tmp/input.mp4','segments':[{'words':[{'word':'保留','start':.1,'end':1.}, {'word':'OK','start':2.,'end':3.},{'word':'口误','start':4.,'end':5.},{'word':'重录','start':8.,'end':9.}]}]}
        for c in p['clips']: c.pop('words')
        plan=make_plan(raw,p); text=''.join(w['text'] for c in plan['clips'] for w in c['words'])
        self.assertEqual(text,'保留重录')
    def test_invalid_times_and_numbers(self):
        for value in [-1.,float('nan'),float('inf'),12.]:
            p=fixture(); p['clips'][0]['start']=value
            with self.assertRaises(ValueError): self.validate(p)
    def test_word_outside_clip(self):
        p=fixture(); p['clips'][1]['words'][0]['end']=9.5
        with self.assertRaises(ValueError): self.validate(p)
    def test_duplicate_ids_rejected(self):
        p=fixture(); p['clips'][1]['id']='first'
        with self.assertRaises(ValueError): self.validate(p)
    def test_order_rejected_unless_explicit(self):
        p=fixture(); p['clips'].reverse()
        with self.assertRaises(ValueError): self.validate(p)
        p['allow_reorder']=True; self.validate(p)
    def test_subframe_clip_rejected(self):
        p=fixture(); p['clips'][0]['end']=.101
        with self.assertRaises(ValueError): self.validate(p)
    def test_srt_no_original_time_leak(self):
        p=compile_plan(fixture())
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'sub.srt'; write_srt(p,f); txt=f.read_text()
            self.assertIn('00:00:01,000 --> 00:00:02,000',txt); self.assertNotIn('00:00:08',txt)
    def test_caption_chunking_uses_words(self):
        c={'words':[dict(text='先把需求',start=0,end=.8),dict(text='讲明白',start=.8,end=1.5),dict(text='再试',start=2.5,end=3.)]}
        gs=caption_groups(c,13); self.assertEqual(len(gs),2); self.assertEqual(gs[1][0]['start'],2.5)
    def test_missing_timestamp_rejected(self):
        with self.assertRaises(ValueError): make_plan({'video':'/tmp/x','segments':[{'text':'无时间'}]},fixture())
    @unittest.skipUnless(Path(FONT).exists(),'font not available')
    def test_inline_caption_and_animation_render(self):
        from PIL import Image, ImageChops
        p=compile_plan(fixture()); p['title']='测试标题'; p['clips'][0]['index']=1; p['clips'][0]['card']=dict(label='方法',value='讲明白',at=.1)
        painter=Painter(p); bg=Image.new('RGB',(720,1280),'#536478')
        a=painter.paint(bg,p['clips'][0],.02); b=painter.paint(bg,p['clips'][0],.28)
        self.assertIsNotNone(ImageChops.difference(a,b).getbbox())
        # Word boundary changes only caption highlight; these frames have fully settled card animation.
        x=painter.paint(bg,p['clips'][0],.3); y=painter.paint(bg,p['clips'][0],.65)
        self.assertIsNotNone(ImageChops.difference(x.crop((0,1090,720,1160)),y.crop((0,1090,720,1160))).getbbox())

if __name__=='__main__': unittest.main()

class ReferenceModeTests(unittest.TestCase):
    def test_semantic_marks_compile_to_rich_events(self):
        from make_cut_plan import make_plan
        raw={'video':'/tmp/input.mp4','source_duration':4.,'segments':[{'words':[{'word':'选择','start':0.,'end':.5},{'word':'豆包','start':.5,'end':1.2}]}]}
        d={'version':2,'font':FONT,'source_duration':4.,'fps':30,'width':720,'height':1280,'template':'knowledge','clips':[{'id':'a','start':0,'end':2,'reason':'point','semantic_marks':[{'start':0,'end':1.5,'value':'豆包','accent':'#FFD52F'}]}]}
        p=make_plan(raw,d); self.assertTrue(p['clips'][0]['caption_events']); self.assertEqual(p['clips'][0]['caption_events'][0]['runs'][1]['style'],'keyword')

class ReviewApplyTests(unittest.TestCase):
    def test_accepting_candidate_splits_clip_without_reintroducing_audio(self):
        from apply_review import apply
        p=fixture(); p['review']={'review_candidates':[{'start':.4,'end':.7,'reason':'possible retake'}]}
        q=apply(p,{'accept':[1]})
        self.assertEqual([(c['start'],c['end']) for c in q['clips']],[(.1,.4),(.7,1.1),(8.,9.)])
        self.assertEqual(q['removed'][0]['start'],.4)

class AutoPlanTests(unittest.TestCase):
    def test_auto_plan_emits_title_template_and_review_report(self):
        from auto_plan import build
        import tempfile
        raw={'video':'/tmp/input.mp4','source_duration':3.,'segments':[{'words':[{'word':'第一步','start':0.,'end':.4},{'word':'先说清楚','start':.4,'end':1.}]}]}
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'plan.json'
            with patch('timeline.probe',return_value={'streams':[{'codec_type':'video','width':720,'height':1280}]}):
                p=build(raw,out,FONT)
            self.assertTrue(p['title']); self.assertEqual(p['template'],'list-cards'); self.assertEqual(p['title'],'第一步先说清楚'); self.assertTrue(out.with_name('plan_review.md').exists())

class ProfileTests(unittest.TestCase):
    @unittest.skipUnless(Path(FONT).exists(),'font not available')
    def test_style_profile_overrides_theme_defaults(self):
        from render_template import Painter
        p=compile_plan(fixture()); p['style_profile']='warning'; painter=Painter(p)
        self.assertEqual(painter.theme['accent'],'#E84B4B')

class TemplateCatalogTests(unittest.TestCase):
    def test_three_template_variants_bind_font_color_and_zoom(self):
        from template_catalog import catalog
        c=catalog()
        for name in ('mint_clean','orange_hook','yellow_stroke'):
            self.assertTrue(Path(c[name]['font']).exists(), name)
            self.assertTrue(c[name]['accent']); self.assertIn(c[name]['zoom_language'],('gentle_push','punch_push','no_zoom'))
        self.assertNotEqual(c['mint_clean']['font'],c['orange_hook']['font'])
