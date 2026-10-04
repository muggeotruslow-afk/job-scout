import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('onboarding',ROOT/'scripts/onboarding.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class OnboardingTests(unittest.TestCase):
    def test_first_use_does_not_create_private_files(self):
        with tempfile.TemporaryDirectory() as base:
            target=Path(base)/'private'
            self.assertEqual(m.profile_status(target)['state'],'first_use')
            self.assertFalse(target.exists())

    def test_draft_confirmation_and_reuse_preserve_pending_task(self):
        with tempfile.TemporaryDirectory() as base:
            directory=Path(base)
            value={'evidence_text':'虚构产品项目，负责需求和测试','target_roles':['AI产品'],
                'recruitment_type':'日常实习','locations':['北京'],'weekly_days':5,
                'earliest_start':'录用后一周','duration_months':6,'education':'本科在读','graduation':'2027-06','pending_request':'帮我找腾讯AI产品日常实习'}
            self.assertEqual(m.save_profile(directory,value)['state'],'needs_confirmation')
            self.assertEqual(m.save_profile(directory,value,True)['state'],'ready')
            result=m.profile_status(directory)
            self.assertEqual(result['profile']['pending_request'],value['pending_request'])
            self.assertEqual(result['profile']['weekly_days'],5)

    def test_confirmed_unknowns_stay_unknown(self):
        with tempfile.TemporaryDirectory() as base:
            result=m.save_profile(Path(base),{'evidence_text':'虚构简历'},True)
            self.assertEqual(result['state'],'ready_with_unknowns')
            self.assertIsNone(result['profile']['weekly_days'])
            self.assertIsNone(result['profile']['locations'])

    def test_invalid_input_does_not_overwrite_good_profile(self):
        with tempfile.TemporaryDirectory() as base:
            directory=Path(base);m.save_profile(directory,{'evidence_text':'原资料'},True)
            original=(directory/'profile.json').read_bytes()
            for value in ({'evidence_text':'修改','weekly_days':8},{'evidence_text':'修改','duration_months':0},{'evidence_text':''},{'evidence_text':'修改','locations':'北京'}):
                with self.assertRaises(ValueError):m.save_profile(directory,value,True)
            self.assertEqual((directory/'profile.json').read_bytes(),original)

    def test_corrupt_profile_is_reported_and_preserved(self):
        with tempfile.TemporaryDirectory() as base:
            directory=Path(base);file=directory/'profile.json';file.write_text('[]',encoding='utf-8')
            with self.assertRaises(ValueError):m.profile_status(directory)
            self.assertEqual(file.read_text(encoding='utf-8'),'[]')

    def test_docx_extracts_table_and_nested_text_once(self):
        with tempfile.TemporaryDirectory() as base:
            file=Path(base)/'resume.docx'
            xml='<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>虚构姓名</w:t></w:r></w:p><w:tbl><w:tr><w:tc><w:p><w:r><w:t>产品经历</w:t></w:r></w:p></w:tc></w:tr></w:tbl></w:body></w:document>'
            with ZipFile(file,'w') as archive:archive.writestr('word/document.xml',xml)
            self.assertEqual(m.extract_resume(file),'虚构姓名\n产品经历')

    def test_unsupported_resume_format_is_not_guessed(self):
        with self.assertRaises(ValueError):m.extract_resume(Path('resume.pdf'))

    def test_contact_details_are_not_persisted_in_evidence(self):
        with tempfile.TemporaryDirectory() as base:
            d=m.save_profile(Path(base),{'evidence_text':'虚构产品经历；13800138000；demo@example.com'},True)
            self.assertNotIn('13800138000',d['profile']['evidence_text'])
            self.assertNotIn('demo@example.com',d['profile']['evidence_text'])
            self.assertIn('虚构产品经历',d['profile']['evidence_text'])

if __name__=='__main__':unittest.main()
