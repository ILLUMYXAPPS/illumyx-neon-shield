# Match Report Schema

Every scanner candidate should produce one auditable record with these fields:

- `candidate_id`: stable identifier for the candidate.
- `score`: deterministic overall match score.
- `evidence`: per-signal evidence such as audio, lyrics, artwork, and metadata.
- `status`: review outcome, such as `confirmed_match` or `false_positive`.
- `audit`: decision history containing the reviewer decision and reason.

## Canonical flow

`Candidate -> Score -> Evidence -> Review -> Decision -> Audit`

The transcript must preserve the scanner score and original evidence when a human decision is applied. This keeps the release testable and gives investigators a single evidence trail rather than separate fragments.
