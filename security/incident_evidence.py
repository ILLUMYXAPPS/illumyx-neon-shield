"""Server-side, privacy-conscious intrusion evidence ledger."""
import hashlib, ipaddress, json, sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

def _ip(value):
    try: return str(ipaddress.ip_address(value.strip())) if value else None
    except ValueError: return None

def resolve_client_ip(peer_ip, forwarded_for=None, trusted_proxies=()):
    peer=_ip(peer_ip)
    if not peer: return None
    nets=[]
    for item in trusted_proxies:
        try: nets.append(ipaddress.ip_network(item, strict=False))
        except ValueError: pass
    trusted=lambda value:any(ipaddress.ip_address(value) in n for n in nets)
    if not trusted(peer) or not forwarded_for: return peer
    chain=[x for x in (_ip(p) for p in forwarded_for.split(",")) if x]+[peer]
    return next((x for x in reversed(chain) if not trusted(x)), chain[0])

class EvidenceStore:
    """Append-only SQLite ledger. Hash chaining is tamper-evident, not tamper-proof."""
    def __init__(self, database):
        self.database=str(database); Path(self.database).parent.mkdir(parents=True,exist_ok=True)
        with self._db() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS events(
            seq INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT NOT NULL, kind TEXT NOT NULL,
            ip TEXT, method TEXT, path TEXT, status INTEGER, agent TEXT, details TEXT NOT NULL,
            prev TEXT NOT NULL, digest TEXT NOT NULL UNIQUE)""")
    @contextmanager
    def _db(self):
        """Open a short-lived connection and always release its file handle."""
        db = sqlite3.connect(self.database, timeout=15, isolation_level="IMMEDIATE")
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()
    def record_event(self, *, event_type, source_ip=None, method=None, path=None,
                     status_code=None, user_agent=None, details=None):
        if not event_type or len(event_type)>80: raise ValueError("invalid event_type")
        clean={}
        for k,v in (details or {}).items():
            if isinstance(k,str) and len(k)<=64 and (v is None or isinstance(v,(str,int,float,bool))):
                clean[k]=v[:256] if isinstance(v,str) else v
        at=datetime.now(timezone.utc).isoformat()
        with self._db() as db:
            row=db.execute("SELECT digest FROM events ORDER BY seq DESC LIMIT 1").fetchone()
            prev=row["digest"] if row else "0"*64
            payload={"at":at,"kind":event_type,"ip":_ip(source_ip),
              "method":method[:12].upper() if method else None,
              "path":path.split("?",1)[0].split("#",1)[0][:512] if path else None,
              "status":status_code,"agent":user_agent[:256] if user_agent else None,
              "details":clean,"prev":prev}
            canonical=json.dumps(payload,sort_keys=True,separators=(",",":"),ensure_ascii=False)
            digest=hashlib.sha256(canonical.encode()).hexdigest()
            cur=db.execute("INSERT INTO events(at,kind,ip,method,path,status,agent,details,prev,digest) VALUES(?,?,?,?,?,?,?,?,?,?)",
             (at,event_type,payload["ip"],payload["method"],payload["path"],status_code,payload["agent"],
              json.dumps(clean,sort_keys=True,separators=(",",":")),prev,digest))
            return {"sequence":cur.lastrowid,**payload,"sha256":digest}
    def verify_chain(self):
        prev="0"*64; count=0
        with self._db() as db: rows=db.execute("SELECT * FROM events ORDER BY seq").fetchall()
        for r in rows:
            p={"at":r["at"],"kind":r["kind"],"ip":r["ip"],"method":r["method"],"path":r["path"],
               "status":r["status"],"agent":r["agent"],"details":json.loads(r["details"]),"prev":r["prev"]}
            digest=hashlib.sha256(json.dumps(p,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
            if r["prev"]!=prev or r["digest"]!=digest:
                return {"valid":False,"verified_events":count,"failed_sequence":r["seq"]}
            prev=digest; count+=1
        return {"valid":True,"verified_events":count,"head_hash":prev}
    def export_json(self):
        with self._db() as db: rows=db.execute("SELECT * FROM events ORDER BY seq").fetchall()
        return {"schema_version":1,"generated_at":datetime.now(timezone.utc).isoformat(),
          "integrity":self.verify_chain(),"events":[{"sequence":r["seq"],"timestamp":r["at"],
          "event_type":r["kind"],"source_ip":r["ip"],"method":r["method"],"path":r["path"],
          "status_code":r["status"],"user_agent":r["agent"],"details":json.loads(r["details"]),
          "previous_hash":r["prev"],"sha256":r["digest"]} for r in rows],
          "notice":"Server-observed technical records; IP addresses do not establish a person's identity."}
