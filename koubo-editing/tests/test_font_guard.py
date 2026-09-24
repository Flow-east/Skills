import json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from font_guard import inspect_font,display_text
from render_template import Painter
from timeline import compile_plan
from caption_corrections import apply
ST='/System/Library/Fonts/STHeiti Medium.ttc'
JP='/System/Library/Fonts/ヒラギノ角ゴシック W8.ttc'
TEXT='员工们来检查公司的执行力差，反复复制粘贴改格式，低效环节自查，私信我诊断哦。'
def plan():
 return dict(version=2,font=ST,source='/tmp/source.mp4',source_duration=3.,width=720,height=960,fps=30,
 template='knowledge',style_profile='mint',template_variant='orange_hook',title='员工效率不高',
 audio=dict(normalize=False),clips=[dict(id='a',start=0.,end=3.,reason='test',words=[dict(text=TEXT,start=0.,end=2.8)])])
@unittest.skipUnless(Path(ST).exists(),'local CJK font required')
class FontGuardTests(unittest.TestCase):
 def test_chinese_font_covers_real_video_text(self):
  self.assertTrue(inspect_font(ST,TEXT)['passed'])
 @unittest.skipUnless(Path(JP).exists(),'Japanese fixture font required')
 def test_existing_japanese_font_is_rejected_for_simplified_text(self):
  r=inspect_font(JP,TEXT); self.assertFalse(r['passed']); self.assertIn('员',r['missing']); self.assertIn('们',r['missing'])
 def test_replacement_character_is_rejected(self):
  self.assertFalse(inspect_font(ST,'文字\ufffd')['passed'])
 def test_title_caption_run_and_english_text_are_checked(self):
  p=plan();p['clips'][0]['caption_events']=[dict(start=0,end=1,runs=[dict(text='测试')],english=dict(text='check'))]
  text=display_text(p);self.assertIn('员工效率不高',text);self.assertIn('测试',text);self.assertIn('check',text)
 def test_auto_caption_keeps_keyword_as_one_wrap_unit(self):
  p=plan();p['clips'][0]['words']=[dict(text=x,start=i*.2,end=(i+1)*.2) for i,x in enumerate('各种表格汇总数据')]
  p['clips'][0]['emphasis_words']=['汇总数据']
  q=compile_plan(p);events=Painter(q)._auto_events(q['clips'][0])
  self.assertEqual([r['text'] for r in events[0]['runs']],['各种表格','汇总数据'])
 def test_template_color_cannot_be_overwritten_by_legacy_profile(self):
  from template_catalog import get
  painter=Painter(compile_plan(plan())); self.assertEqual(painter.theme['accent'],get('orange_hook')['accent'])
 def test_provenance_records_actual_fonts_and_script_hash(self):
  with tempfile.TemporaryDirectory() as out:
   r=Painter(compile_plan(plan())).font_preflight(out)
   self.assertEqual(r['roles']['body'],ST);self.assertTrue(r['passed'])
   self.assertIn('scripts/render_template.py',r['files']);self.assertTrue(Path(out,'font_qa.json').exists())
 @unittest.skipUnless(Path(JP).exists(),'Japanese fixture font required')
 def test_bad_font_prevents_render_before_encoder_start(self):
  import render_template as core
  p=plan();p['template_variant']=None;p['font']=JP
  with tempfile.TemporaryDirectory() as tmp:
   out=Path(tmp,'out')
   with patch.object(core,'load_plan',return_value=p),patch.object(core,'probe',return_value=dict(streams=[dict(codec_type='video',width=720,height=960),dict(codec_type='audio')],format=dict(duration=3.))),patch.object(core,'run') as runner:
    with self.assertRaisesRegex(ValueError,'FONT_COVERAGE_FAILED'):core.render('/tmp/plan.json',out)
    runner.assert_not_called();self.assertFalse((out/'final.mp4').exists());self.assertFalse(json.loads((out/'font_qa.json').read_text())['passed'])
class CorrectionsTests(unittest.TestCase):
 def test_correction_spans_asr_tokens_and_retains_original(self):
  p=plan();p['clips'][0]['words']=[dict(text=x,start=i*.2,end=(i+1)*.2) for i,x in enumerate(['执','行','理','查。'])]
  q=apply(p,[dict(start=0.,end=.8,old='执行理查。',new='执行力差。',reason='reviewed')])
  self.assertEqual(q['clips'][0]['words'][0]['text'],'执行力差。');self.assertEqual(len(p['clips'][0]['words']),4);self.assertTrue(q['caption_corrections'][0]['applied'])
 def test_unmatched_correction_fails_instead_of_claiming_success(self):
  with self.assertRaises(ValueError):apply(plan(),[dict(start=0,end=1,old='不匹配',new='已修正')])
if __name__=='__main__':unittest.main()

class PortableFontMetadataTests(unittest.TestCase):
    def test_template_contract_replaces_machine_font_metadata(self):
        p = plan(); p['template_variant'] = 'tpl-bilingual-wine-red'
        q = compile_plan(p)
        self.assertTrue(q['font'].endswith('/assets/fonts/NotoSerifSC-VF.ttf'))
        self.assertEqual(q['font_source'], 'skill_bundle_contract')
        self.assertEqual(q['font_roles']['translation']['index'], 0)
        self.assertTrue(q['font_roles']['body']['sha256'])
        self.assertNotIn('/System/Library/Fonts/', q['font'])

class PortableFontAuditTests(unittest.TestCase):
    def test_role_metadata_is_verified(self):
        p = plan(); p['template_variant'] = 'tpl-bilingual-wine-red'
        q = compile_plan(p)
        q['clips'][0]['words']=[dict(text='测试字幕',start=.1,end=2.5)]
        q.update(scene_time_space='output', scene_title_lines=['测试标题'], scene_captions=[dict(start=0.1,end=2.5,phrases=[dict(start=0.1,end=2.5,text='测试字幕',id='p',runs=[dict(text='测试',role='body'),dict(text='字幕',role='keyword')])])], template_delivery='preview', scene_translations=[dict(phrase_id='p',source_text='测试字幕',start=.1,end=2.5,text='test caption',language='en',review_status='reviewed',reviewer='test')])
        a = Painter(q)
        with tempfile.TemporaryDirectory() as d:
            report = a.font_preflight(d)
        self.assertTrue(report['font_roles_consistent'])
        self.assertTrue(all(x['passed'] for x in report['font_role_metadata']))
