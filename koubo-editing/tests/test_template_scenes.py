import copy,json,sys,tempfile,unittest
from pathlib import Path
from PIL import Image,ImageChops
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from render_template import Painter
from timeline import compile_plan
from template_scenes import audit_layout,layout,video_layer,write_srt
from font_guard import inspect_font,display_text
from test_pipeline import fixture


def plan(kind='pink',stack=False):
    p=fixture();p.update(width=720,height=960,template_variant=f'ref_{kind}_v1',scene_time_space='output',title='方法清楚',scene_title_lines=['方法清楚'],title_duration=1.0)
    # Fixture duration is four seconds; source-independent typography test content.
    p['clips']=[dict(id='t',start=0,end=4,reason='test',words=[dict(text='方法',start=.1,end=1),dict(text='清楚',start=1,end=2)])]
    phrases=[dict(start=.1,end=3.8,text='方法'),dict(start=1,end=3.8,runs=[dict(text='清楚',role='keyword')])] if stack else [dict(start=.1,end=3.8,text='方法清楚')]
    p['scene_captions']=[dict(start=.1,end=3.8,phrases=phrases)];p['scene_canvas']=[];p['scene_tags']=[]
    return p

def painter(p):return Painter(compile_plan(p))

class TemplateScenesTests(unittest.TestCase):
    def test_three_contracts_distinct(self):
        a=[painter(plan(k)) for k in ('pink','gold','grid')]
        self.assertEqual(len({x.variant['scene_system']['kind'] for x in a}),3)
        self.assertEqual(len({(layout(x)[-1]['image'].size,layout(x)[-1]['image'].tobytes()) for x in a}),3)
    def test_phrase_two_is_absent_until_its_own_start(self):
        a=painter(plan(stack=True));im=Image.new('RGB',(720,960),'#303030');es=[e for e in layout(a) if e['role']=='caption'];roi=tuple(round(x) for x in es[1]['box'])
        before=a.paint(im,a.p['clips'][0],.8);after=a.paint(im,a.p['clips'][0],1.4)
        self.assertIsNone(ImageChops.difference(before.crop(roi),im.crop(roi)).getbbox());self.assertIsNotNone(ImageChops.difference(after.crop(roi),im.crop(roi)).getbbox())
    def test_first_phrase_does_not_reanimate_when_second_enters(self):
        a=painter(plan(stack=True));im=Image.new('RGB',(720,960));e=[e for e in layout(a) if e['role']=='caption'][0];box=tuple(map(round,e['box']))
        self.assertEqual(a.paint(im,a.p['clips'][0],.8).crop(box).tobytes(),a.paint(im,a.p['clips'][0],1.4).crop(box).tobytes())
    def test_phrase_end_is_independent(self):
        p=plan(stack=True);p['scene_captions'][0]['phrases'][0]['end']=1.5;a=painter(p);im=Image.new('RGB',(720,960));e=[e for e in layout(a) if e['role']=='caption'][0];box=tuple(map(round,e['box']))
        self.assertIsNone(a.paint(im,a.p['clips'][0],2).crop(box).getbbox())
    def test_real_circle_not_normalized_ellipse(self):
        p=plan();p['scene_canvas']=[dict(start=0,end=4,kind='circle',radius=.25,center=[.5,.45],reason='framing test')];a=painter(p);im=video_layer(a,Image.new('RGB',(720,960),'red'),1).convert('RGB');mask=im.getchannel('R').point(lambda x:255 if x>100 else 0);b=mask.getbbox();self.assertEqual(b[2]-b[0],b[3]-b[1])
    def test_circle_does_not_clip_title(self):
        p=plan();p['scene_canvas']=[dict(start=0,end=4,kind='circle',radius=.25,center=[.5,.45],reason='framing test')];a=painter(p);im=a.paint(Image.new('RGB',(720,960)),a.p['clips'][0],.5)
        e=layout(a)[0];crop=im.crop(tuple(map(round,e['box'])));self.assertGreater(crop.getextrema()[0][1],150)
    def test_swipe_does_not_blur_title(self):
        p=plan('gold');p['scene_canvas']=[dict(start=.2,end=.6,kind='swipe')];a=painter(p);bg=Image.new('RGB',(720,960),'#202020');e=layout(a)[0];box=tuple(map(round,e['box']));with_fx=a.paint(bg,a.p['clips'][0],.4);p['scene_canvas']=[];b=painter(p);self.assertEqual(with_fx.crop(box).tobytes(),b.paint(bg,b.p['clips'][0],.4).crop(box).tobytes())
    def test_safe_layout(self):
        for k in ('pink','gold','grid'):self.assertTrue(audit_layout(painter(plan(k)))['passed'])
    def test_16_9_portrait_and_square_safe(self):
        for h in (720,1280):
            for k in ('pink','gold','grid'):
                p=plan(k);p['height']=h;self.assertTrue(audit_layout(painter(p))['passed'])
    def test_face_collision_blocks(self):
        p=plan();p['protected_regions']=[dict(start=0,end=4,box=[0,.65,1,.95])]
        with self.assertRaisesRegex(ValueError,'protected'):audit_layout(painter(p))
    def test_text_change_blocks(self):
        p=plan();p['scene_captions'][0]['phrases'][0]['text']='方法错误'
        with self.assertRaisesRegex(ValueError,'transcript'):painter(p)
    def test_nested_font_text_is_collected(self):
        p=plan(stack=True);p['scene_tags']=[dict(start=2,end=3,text='词标',reason='test')];text=display_text(p);self.assertIn('清楚',text);self.assertIn('词标',text)
    def test_variable_weight_matches_real_font(self):
        a=painter(plan());f=a.font(64);self.assertEqual(a.font_weight(),650)
        report=inspect_font(a.font_path(),'方法清楚',weight=650);self.assertTrue(report['passed']);self.assertEqual(report['weight'],650)
    def test_weights_have_different_raster(self):
        a=painter(plan());f=a.font(64);x=bytes(f.getmask('方法'));a.variant['body_font_weight']=900;self.assertNotEqual(x,bytes(a.font(64).getmask('方法')))
    def test_unknown_frame_mode_blocks(self):
        p=plan('grid');p['scene_canvas']=[dict(start=0,end=1,kind='circle')]
        with self.assertRaises(ValueError):painter(p)
    def test_unknown_time_space_blocks(self):
        p=plan();p['scene_time_space']='source'
        with self.assertRaises(ValueError):painter(p)
    def test_legacy_overlays_block(self):
        for key in ('caption_events','keyword_stickers','viewport_events'):
            p=plan();p[key]=[dict(text='旧')]
            with self.assertRaises(ValueError):painter(p)
    def test_long_caption_does_not_silently_clip(self):
        p=plan();text='很长的文字'*30;p['clips'][0]['words'][0]['text']=text;p['clips'][0]['words'][1]['text']='清楚';p['scene_captions'][0]['phrases'][0]['text']=text+'清楚'
        with self.assertRaisesRegex(ValueError,'too long'):audit_layout(painter(p))
    def test_nonfinite_times_block(self):
        p=plan();p['scene_captions'][0]['phrases'][0]['start']=float('nan')
        with self.assertRaises(ValueError):painter(p)
    def test_overlapping_groups_block(self):
        p=plan();p['scene_captions']*=2
        with self.assertRaises(ValueError):painter(p)
    def test_gold_cannot_use_pink_double_stack(self):
        with self.assertRaises(ValueError):painter(plan('gold',True))
    def test_circle_beyond_canvas_blocks(self):
        p=plan();p['scene_canvas']=[dict(start=0,end=1,kind='circle',center=[.1,.1],radius=.4,reason='bad')]
        with self.assertRaises(ValueError):painter(p)
    def test_output_events_dont_remap_at_source_offset(self):
        p=plan();p['source_duration']=100;c=p['clips'][0];c['start']+=20;c['end']+=20
        for w in c['words']:w['start']+=20;w['end']+=20
        a=painter(p);self.assertEqual(a.p['scene_captions'][0]['phrases'][0]['start'],.1)
    def test_srt_tracks_retained_phrases(self):
        a=painter(plan(stack=True))
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'a.srt';write_srt(a.p,f);t=f.read_text();self.assertIn('00:00:00,100 --> 00:00:01,000\n方法',t);self.assertIn('00:00:01,000 --> 00:00:03,800\n方法\n清楚',t)
    def test_tag_needs_semantic_reason(self):
        p=plan('grid');p['scene_tags']=[dict(start=2,end=3,text='词标')]
        with self.assertRaises(ValueError):painter(p)
    def test_gold_title_does_not_accept_two_lines(self):
        p=plan('gold');p['scene_title_lines']=['方法','清楚']
        with self.assertRaises(ValueError):painter(p)
    def test_decimal_or_percentage_change_not_hidden_as_punctuation(self):
        for original,changed in [('3.5','35'),('30%','30'),('-3','3')]:
            p=plan();p['clips'][0]['words']=[dict(text=original,start=.1,end=2)];p['scene_captions'][0]['phrases'][0]['text']=changed
            with self.assertRaisesRegex(ValueError,'transcript'):painter(p)
    def test_inline_cross_is_opt_in_and_gold_only(self):
        from template_scenes import phrase_sprite
        a=painter(plan('gold'));plain=phrase_sprite(a,dict(text='方法'));cross=phrase_sprite(a,dict(text='方法',symbol='cross'));self.assertGreater(cross.width,plain.width)
        p=plan('pink');p['scene_captions'][0]['phrases'][0]['symbol']='cross'
        with self.assertRaises(ValueError):painter(p)
    def test_title_semantic_lines_required(self):
        p=plan();p.pop('scene_title_lines')
        with self.assertRaises(ValueError):painter(p)

if __name__=='__main__':unittest.main()
