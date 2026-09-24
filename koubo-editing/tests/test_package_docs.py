import re
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class PackageDocsTests(unittest.TestCase):
    def test_internal_markdown_links(self):
        for page in ROOT.rglob('*.md'):
            for href in re.findall(r'\]\(([^)]+)\)',page.read_text(encoding='utf8')):
                target=href.split('#',1)[0]
                if not target or target.startswith(('http:', 'https:', 'mailto:')):continue
                self.assertTrue((page.parent/target).is_file(),f'{page}: {href}')

    def test_no_development_history_in_distributable_docs(self):
        for page in [ROOT/'SKILL.md',ROOT/'README.md',ROOT/'README.zh-CN.md',*(ROOT/'references').glob('*.md')]:
            text=page.read_text(encoding='utf8')
            for phrase in ('Nexora','旧的 `ink_note / cream_serif`','等待用户审美验收','历史交付','当前状态：','逐套校准版','参考工程'):
                self.assertNotIn(phrase,text,str(page))
        self.assertLessEqual(len(list((ROOT/'references').glob('*.md'))),12)

    def test_required_license_and_content(self):
        for path in ('THIRD_PARTY_NOTICES.md','assets/fonts/manifest.json','assets/sfx/catalog.json','references/privacy-soft-mask.md','references/plan-format.md','references/keyword-stickers.md'):
            self.assertTrue((ROOT/path).is_file(),path)

if __name__=='__main__':unittest.main()
