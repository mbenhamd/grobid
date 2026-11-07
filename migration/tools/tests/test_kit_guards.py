import hashlib
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest


def module(name):
    p=Path(__file__).resolve().parents[1]/(name+'.py')
    spec=importlib.util.spec_from_file_location(name,p)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


kit=module('check_kit');pin=module('verify_upstream')


class GraphTests(unittest.TestCase):
    def task(self,ident,deps):
        return dict(id=ident,depends_on=deps,acceptance=['real assertion'],owned_paths=['crates/a'],skill='grobid-port-text')
    def test_valid_diamond(self):
        tasks=[self.task('T000',[]),self.task('T001',['T000']),self.task('T002',['T000']),self.task('T003',['T001','T002'])]
        self.assertEqual(len(kit.validate_graph(tasks)),4)
    def test_invalid_graphs_fail(self):
        cases=[[],[self.task('T000',['T001'])],[self.task('T000',['T000'])],
               [self.task('T000',['T001']),self.task('T001',['T000'])],
               [self.task('T000',[]),self.task('T000',[])]]
        for value in cases:
            with self.subTest(value=value),self.assertRaises(kit.KitError):kit.validate_graph(value)


class PinTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        def g(*args):return subprocess.check_output(['git','-C',str(self.root),*args],text=True,stderr=subprocess.DEVNULL).strip()
        self.g=g;g('init');g('config','user.name','Fixture');g('config','user.email','fixture@example.invalid')
        (self.root/'source.txt').write_text('frozen source\n');g('add','source.txt');g('commit','-m','fixture')
        self.lock={'commit':g('rev-parse','HEAD'),'source_hashes':{'source.txt':hashlib.sha256((self.root/'source.txt').read_bytes()).hexdigest()}}
    def tearDown(self):self.tmp.cleanup()
    def test_clean_pin_is_static_only(self):
        result=pin.verify(self.root,self.lock)
        self.assertFalse(result['runtime_verified']);self.assertFalse(result['model_assets_verified'])
    def test_dirty_source_rejected(self):
        (self.root/'source.txt').write_text('changed')
        with self.assertRaises(pin.PinError):pin.verify(self.root,self.lock)
    def test_wrong_head_or_hash_or_empty_or_path_rejected(self):
        variants=[{'commit':'1'*40,'source_hashes':self.lock['source_hashes']},
                  {'commit':self.lock['commit'],'source_hashes':{'source.txt':'2'*64}},
                  {'commit':self.lock['commit'],'source_hashes':{}},
                  {'commit':self.lock['commit'],'source_hashes':{'../outside':'3'*64}}]
        for value in variants:
            with self.subTest(value=value),self.assertRaises(pin.PinError):pin.verify(self.root,value)


if __name__=='__main__':unittest.main()
