import tempfile, unittest
from pathlib import Path
from security.incident_evidence import EvidenceStore, resolve_client_ip

class EvidenceTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(); self.store=EvidenceStore(Path(self.tmp.name)/"e.sqlite")
 def tearDown(self): self.tmp.cleanup()
 def test_hash_chain_and_redaction(self):
  self.store.record_event(event_type="auth.failed",source_ip="203.0.113.8",method="POST",path="/login?token=secret")
  self.assertTrue(self.store.verify_chain()["valid"])
  out=self.store.export_json()
  self.assertNotIn("secret",str(out)); self.assertEqual(out["events"][0]["path"],"/login")
 def test_forwarded_header_untrusted_peer_ignored(self):
  self.assertEqual(resolve_client_ip("203.0.113.2","198.51.100.9",["10.0.0.0/8"]),"203.0.113.2")
 def test_trusted_proxy_chain(self):
  self.assertEqual(resolve_client_ip("10.0.0.2","198.51.100.9, 10.0.0.1",["10.0.0.0/8"]),"198.51.100.9")
if __name__=="__main__": unittest.main()
