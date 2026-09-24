import copy,json,sys,tempfile,unittest
from pathlib import Path
from PIL import Image,ImageChops
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_template_scenes import plan,painter
from template_scenes import layout,audit_layout,write_srt as chinese_srt
from scene_bilingual import write_srt,wrap_text
from template_scenes_b3 import line
from font_guard import audit,display_text
from template_contracts import validate,ROOT
from template_catalog import get


def bilingual(kind='bired',stack=False):
    p=plan(kind,stack);p['template_delivery']='preview';p['scene_translations']=[]
    for j,e in enumerate(p['scene_captions'][0]['phrases']):
        e['id']=f'p{j}'
        text=e.get('text') or ''.join(r['text'] for r in e['runs'])
        p['scene_translations'].append(dict(phrase_id=e['id'],source_text=text,start=e['start']+.15,end=e['end']-.1,text='Make the method clear.' if not stack else ['Make the method','clear.'][j],language='en',review_status='reviewed',reviewer='fixture reviewer'))
    return p


class BilingualTests(unittest.TestCase):
    def test_three_independent_typographic_recipes(self):
        sprites=[line(painter(bilingual(k)),[dict(text='方法',role='body'),dict(text='清楚',role='keyword')],40) for k in ('bired','biluxe','biblue')]
        self.assertEqual(len({(x.size,x.tobytes()) for x in sprites}),3)
        self.assertEqual(len({x.size for x in sprites}),3)
    def test_all_declared_aspects_safe(self):
        for k in ('bired','biluxe','biblue'):
            for h in (960,1280):
                p=bilingual(k);p['height']=h
                self.assertTrue(audit_layout(painter(p))['passed'])
    def test_no_chinese_pollution(self):
        p=bilingual();p['scene_translations'][0]['text']='An independently edited English sentence.'
        self.assertTrue(painter(p))
        with tempfile.TemporaryDirectory() as d:
            chinese_srt(p,Path(d)/'zh.srt');write_srt(p,Path(d)/'en.srt')
            self.assertNotIn('English', (Path(d)/'zh.srt').read_text())
            self.assertNotIn('方法', (Path(d)/'en.srt').read_text())
    def test_translation_delayed_and_ends_independently(self):
        p=bilingual();a=painter(p);e=next(x for x in layout(a) if x['role']=='translation');bg=Image.new('RGB',(720,960),'#222222');box=e['box']
        for t in (.12,3.75):
            self.assertIsNone(ImageChops.difference(a.paint(bg,a.p['clips'][0],t).crop(box),bg.crop(box)).getbbox())
        self.assertIsNotNone(ImageChops.difference(a.paint(bg,a.p['clips'][0],1.5).crop(box),bg.crop(box)).getbbox())
    def test_first_translation_does_not_restart(self):
        a=painter(bilingual(stack=True));e=next(x for x in layout(a) if x['role']=='translation');bg=Image.new('RGB',(720,960));box=e['box']
        self.assertEqual(a.paint(bg,a.p['clips'][0],.8).crop(box).tobytes(),a.paint(bg,a.p['clips'][0],1.6).crop(box).tobytes())
    def test_english_wrap_preserves_words_and_numbers(self):
        text='Improve efficiency by 30% in 3.5 hours with AI and SOP.'
        rows,size=wrap_text(painter(bilingual()),text,23,380)
        self.assertEqual(' '.join(rows),text);self.assertLessEqual(len(rows),2)
    def test_long_translation_blocks(self):
        with self.assertRaisesRegex(ValueError,'too long'):wrap_text(painter(bilingual()),'long '*200,23,400)
    def test_no_single_word_truncation(self):
        with self.assertRaisesRegex(ValueError,'too long'):wrap_text(painter(bilingual()),'W'*100,23,400)
    def test_translation_coverage_required(self):
        p=bilingual();p['scene_translations']=[]
        with self.assertRaises(ValueError):painter(p)
    def test_unknown_duplicate_or_changed_anchor_blocks(self):
        for mutation in ('unknown','duplicate','changed'):
            p=bilingual()
            if mutation=='unknown':p['scene_translations'][0]['phrase_id']='missing'
            elif mutation=='duplicate':p['scene_translations']*=2
            else:p['scene_translations'][0]['source_text']='另一个意思'
            with self.assertRaises(ValueError):painter(p)
    def test_independent_but_not_detached_clock(self):
        for key,value in [('start',float('nan')),('start',0),('end',3.99)]:
            p=bilingual();p['scene_translations'][0][key]=value
            with self.assertRaises(ValueError):painter(p)
    def test_draft_requires_preview(self):
        p=bilingual();p['scene_translations'][0]['review_status']='draft';p.pop('template_delivery')
        with self.assertRaisesRegex(ValueError,'Draft'):painter(p)
    def test_reviewed_requires_provenance(self):
        p=bilingual();del p['scene_translations'][0]['reviewer']
        with self.assertRaises(ValueError):painter(p)
    def test_legacy_template_cannot_silently_ignore_translations(self):
        p=bilingual();p['template_variant']='ref_pink_v1'
        with self.assertRaisesRegex(ValueError,'Bilingual'):painter(p)
    def test_translation_font_guard_actual_role(self):
        p=bilingual();p['scene_translations'][0]['text']='AI效率提升30%，3.5小時'
        a=painter(p);q=audit(a)
        self.assertTrue(q['passed']);self.assertIn('translation',q['roles']);self.assertIn('AI效率',display_text(p))
        p['scene_translations'][0]['text']='replacement \ufffd'
        self.assertFalse(audit(painter(p))['passed'])
    def test_translation_face_collision_blocks(self):
        p=bilingual();a=painter(p);e=next(x for x in layout(a) if x['role']=='translation')
        x0,y0,x1,y1=e['box'];p['protected_regions']=[dict(start=0,end=4,box=[x0/720,y0/960,x1/720,y1/960])]
        with self.assertRaisesRegex(ValueError,'protected'):audit_layout(painter(p))
    def test_highlight_requires_anchor_and_reason(self):
        p=bilingual('biluxe');p['title_duration']=.1
        p['scene_highlights']=[dict(start=1,end=3,text='方法',phrase_id='p0',reason='emphasis')]
        self.assertTrue(audit_layout(painter(p))['passed'])
        p['scene_highlights'][0]['text']='虚构结论'
        with self.assertRaises(ValueError):painter(p)
    def test_title_highlight_overlap_blocked(self):
        p=bilingual('biluxe');p['scene_highlights']=[dict(start=.2,end=3,text='方法',phrase_id='p0',reason='test')]
        with self.assertRaisesRegex(ValueError,'collide'):audit_layout(painter(p))
    def test_missing_translation_font_contract_rejected(self):
        c=json.loads((ROOT/'assets/template_contracts/kp-01.json').read_text());del c['typography']['translation']
        with self.assertRaisesRegex(ValueError,'font role'):validate(c)
    def test_all_three_licensed_contracts(self):
        for i in (1,2,3):validate(json.loads((ROOT/f'assets/template_contracts/kp-{i:02}.json').read_text()),verify_assets=True)
    def test_formal_delivery_still_requires_user_acceptance(self):
        p=bilingual();p['template_delivery']='accepted'
        with self.assertRaisesRegex(ValueError,'acceptance'):painter(p)
    def test_chinese_negation_change_rejected(self):
        p=bilingual();p['scene_captions'][0]['phrases'][0]['text']='方法不清楚'
        with self.assertRaises(ValueError):painter(p)

if __name__=='__main__':unittest.main()
