import copy, hashlib, json, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import template_library as lib

class LibraryTests(unittest.TestCase):
    def setUp(self): self.r=lib.read(lib.ROOT/'assets/template_progress.json')
    def test_exact_54_and_no_inferred_approval(self):
        s=lib.summary(self.r);self.assertEqual(s['target_count'],54);self.assertEqual(s['completed'],0)
        self.assertEqual(len(lib.eligible(self.r)),54)
    def test_legacy_numeric_id_rejected(self):
        with self.assertRaises(ValueError): lib.set_state(self.r,'kp-01','visual','in_use')
        self.assertTrue(all(row['id'].startswith('tpl-') for row in lib.eligible(self.r)))
        self.assertEqual(lib.summary(self.r)['visual_accepted'],0)
        self.assertTrue(any(row['limitations'] for row in self.r['targets']))

    def test_duplicate_and_missing(self):
        for rows in [self.r['targets'][:-1],self.r['targets'][:-1]+[self.r['targets'][0]]]:
            x=copy.deepcopy(self.r);x['targets']=rows
            with self.assertRaises(ValueError):lib.validate(x)
    def test_reference_hash_cannot_be_rewritten(self):
        self.r['targets'][0]['reference_sha256']='a'*64
        with self.assertRaises(ValueError):lib.validate(self.r)
    def test_alias_not_a_new_template(self):
        rows=[r for r in self.r['targets'] if r['variant']];rows[1]['variant']=rows[0]['variant']
        with self.assertRaises(ValueError):lib.validate(self.r)
    def test_in_use_templates_eligible_by_default(self):
        self.assertEqual(len(lib.eligible(self.r)),54);self.assertEqual(len(lib.eligible(self.r,preview=True)),54)
    def test_completed_requires_all_gates(self):
        r=self.r['targets'][5];self.assertFalse(lib.completed(r))
        r['visual']='accepted'
        with self.assertRaises(ValueError):lib.validate(self.r)
    def test_invalid_status(self):
        with self.assertRaises(ValueError):lib.set_state(self.r,'tpl-bilingual-wine-red','implementation','downloaded')
    def test_gate_needs_existing_evidence(self):
        with self.assertRaises(ValueError):lib.set_state(self.r,'tpl-soft-pink','technical','passed')
    def test_state_transition_hash_and_revision(self):
        row=self.r['targets'][5];row['implementation']='implemented'
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'e.json';p.write_text(json.dumps({'target_id':'tpl-soft-pink','revision':1,'passed':True}))
            ev={'path':'e.json','sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'revision':1,'reviewer':'test','scope':'test full package'}
            out=lib.set_state(self.r,'tpl-soft-pink','technical','passed',ev,d)
            self.assertEqual(out['targets'][5]['technical'],'passed');self.assertEqual(self.r['targets'][5]['technical'],'sample_passed')
            p.write_text('{}')
            with self.assertRaises(ValueError):lib.set_state(self.r,'tpl-soft-pink','technical','passed',ev,d)
    def test_unrelated_report_not_accepted(self):
        self.r['targets'][5]['implementation']='implemented'
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'e.json';p.write_text(json.dumps({'target_id':'tpl-white-gold','revision':1,'passed':True}))
            ev={'path':'e.json','sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'revision':1,'reviewer':'test','scope':'test'}
            with self.assertRaises(ValueError):lib.set_state(self.r,'tpl-soft-pink','technical','passed',ev,d)
    def test_gallery_separates_reference_and_preview(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'index.html';v=Path(d)/'sample.mp4';v.touch()
            lib.render_gallery(self.r,p,{'tpl-soft-pink':{'reference':str(v)}})
            self.assertIn('非本技能成片',p.read_text());self.assertNotIn('<summary>本技能校准预览',p.read_text())
            self.assertEqual(p.read_text().count('<article '),54)

if __name__=='__main__': unittest.main()
