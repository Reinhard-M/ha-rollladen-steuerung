# Changelog

## 1.10.1

* Start lock after a Home Assistant start: drive commands wait until HA is running, the cover is available and (with the combined Homematic control) `homematicip_local.put_paramset` exists, at most 5 minutes. Prevents lost commands and the "Referenced entities … are missing" / "Action homematicip_local.put_paramset not found" warnings during startup.
* `homematicip_local` added to `after_dependencies`, so the integration is set up after the Homematic integration when both are present.

## 1.10.0

* Renamed entities are followed automatically: the new entity ID is taken over into the settings, also for renames while the instance was not loaded (registry ID is stored).
* Missing or disabled entities are reported under Settings → Repairs, with a dialog to pick a replacement.
* Diagnostic sensor shows "Konfigurationsfehler, Entität fehlt: …" and the new attributes `mypos_taster` / `fehlende_entitäten`.
* Missing MyPosition button: automatic drives fall back to the configured position (warning in the log and a note in the command log) instead of silently sending nothing.

## 1.9.3

* Help icon (?) in the Lovelace card and README link in the settings dialogs.
* English code comments; repository prepared for GitHub and HACS (license, disclaimer, workflows, tests).
