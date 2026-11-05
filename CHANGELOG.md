# Changelog

## 1.10.9

* Drives caused by a window contact (night: ventilation height, opening, closing, and the catch-up after the lock-out protection) now start immediately. The *automatic drive delay* only applies to timer-driven automatic drives (day/night change, shading, release of a block), which can happen at the same time on several shutters.
* An automatic drive that was still waiting for the drive delay is no longer lost when Home Assistant restarts or the integration is reloaded. It is stored and made up after the start if it is at most 30 minutes old, the phase (day/night) is unchanged and it was not a shading drive.
* README: the delay description mentions that contact drives are never delayed.

## 1.10.8

* Card: the drive times (morning/evening) are now HTML-escaped. A text sensor chosen as drive-time source can no longer inject markup into the dashboard.
* README: new introduction; installation section moved in front of the setup and now leads with the Marketplace / HACS search (including the "Open Marketplace repository" button) and keeps the custom repository steps as a fallback.

## 1.10.7

* The drive times shown in the card (and in the input sensors "Drive time morning/evening") now include the *automatic drive delay*, so they show when the shutter really starts moving. The time of the schedule itself stays available in the attribute `rohwert`.

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
