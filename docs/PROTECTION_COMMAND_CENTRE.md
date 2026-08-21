# Protection Command Centre

The Protection Command Centre is the UI-neutral control layer for Neon Shield.

It exposes a common dashboard state for every protection profile:

- Protected file count
- Scan count
- Candidate count
- High-priority count
- Recent match records
- Alerts
- Active protection profile and evidence types

The command centre does not perform remote-device access, collect credentials,
make legal infringement determinations, or submit automated claims. UI clients
can render the same snapshot on iOS, web, or desktop.
