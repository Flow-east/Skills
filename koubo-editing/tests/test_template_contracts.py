import copy, json, sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from template_contracts import ROOT,validate,bind
from template_catalog import get
from test_template_scenes import plan,painter

class ContractTests(unittest.TestCase):
    def setUp(self):self.c=json.loads((ROOT/'assets/template_contracts/tpl-soft-pink.json').read_text())
    def test_valid_assets(self):self.assertEqual(validate(self.c,verify_assets=True)['target_id'],'tpl-soft-pink')
    def test_each_rule_required(self):
        for key in ('typography','layout','annotation','timing','motion','composition'):
            c=copy.deepcopy(self.c);del c[key]
            with self.assertRaises(ValueError):validate(c)
    def test_no_unknown_effects(self):
        self.c['capabilities'].append('subject_segmentation')
        with self.assertRaises(ValueError):validate(self.c)
    def test_relative_assets_only(self):
        for path in ('/tmp/font.ttf','../../etc/passwd'):
            self.c['typography']['title']['file']=path
            with self.assertRaises(ValueError):validate(self.c)
    def test_nonfinite_or_unsafe_metric(self):
        for k,v in [('body_size',float('nan')),('title_y',1.5),('tag_x',True)]:
            c=copy.deepcopy(self.c);c['render']['scene_system'][k]=v
            with self.assertRaises(ValueError):validate(c)
    def test_reference_pair_verified(self):
        self.c['reference']['name']='基础白金'
        with self.assertRaises(ValueError):validate(self.c)
    def test_contract_is_authoritative(self):
        v=get('tpl-soft-pink');self.assertEqual(v['body_font_weight'],650);self.assertEqual(v['_contract']['layout']['max_phrases'],2)
    def test_unknown_ratio_blocked(self):
        p=plan();p['width']=960;p['height']=720
        with self.assertRaisesRegex(ValueError,'Aspect'):painter(p)
    def test_formal_acceptance_not_inferred(self):
        p=plan();p['template_delivery']='accepted'
        with self.assertRaisesRegex(ValueError,'acceptance'):painter(p)
    def test_camera_recipe_cannot_be_overridden(self):
        p=plan('white');p['camera_motion']={'time_space':'output','max_zoom':1.3,'keyframes':[{'time':0,'zoom':1},{'time':4,'zoom':1.3}]}
        with self.assertRaisesRegex(ValueError,'recipe'):painter(p)
    def test_status_metadata_not_frozen_in_render_recipe(self):
        v=get('tpl-minimal-white');self.assertEqual(v['design_status'],'implemented_in_use_iterating')
    def test_preview_explicitly_allowed(self):
        p=plan();p['template_delivery']='preview';self.assertTrue(painter(p).variant['_contract'])

if __name__=='__main__':unittest.main()
