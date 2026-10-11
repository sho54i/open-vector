"""Local HTTP smoke and failure recovery for the real release package/updater."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import local_updater as updater
from build_release import build


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self,*args): pass


class UpdaterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        cls.base=Path(cls.tmp.name)
        cls.feed=cls.base/'feed'
        cls.manifest=build(ROOT,cls.feed,'smoke-1',1)
        cls.archive=(cls.feed/cls.manifest['package']).read_bytes()
        cls.files=updater.unpack(cls.manifest,cls.archive)
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=str(cls.feed)))
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.url=f'http://127.0.0.1:{cls.server.server_port}/latest.json'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join();cls.tmp.cleanup()

    def setUp(self):
        self.local=tempfile.TemporaryDirectory(dir=self.base)
        self.root=Path(self.local.name)
        (self.root/'vector_pen_tool.html').write_text('original local editor')
        (self.root/'artwork.json').write_text('my artwork')
        (self.root/'planning').mkdir();(self.root/'planning/notes.txt').write_text('keep planning')

    def tearDown(self): self.local.cleanup()

    def cli(self,action):
        return subprocess.run([sys.executable,str(ROOT/'scripts/local_updater.py'),action,'--directory',str(self.root),'--manifest',self.url,'--allow-localhost'],capture_output=True,text=True,timeout=15)

    def test_http_check_apply_noop_rollback(self):
        result=self.cli('check');self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual((self.root/'vector_pen_tool.html').read_text(),'original local editor')
        self.assertFalse((self.root/updater.STATE).exists(),'Check must not write updater state')
        result=self.cli('apply');self.assertEqual(result.returncode,0,result.stderr)
        for name,data in self.files.items():self.assertEqual((self.root/name).read_bytes(),data)
        result=self.cli('apply');self.assertEqual(result.returncode,0,result.stderr);self.assertIn('no files changed',result.stdout)
        self.assertEqual((self.root/'artwork.json').read_text(),'my artwork')
        self.assertEqual((self.root/'planning/notes.txt').read_text(),'keep planning')
        result=self.cli('rollback');self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual((self.root/'vector_pen_tool.html').read_text(),'original local editor')
        self.assertFalse((self.root/'vendor/draw-fonts.js').exists())
        self.assertFalse((self.root/updater.RECEIPT).exists())

    def test_bad_package_and_file_hash(self):
        with self.assertRaises(updater.UpdateError):updater.unpack(self.manifest,self.archive+b'bad')
        m=json.loads(json.dumps(self.manifest));m['files']['vector_pen_tool.html']['sha256']='0'*64
        with self.assertRaises(updater.UpdateError):updater.unpack(m,self.archive)
        self.assertEqual((self.root/'vector_pen_tool.html').read_text(),'original local editor')

    def test_traversal_reserved_and_unowned_files(self):
        for name in ['../outside','vendor/../../x','/tmp/x','vendor\\x','vendor/NUL.js','planning/a.txt','.git/config','vendor/x:stream.js']:
            self.assertFalse(updater.allowed(name),name)
        m=json.loads(json.dumps(self.manifest));m['files']['../outside']={'size':1,'sha256':'0'*64}
        with self.assertRaises(updater.UpdateError):updater.validate_manifest(m)

    def test_symlink_destination(self):
        outside=self.root/'outside';outside.mkdir()
        (self.root/'vendor').symlink_to(outside,target_is_directory=True)
        with self.assertRaises(updater.UpdateError):updater.install(self.root,self.manifest,self.files)
        self.assertEqual(list(outside.iterdir()),[])
        self.assertEqual((self.root/'vector_pen_tool.html').read_text(),'original local editor')

    def test_write_failure_restores_exact_originals(self):
        with updater.install_lock(self.root):
            with self.assertRaises(OSError):
                updater.transact(self.root,{'vector_pen_tool.html':b'new','vendor/temp.js':b'new file'},fail_after=2)
        self.assertEqual((self.root/'vector_pen_tool.html').read_text(),'original local editor')
        self.assertFalse((self.root/'vendor/temp.js').exists())
        self.assertFalse((self.root/updater.STATE/'pending.json').exists())

    def test_process_crash_recovery(self):
        # Kill after a durable file replacement, before transaction completion.
        program='''import sys,os
from pathlib import Path
sys.path.insert(0,sys.argv[1])
import local_updater as u
root=Path(sys.argv[2]); original=u.atomic_write
def crash(path,data):
    original(path,data)
    if path==root/'vector_pen_tool.html': os._exit(71)
u.atomic_write=crash
with u.install_lock(root): u.transact(root,{'vector_pen_tool.html':b'partial update'})
'''
        result=subprocess.run([sys.executable,'-c',program,str(ROOT/'scripts'),str(self.root)],timeout=10)
        self.assertEqual(result.returncode,71)
        self.assertEqual((self.root/'vector_pen_tool.html').read_bytes(),b'partial update')
        with self.assertRaises(updater.UpdateError):updater.install(self.root,self.manifest,self.files)
        updater.rollback(self.root,recover=True)
        self.assertEqual((self.root/'vector_pen_tool.html').read_text(),'original local editor')

    def test_local_edit_blocks_update_and_rollback(self):
        updater.install(self.root,self.manifest,self.files)
        (self.root/'vector_pen_tool.html').write_text('user edit')
        with self.assertRaises(updater.UpdateError):updater.install(self.root,self.manifest,self.files)
        with self.assertRaises(updater.UpdateError):updater.rollback(self.root)
        self.assertEqual((self.root/'vector_pen_tool.html').read_text(),'user edit')

    def test_new_version_and_obsolete_managed_file(self):
        updater.install(self.root,self.manifest,self.files)
        m=json.loads(json.dumps(self.manifest));m['sequence']=2;m['version']='smoke-2'
        files=dict(self.files);del files['vendor/draw-fonts.js'];del m['files']['vendor/draw-fonts.js']
        updater.install(self.root,m,files)
        self.assertFalse((self.root/'vendor/draw-fonts.js').exists())
        updater.rollback(self.root)
        self.assertEqual((self.root/'vendor/draw-fonts.js').read_bytes(),self.files['vendor/draw-fonts.js'])
        self.assertEqual(json.loads((self.root/updater.RECEIPT).read_text())['version'],'smoke-1')

    def test_concurrent_updater_rejected(self):
        with updater.install_lock(self.root):
            with self.assertRaises(updater.UpdateError):
                with updater.install_lock(self.root):pass

    def test_http_and_cross_origin_redirect_refused(self):
        with self.assertRaises(updater.UpdateError):updater.download(self.url,1000)
        from urllib.request import Request
        with self.assertRaises(updater.UpdateError):
            updater.SameOriginRedirect().redirect_request(Request('https://example.com/a'),None,302,'',{},'https://other.example/a')

    def test_manifest_limits_and_zip_symlinks(self):
        m=json.loads(json.dumps(self.manifest));m['size']=updater.MAX_PACKAGE+1
        with self.assertRaises(updater.UpdateError):updater.validate_manifest(m)
        stream=io.BytesIO()
        with zipfile.ZipFile(stream,'w') as z:
            info=zipfile.ZipInfo('vector_pen_tool.html');info.external_attr=0o120777<<16
            z.writestr(info,b'outside')
        blob=stream.getvalue();m=dict(self.manifest,size=len(blob),sha256=updater.digest(blob),files={'vector_pen_tool.html':{'size':7,'sha256':updater.digest(b'outside')}})
        with self.assertRaises(updater.UpdateError):updater.unpack(m,blob)

    def test_release_is_repeatable_and_excludes_private_files(self):
        m=build(ROOT,self.feed,'smoke-1',1)
        self.assertEqual(m,self.manifest)
        self.assertFalse(any(n.startswith(('planning/','tests/','.git/')) for n in m['files']))


if __name__=='__main__':unittest.main(verbosity=2)
