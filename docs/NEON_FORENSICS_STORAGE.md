# Neon Forensics storage model

## Goals

- Evidence is encrypted before being written to local disk.
- Evidence is never uploaded by the vault.
- The encryption key is supplied by an approved key-management layer; Neon Forensics does not persist plaintext keys.
- Retention is explicit and classification-aware.
- Collection pauses when local free space falls below the configured safety threshold.

## Default retention

| Classification | Default retention |
|---|---:|
| SAFE_TO_COLLECT | 30 days |
| CONSENT_REQUIRED | 90 days |
| USER_SUBMITTED | 90 days |
| DO_NOT_COLLECT | never stored |

These are product defaults, not legal retention requirements. A deployment must configure retention to its applicable privacy, contractual and operational requirements.

## Encryption

`EvidenceVault` uses AES-256-GCM with a fresh 96-bit nonce per evidence item. Associated authenticated data binds the ciphertext to the evidence ID, classification and content type. Tampering causes decryption failure.

The vault accepts only a 32-byte key. Production integrations must obtain that key from an OS-backed or enterprise-approved secret/key-management mechanism. Do not commit keys, put them in source control, or store them beside the evidence files.

## Collection boundary

The vault is storage only. It does not grant collectors permission to access data. All observations must pass the Neon Forensics deny-by-default policy before they reach the vault.

## Export

Forensic exports should include the incident JSON and manifest. Raw encrypted evidence remains local unless the user explicitly chooses an approved export destination.
