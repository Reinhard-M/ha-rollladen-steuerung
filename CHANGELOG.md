# Changelog

## 1.10.6

* Repairs: the dialog now says why an entity counts as missing ("does not exist" or "disabled (device or integration switched off)").
* If the same entity is confirmed again, the result says "unchanged, still disabled" instead of "entity → same entity", with a hint how to enable it or pick another one. The notice stays until the entity is usable.

## 1.10.5

* Repairs: the dialog no longer ends with a bare "The problem is fixed!". If the reported entities exist again, it now says which instance it was about and that there was nothing to repair; entities that exist but are only "unavailable" are listed (this is not a missing entity).
* After replacing entities, a confirmation names the instance and shows what was changed (old entity → new entity).

## 1.10.4

* Start lock after a Home Assistant start: drive commands wait until HA is running, the cover is available and (with the combined Homematic control) `homematicip_local.put_paramset` exists, at most 5 minutes. Prevents lost commands and the "Referenced entities … are missing" / "Action homematicip_local.put_paramset not found" warnings during startup.
* `homematicip_local` added to `after_dependencies`, so the integration is set up after the Homematic integration when both are present.

## 1.10.3

* The settings dialog now shows the name of the service instance ("Dienst: …") at the top, so it is clear which control is being edited.

## 1.10.2

* Version alignment: the manifest now matches the release tag (v1.10.1 was tagged with manifest version 1.10.0).
* CI: the HACS action runs without ignored checks (required for the HACS default list).

## 1.10.0

* Renamed entities are followed automatically: the new entity ID is taken over into the settings, also for renames while the instance was not loaded (registry ID is stored).
* Missing or disabled entities are reported under Settings → Repairs, with a dialog to pick a replacement.
* Diagnostic sensor shows "Konfigurationsfehler, Entität fehlt: …" and the new attributes `mypos_taster` / `fehlende_entitäten`.
* Missing MyPosition button: automatic drives fall back to the configured position (warning in the log and a note in the command log) instead of silently sending nothing.

## 1.9.3

* Help icon (?) in the Lovelace card and README link in the settings dialogs.
* English code comments; repository prepared for GitHub and HACS (license, disclaimer, workflows, tests).
