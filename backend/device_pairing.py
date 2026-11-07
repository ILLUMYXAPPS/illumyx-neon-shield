"""Server-authoritative, one-time device pairing for Neon Shield."""
from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from auth_server import AuthenticationError
from auth_server_contract import AuthFailure
from backend.store import _hash, verify_secret
from backend.device_limits import DeviceAllowance, DeviceLimitPolicy


class DevicePairingRepository:
    """Pairing persistence shared by SQLite and managed DB-API auth stores."""

    def __init__(self, store):
        self.store = store
        self.pepper = getattr(store, 'pepper', getattr(store, '_pepper', ''))
        if not self.pepper:
            raise RuntimeError('device pairing requires the deployment auth pepper')

    def _connection(self):
        if hasattr(self.store, '_db'):
            return self.store._db, False
        return self.store._connection_factory(), True

    def _sql(self, query):
        return query.replace('?', getattr(self.store, '_placeholder', '?'))

    def _migrate(self):
        connection, close = self._connection()
        cursor = connection.cursor()
        try:
            cursor.execute('CREATE TABLE IF NOT EXISTS device_pairing_requests (request_id TEXT PRIMARY KEY, subject_id TEXT NOT NULL, device_hash TEXT NOT NULL, device_name TEXT NOT NULL, secret_hash TEXT NOT NULL, code_hash TEXT NOT NULL, status TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL, expires_at TEXT NOT NULL)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_pairing_subject ON device_pairing_requests(subject_id, status)')
            cursor.execute('CREATE TABLE IF NOT EXISTS device_labels (subject_id TEXT NOT NULL, device_hash TEXT NOT NULL, device_name TEXT NOT NULL, updated_at TEXT NOT NULL, PRIMARY KEY(subject_id, device_hash))')
            connection.commit()
        finally:
            cursor.close()
            if close: connection.close()

    def _begin(self, connection):
        # SQLite needs an explicit write reservation before reading the pairing
        # request or allowance counts. This applies to both the in-memory AuthStore
        # and managed SQLite adapters. Server databases use their row-locking
        # transaction semantics and the resolver locks the household owner row.
        if hasattr(self.store, '_db') or getattr(self.store, '_placeholder', None) == '?':
            connection.execute('BEGIN IMMEDIATE')

    def _row_dict(self, cursor, row):
        if row is None: return None
        if isinstance(row, dict): return row
        return dict(zip([column[0] for column in cursor.description], row, strict=False))

    def create_request(self, subject_id, device_id, device_name, request_id, secret_hash, code_hash, created_at, expires_at):
        connection, close = self._connection(); cursor = connection.cursor()
        try:
            cursor.execute(self._sql('INSERT INTO device_pairing_requests(request_id,subject_id,device_hash,device_name,secret_hash,code_hash,status,attempts,created_at,expires_at) VALUES(?,?,?,?,?,?,\'pending\',0,?,?)'), (request_id, subject_id, _hash(device_id, self.pepper), device_name, secret_hash, code_hash, created_at, expires_at))
            connection.commit()
        finally:
            cursor.close()
            if close: connection.close()

    def status(self, request_id, secret_hash, now):
        connection, close = self._connection(); cursor = connection.cursor()
        try:
            cursor.execute(self._sql('SELECT request_id, status, expires_at FROM device_pairing_requests WHERE request_id=? AND secret_hash=?'), (request_id, secret_hash))
            row = self._row_dict(cursor, cursor.fetchone())
            if row is None: raise AuthenticationError(AuthFailure.INVALID_CREDENTIALS)
            if datetime.fromisoformat(row['expires_at']) <= now and row['status'] == 'pending':
                cursor.execute(self._sql('UPDATE device_pairing_requests SET status=\'expired\' WHERE request_id=? AND status=\'pending\''), (request_id,)); connection.commit()
                return 'expired'
            return row['status']
        finally:
            cursor.close()
            if close: connection.close()

    def _append_audit_fingerprint(self, connection, event_type, subject_id, device_fingerprint, occurred_at):
        """Append an audit event using the caller's transaction and connection."""
        cursor = connection.cursor()
        try:
            lock = getattr(self.store, '_audit_lock_clause', '')
            # Serialize audit-chain writers on the stable singleton row. The
            # pairing transaction already owns this connection, so a failure
            # here also rolls back the device approval.
            cursor.execute(self._sql('UPDATE audit_chain_head SET event_hash=event_hash WHERE chain_id=1'))
            cursor.execute(self._sql('SELECT event_hash FROM audit_chain_head WHERE chain_id=1' + lock))
            row = cursor.fetchone()
            if row is None:
                raise RuntimeError('audit chain head is missing; run migrations')
            previous_hash = row[0] if not isinstance(row, dict) else row['event_hash']
            event_hash = hashlib.sha256(
                f"{event_type}|{occurred_at}|{subject_id or ''}|{device_fingerprint}|{previous_hash}".encode()
            ).hexdigest()
            cursor.execute(
                self._sql('INSERT INTO audit_events(event_hash,event_type,occurred_at,subject_id,device_fingerprint,previous_hash) VALUES(?,?,?,?,?,?)'),
                (event_hash, event_type, occurred_at, subject_id, device_fingerprint, previous_hash),
            )
            cursor.execute(
                self._sql('UPDATE audit_chain_head SET event_hash=? WHERE chain_id=1'),
                (event_hash,),
            )
            if getattr(cursor, 'rowcount', 1) != 1:
                raise RuntimeError('audit chain head update did not affect exactly one row')
            return event_hash
        finally:
            cursor.close()

    def approve(self, request_id, subject_id, code_hash, now, allowance=None, allowance_resolver=None, audit_fingerprint=None):
        connection, close = self._connection(); cursor = connection.cursor()
        try:
            self._begin(connection)
            lock = getattr(self.store, '_audit_lock_clause', '')
            cursor.execute(self._sql('SELECT subject_id, device_hash, device_name, code_hash, status, attempts, expires_at FROM device_pairing_requests WHERE request_id=?' + lock), (request_id,))
            row = self._row_dict(cursor, cursor.fetchone())
            if row is None or row['subject_id'] != subject_id or row['status'] != 'pending':
                connection.rollback(); raise AuthenticationError(AuthFailure.INVALID_CREDENTIALS)
            if datetime.fromisoformat(row['expires_at']) <= now:
                cursor.execute(self._sql('UPDATE device_pairing_requests SET status=\'expired\' WHERE request_id=?'), (request_id,)); connection.commit()
                raise AuthenticationError(AuthFailure.EXPIRED_SESSION)
            if int(row['attempts']) >= 5:
                connection.rollback(); raise AuthenticationError(AuthFailure.RATE_LIMITED)
            valid = hmac.compare_digest(row['code_hash'], code_hash or '')
            if not valid:
                cursor.execute(self._sql('UPDATE device_pairing_requests SET attempts=attempts+1 WHERE request_id=?'), (request_id,)); connection.commit()
                raise AuthenticationError(AuthFailure.INVALID_CREDENTIALS)
            # Resolve authoritative entitlements and device counts while the pairing
            # approval transaction is holding its database lock. Production resolvers
            # should implement resolve_for_approval(connection, subject_id, request_id)
            # so the trusted-device counts are read from this same transaction.
            if allowance_resolver is not None:
                transactional_resolver = getattr(allowance_resolver, 'resolve_for_approval', None)
                if transactional_resolver is None:
                    connection.rollback()
                    raise RuntimeError('device allowance resolver must support transactional approval')
                allowance = transactional_resolver(connection, subject_id, request_id)
            if allowance is not None:
                if not isinstance(allowance, DeviceAllowance):
                    connection.rollback()
                    raise RuntimeError('device allowance resolver returned invalid data')
                DeviceLimitPolicy.assert_can_add_device(allowance)
            cursor.execute(self._sql('UPDATE device_pairing_requests SET status=\'approved\' WHERE request_id=? AND status=\'pending\''), (request_id,))
            if getattr(cursor, 'rowcount', 1) != 1:
                connection.rollback(); raise AuthenticationError(AuthFailure.INVALID_CREDENTIALS)
            cursor.execute(self._sql('INSERT INTO devices(subject_id,device_hash,trusted,created_at) VALUES(?,?,1,?) ON CONFLICT(subject_id,device_hash) DO UPDATE SET trusted=1,created_at=excluded.created_at'), (subject_id, row['device_hash'], now.isoformat()))
            cursor.execute(self._sql('INSERT INTO device_labels(subject_id,device_hash,device_name,updated_at) VALUES(?,?,?,?) ON CONFLICT(subject_id,device_hash) DO UPDATE SET device_name=excluded.device_name,updated_at=excluded.updated_at'), (subject_id, row['device_hash'], row['device_name'], now.isoformat()))
            if audit_fingerprint is not None:
                self._append_audit_fingerprint(
                    connection,
                    'device_pairing_approved',
                    subject_id,
                    audit_fingerprint,
                    datetime.now(timezone.utc).isoformat(),
                )
            connection.commit()
            return row['device_hash']
        except Exception:
            # The transaction may already have been committed for expected failures.
            try: connection.rollback()
            except Exception: pass
            raise
        finally:
            cursor.close()
            if close: connection.close()

    def list_devices(self, subject_id):
        connection, close = self._connection(); cursor = connection.cursor()
        try:
            cursor.execute(self._sql('SELECT d.device_hash, d.created_at, COALESCE(l.device_name, \'Neon Shield device\') AS device_name FROM devices d LEFT JOIN device_labels l ON l.subject_id=d.subject_id AND l.device_hash=d.device_hash WHERE d.subject_id=? AND d.trusted=1 ORDER BY d.created_at'), (subject_id,))
            rows = [self._row_dict(cursor, row) for row in cursor.fetchall()]
            return [{'device_ref': hmac.new(self.pepper.encode(), ('device-ref:' + row['device_hash']).encode(), hashlib.sha256).hexdigest()[:24], 'device_name': row['device_name'], 'added_at': row['created_at']} for row in rows]
        finally:
            cursor.close()
            if close: connection.close()

    def rename_device(self, subject_id, device_ref, name):
        devices = self._device_rows(subject_id)
        match = next((row for row in devices if hmac.compare_digest(self._ref(row['device_hash']), device_ref)), None)
        if match is None: raise AuthenticationError(AuthFailure.INVALID_CREDENTIALS)
        connection, close = self._connection(); cursor = connection.cursor()
        try:
            cursor.execute(self._sql('INSERT INTO device_labels(subject_id,device_hash,device_name,updated_at) VALUES(?,?,?,?) ON CONFLICT(subject_id,device_hash) DO UPDATE SET device_name=excluded.device_name,updated_at=excluded.updated_at'), (subject_id, match['device_hash'], name, datetime.now(timezone.utc).isoformat()))
            connection.commit()
        finally:
            cursor.close()
            if close: connection.close()

    def unlink_device(self, subject_id, device_ref):
        devices = self._device_rows(subject_id)
        match = next((row for row in devices if hmac.compare_digest(self._ref(row['device_hash']), device_ref)), None)
        if match is None: raise AuthenticationError(AuthFailure.INVALID_CREDENTIALS)
        connection, close = self._connection(); cursor = connection.cursor()
        try:
            self._begin(connection)
            cursor.execute(self._sql('UPDATE devices SET trusted=0 WHERE subject_id=? AND device_hash=?'), (subject_id, match['device_hash']))
            cursor.execute(self._sql('UPDATE sessions SET revoked=1 WHERE subject_id=? AND device_hash=? AND revoked=0'), (subject_id, match['device_hash']))
            connection.commit()
        except Exception:
            connection.rollback(); raise
        finally:
            cursor.close()
            if close: connection.close()

    def _device_rows(self, subject_id):
        connection, close = self._connection(); cursor = connection.cursor()
        try:
            cursor.execute(self._sql('SELECT device_hash FROM devices WHERE subject_id=? AND trusted=1'), (subject_id,))
            return [self._row_dict(cursor, row) for row in cursor.fetchall()]
        finally:
            cursor.close()
            if close: connection.close()

    def _ref(self, device_hash):
        return hmac.new(self.pepper.encode(), ('device-ref:' + device_hash).encode(), hashlib.sha256).hexdigest()[:24]


class DevicePairingService:
    REQUEST_TTL = timedelta(minutes=5)
    STATUS_RATE_WINDOW_SECONDS = 60
    MAX_STATUS_POLLS_PER_WINDOW = 30

    def __init__(self, identity_service):
        self.identity_service = identity_service
        self.allowance_resolver = getattr(identity_service, 'device_allowance_resolver', None)
        import os
        if os.environ.get('NEON_AUTH_ENV') == 'production':
            if self.allowance_resolver is None:
                raise RuntimeError('production device pairing requires a verified device allowance resolver')
            if not callable(getattr(self.allowance_resolver, 'resolve_for_approval', None)):
                raise RuntimeError('production device allowance resolver must support transactional approval')
        self.store = identity_service.store
        self.repository = DevicePairingRepository(self.store)
        self.pepper = self.repository.pepper

    def start(self, identity, credential, device_id, device_name):
        identity = identity.strip().lower()
        if not identity or len(identity) > 320 or not credential or not device_id or len(device_id) > 512:
            raise AuthenticationError(AuthFailure.INVALID_CREDENTIALS)
        if not isinstance(device_name, str) or not device_name.strip() or len(device_name.strip()) > 48:
            raise ValueError('invalid device name')
        if self.identity_service._rate_limited(identity):
            raise AuthenticationError(AuthFailure.RATE_LIMITED)
        user = self.store.find_user(identity)
        if user is None or not verify_secret(credential, user['credential_record']):
            raise AuthenticationError(AuthFailure.INVALID_CREDENTIALS)
        subject_id = user['subject_id']
        if self.store.identity_blocked(subject_id):
            raise AuthenticationError(AuthFailure.BLOCKED_IDENTITY)
        now = datetime.now(timezone.utc)
        request_id = secrets.token_urlsafe(18)
        secret = secrets.token_urlsafe(32)
        code = f'{secrets.randbelow(1_000_000):06d}'
        secret_hash = hmac.new(self.pepper.encode(), ('pair-secret:' + secret).encode(), hashlib.sha256).hexdigest()
        code_hash = hmac.new(self.pepper.encode(), ('pair-code:' + code).encode(), hashlib.sha256).hexdigest()
        expires = now + self.REQUEST_TTL
        self.repository.create_request(subject_id, device_id, device_name.strip(), request_id, secret_hash, code_hash, now.isoformat(), expires.isoformat())
        self.identity_service._clear_failures(identity)
        self.store.add_audit_fingerprint('device_pairing_started', subject_id, _hash(device_id, self.pepper))
        return {'request_id': request_id, 'pairing_code': code, 'pairing_secret': secret, 'expires_at': expires.isoformat(), 'poll_interval_seconds': 3}

    def status(self, request_id, secret):
        if not isinstance(request_id, str) or not isinstance(secret, str) or len(request_id) > 128 or len(secret) > 128:
            raise AuthenticationError(AuthFailure.INVALID_CREDENTIALS)
        secret_hash = hmac.new(self.pepper.encode(), ('pair-secret:' + secret).encode(), hashlib.sha256).hexdigest()
        now = datetime.now(timezone.utc)
        status = self.repository.status(request_id, secret_hash, now)
        allowed = self.store.reserve_sign_in_attempt(
            'device-pairing-status:' + request_id,
            now.isoformat(),
            self.STATUS_RATE_WINDOW_SECONDS,
            self.MAX_STATUS_POLLS_PER_WINDOW,
        )
        if not allowed:
            raise AuthenticationError(AuthFailure.RATE_LIMITED)
        return status

    def _verified_session(self, session):
        return self.identity_service.resolve_session(session.session_id)

    def approve(self, session, request_id, pairing_code):
        session = self._verified_session(session)
        if not isinstance(request_id, str) or not request_id or len(request_id) > 128:
            raise AuthenticationError(AuthFailure.INVALID_CREDENTIALS)
        if not isinstance(pairing_code, str) or not pairing_code.isdigit() or len(pairing_code) != 6:
            raise AuthenticationError(AuthFailure.INVALID_CREDENTIALS)
        code_hash = hmac.new(self.pepper.encode(), ('pair-code:' + pairing_code).encode(), hashlib.sha256).hexdigest()
        self.repository.approve(
            request_id,
            session.subject_id,
            code_hash,
            datetime.now(timezone.utc),
            allowance_resolver=self.allowance_resolver,
            audit_fingerprint=session.device_id,
        )
        return {'status': 'approved'}

    def devices(self, session):
        session = self._verified_session(session)
        return self.repository.list_devices(session.subject_id)

    def rename(self, session, device_ref, device_name):
        session = self._verified_session(session)
        if not isinstance(device_name, str) or not device_name.strip() or len(device_name.strip()) > 48:
            raise ValueError('invalid device name')
        self.repository.rename_device(session.subject_id, device_ref, device_name.strip())

    def unlink(self, session, device_ref):
        session = self._verified_session(session)
        own_ref = self.repository._ref(session.device_id)
        if hmac.compare_digest(own_ref, device_ref):
            raise ValueError('current device cannot unlink itself')
        self.repository.unlink_device(session.subject_id, device_ref)
        self.store.add_audit_fingerprint('device_unlinked', session.subject_id, session.device_id)