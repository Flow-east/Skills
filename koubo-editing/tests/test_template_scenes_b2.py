import copy,json,sys,unittest,tempfile
from pathlib import Path
from PIL import Image,ImageChops
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_template_scenes import plan,painter
from template_scenes import audit_layout,layout,video_layer
from template_scenes_b2 import phrase
from font_guard import display_text,inspect_font

class Batch2Tests(unittest.TestCase):
    def test_five_styles_are_not_recolor(self):
        sprites=[]
        for k in ('white','redyellow','variety','ink','latte'):
            p=painter(plan(k));im=phrase(p,{'text':'方法清楚'});sprites.append((im.size,im.tobytes()))
        self.assertEqual(len(set(sprites)),5);self.assertGreater(len(set(x[0] for x in sprites)),3)
    def test_safe_supported_canvases(self):
        for k in ('white','redyellow','variety','ink','latte'):
            for h in (960,1280):
                p=plan(k);p['height']=h;self.assertTrue(audit_layout(painter(p))['passed'])
    def test_small_mode_actually_smaller(self):
        p=painter(plan('variety'));self.assertLess(phrase(p,{'text':'方法','mode':'small'}).height,phrase(p,{'text':'方法','mode':'display'}).height)
    def test_white_first_line_backplate_only(self):
        p=painter(plan('white',True));e=layout(p);caps=[x for x in e if x['role']=='caption']
        self.assertNotEqual(caps[0]['x'],caps[1]['x']);self.assertEqual(caps[0]['start'],.1);self.assertEqual(caps[1]['start'],1)
    def test_first_phrase_retained_without_reentry(self):
        p=painter(plan('white',True));im=Image.new('RGB',(720,960));b=next(e['box'] for e in layout(p) if e['role']=='caption')
        self.assertEqual(p.paint(im,p.p['clips'][0],.8).crop(b).tobytes(),p.paint(im,p.p['clips'][0],1.5).crop(b).tobytes())
    def test_paper_is_wide_strip_not_card(self):
        p=painter(plan('ink'));s=phrase(p,{'text':'方法清楚','mode':'paper'});self.assertGreater(s.width/s.height,5)
    def test_unsupported_mode_fails(self):
        for k in ('white','redyellow','variety','ink','latte'):
            p=plan(k);p['scene_captions'][0]['phrases'][0]['mode']='made_up'
            with self.assertRaises(ValueError):painter(p)
    def test_nonfinite_inset_fails(self):
        p=plan('latte');p['scene_canvas']=[dict(start=0,end=1,kind='inset',scale=float('nan'),reason='test')]
        with self.assertRaises(ValueError):painter(p)
    def test_unsupported_canvas_fails(self):
        p=plan('white');p['scene_canvas']=[dict(start=0,end=1,kind='inset',reason='test')]
        with self.assertRaises(ValueError):painter(p)
    def test_notes_need_slots_and_reasons(self):
        for e in [dict(start=0,end=1,text='注',slot=3,reason='test'),dict(start=0,end=1,text='注',slot=0)]:
            p=plan('redyellow');p['scene_notes']=[e]
            with self.assertRaises(ValueError):painter(p)
    def test_notes_remain_on_independent_clock(self):
        p=plan('redyellow');p['scene_notes']=[dict(start=.2,end=3.9,text='先检查',slot=0,reason='test')];a=painter(p)
        n=next(e for e in layout(a) if e['role']=='note');self.assertEqual(n['end'],3.9);self.assertIn('先检查',display_text(p))
    def test_old_template_rejects_new_notes(self):
        p=plan('pink');p['scene_notes']=[dict(start=.2,end=3,text='注',slot=0,reason='test')]
        with self.assertRaises(ValueError):painter(p)
    def test_inset_transforms_video_not_text(self):
        p=plan('redyellow');p['scene_canvas']=[dict(start=0,end=4,kind='inset',scale=.8,reason='test')];a=painter(p);im=Image.new('RGB',(720,960),'red')
        self.assertEqual(video_layer(a,im,1).getpixel((0,0))[:3],(8,8,8))
        b=next(x['box'] for x in layout(a) if x['role']=='title');p['scene_canvas']=[];other=painter(p)
        # Use text alpha as mask to verify sharp text geometry survives canvas transform.
        ti=next(x for x in layout(a) if x['role']=='title');self.assertEqual(ti['image'].tobytes(),layout(other)[0]['image'].tobytes())
    def test_latte_circle_is_cream_and_round(self):
        p=plan('latte');p['scene_canvas']=[dict(start=0,end=4,kind='circle',center=[.5,.4],radius=.3,background='#FCF9DD',reason='test')];a=painter(p);out=video_layer(a,Image.new('RGB',(720,960),'red'),1)
        self.assertEqual(out.getpixel((0,0))[:3],(252,249,221))
    def test_long_phrase_blocks(self):
        for k in ('white','redyellow','variety','ink','latte'):
            with self.assertRaisesRegex(ValueError,'too long'):phrase(painter(plan(k)),{'text':'方法'*80})
    def test_dark_padding_needs_explicit_ink_paper(self):
        from template_scenes_b2 import title
        p=plan('ink');p['scene_title_surface']='paper';a=painter(p);im=title(a)
        self.assertEqual(im.getpixel((0,0))[:3],(246,243,229));self.assertTrue(audit_layout(a)['passed'])
        p['template_variant']='ref_white_v1'
        with self.assertRaises(ValueError):painter(p)
    def test_numerals_english_traditional_coverage(self):
        a=painter(plan('white'));r=inspect_font(a.font_path(),'效率提升30%，3.5小時 AI/SOP',weight=a.font_weight());self.assertTrue(r['passed'])

if __name__=='__main__':unittest.main()
