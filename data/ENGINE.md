# Engine data

No synthetic data is bundled into the real engine. Run `python -m core.sync` to
derive a snapshot from the supplied kit, including organiser workbooks. The dashboard may fall back
to Agent B's mocks when a real function is unavailable.

Add source mappings to `config/sources.yaml`, then run `python -m core.sync`.
Supported local formats: CSV, Excel and JSON records. `column_map` maps incoming
column names to standard names; `defaults` supplies verified constant metadata.
Only aggregate rows may be mapped. Do not map trade names or licence identifiers
to `group`. Snapshot replacement requires valid, finite, unique standard rows.

Runtime state lives under `data/cache/` (or `RASED_DATA_DIR`): snapshots, manifest,
fingerprints, sync status, acknowledgements and changelog. Keep the last good
cache for offline use. `data/audit.log` records exports, sync and acknowledgements.
