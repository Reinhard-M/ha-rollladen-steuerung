# Rollladen Steuerung

*English version: [README.en.md](README.en.md)*

![Karte Rollladen Steuerung](docs/karte.png)

Verbindet **Tag/Nacht** (z. B. aus „Rollladen Zeiten“), Sensoren und einen Fensterkontakt mit einem **cover**-Rollo.
Eine Instanz je Rollo (Einstellungen → Geräte & Dienste → „Rollladen Steuerung“ hinzufügen). Beim Anlegen werden nur Rollo und Eingangsentitäten gewählt, **alle Werte sind danach Entitäten des Geräts** (bleiben nach Neustart erhalten). Position: 0 % = zu, 100 % = offen (wie in HA).

## Einrichtung (Eingänge beim Anlegen der Instanz)

**Pflicht** sind nur *Rollo* und *Tag bzw. Tag/Nacht*. Alles andere ist **optional**; was fehlt, wird einfach nicht ausgewertet (z. B. kein Helligkeitssensor = die Helligkeitsbedingung der Beschattung entfällt) und die zugehörigen Entitäten/Spalten erscheinen nicht.

| Feld | Pflicht? | Hinweis |
|---|---|---|
| Rollo (cover) | **Pflicht** | Das zu steuernde Rollo/die Jalousie |
| Tag bzw. Tag/Nacht | **Pflicht** | **Ein** Eintrag: Binärsensor (`on` = Tag) oder Sensor (`day`/`tag` = Tag, `night`/`nacht` = Nacht). Tag/Nacht erzeugt die separate Integration **[Rollladen Zeiten](https://github.com/Reinhard-M/ha-rollladen-zeiten)** (Sensor *Tag* bzw. *Tag/Nacht*, aus Sonnenstand, Zeitgrenzen und freien Tagen); es funktioniert aber jede andere Quelle |
| Gerätetyp | Vorgabe *Fenster* | Fenster, Tür oder Markise. *Tür*: Aussperrschutz standardmäßig an, in der Karte als Tür dargestellt. *Markise*: eigenes Tag/Nacht-Verhalten (siehe Abschnitt *Markise*), in der Karte als Markise dargestellt. Wird der Typ geändert, werden diese Vorgaben neu gesetzt |
| Positionsquelle | Vorgabe aus den Fähigkeiten des Rollos | *Vom Gerät* (set_cover_position/current_position) oder *Intern* (Schätzung aus Laufzeiten). **Nur bei *Intern* gibt es Laufzeiten und Kalibrierung** |
| Lamellen verwenden | Vorgabe aus den Fähigkeiten | Lamellen werden per `set_cover_tilt_position` (0–100 %) gesetzt. **Aus = alle Lamellen-Entitäten entfallen** |
| Fensterkontakt | optional | Entität mit Text-Zustand; die Zustandswörter für offen/gekippt/geschlossen sind einstellbar (Komma-Liste, Standard `open,on` / `tilted,tilt` / `closed,off`). Ohne Kontakt gilt immer „geschlossen“ |
| Helligkeit, Außentemperatur, Zimmertemperatur | optional | Sensoren; nicht gewählt = Bedingung der Beschattung entfällt |
| Sonne Elevation / Azimut | optional | Sensoren oder `sun.sun` (Attribute); nicht gewählt = Bedingung entfällt |
| Externes Kommando | optional | Sensor, dessen Zustand als Kommando ausgeführt wird; jede Zustandsänderung löst es aus. Alle Kommandos siehe Abschnitt *Externes Kommando* |
| Extern blockieren | optional | **Binärer** Eingang (`binary_sensor`, `input_boolean`, `switch`, Sensor): `on`/`true` sperrt die Automatik, `off`/`false` gibt sie frei. Siehe Abschnitt *Automatik sperren* |
| Fahrzeit morgens/abends | optional | Nur Anzeige in der Karte: Sensor mit Uhrzeit (z. B. „Rollladen Zeiten“) |
| MyPosition-Taster am Gerät | optional | Button/Schalter/Skript, das die MyPosition (Zwischenstellung) des Motors anfährt. **Leer = kein Taster *MyPosition* und keine Auswahl *MyPosition* in den Einstellungen** |
| Homematic-Gerät / Kanal | optional | Siehe Abschnitt *Jalousien und Lamellen* |

## Einstellungen (Entitäten des Geräts)

Alle Werte sind Entitäten des Geräts und bleiben nach einem Neustart erhalten. Die Vorgaben sind so gewählt, dass die Steuerung ohne Anpassung sinnvoll läuft; „nur wenn“ nennt die Voraussetzung, unter der die Entität überhaupt angelegt wird.

| Einstellung | Vorgabe | Wirkung / nur wenn |
|---|---|---|
| Nacht Fenster offen / geschlossen / gekippt (Position) | 100 / 0 / 20 % | Zielhöhe der Nacht je Kontaktzustand. **Entfällt bei Markisen** (dort fest: einfahren) |
| Nacht … Art (je Kontaktzustand) | Position | Position oder MyPosition; nur wenn ein MyPosition-Taster konfiguriert ist |
| Tag Höhe / Tag Höhe Art | 100 % / Position | Ziel beim Wechsel auf Tag; die Art nur mit MyPosition-Taster |
| Beschattung Höhe / Beschattung Art | 30 % (Markise 0 %) / Position | Ziel der Beschattung; die Art nur mit MyPosition-Taster |
| Beschattung Elevation min. | 10 ° | Sonne muss mindestens so hoch stehen |
| Beschattung Azimut von / bis | 90 ° / 270 ° | Sonne muss in diesem Bereich stehen (auch über Norden) |
| Beschattung Außentemp. / Zimmertemp. min. | 20 / 22 °C | nur wenn der jeweilige Sensor konfiguriert ist |
| Beschattung Helligkeit Start / Ende | 30000 / 20000 lx | nur mit Helligkeitssensor; Ende < Start vermeidet Flattern |
| Beschattung Ende-Verzögerung | 300 s | So lange muss eine Bedingung verletzt sein, bevor die Beschattung endet |
| Beschattung Ende | vorherige Position | Danach auf vorherige Position oder Tagesposition |
| Nachhol-Verzögerung | 30 s | Wartezeit, bevor eine vom Aussperrschutz zurückgehaltene Fahrt nachgeholt wird |
| **Fahrverzögerung automatisch** | 0 s (aus) | Verzögert jede **automatische** Fahrt (siehe Logik); manuelle nie |
| Lamellen Nacht (offen/geschlossen/gekippt) / Beschattung / Tag | 100 / 0 / 50 / 50 / 100 % | nur mit *Lamellen verwenden* |
| Laufzeit runter / hoch | 30 s | nur bei Positionsquelle *Intern*; Kalibrierung möglich |
| MyPosition Höhe | 50 % | nur bei *Intern* mit MyPosition-Taster; Kalibrierung möglich |
| Schalter *Aussperrschutz* | aus (bei Typ *Tür* an) | siehe Logik |
| Schalter *Beschattung* | an | aus = keine Beschattung |
| Schalter *Automatik gesperrt* | aus | Sperrt die Automatik (Party-Modus). Ist der Eingang *Extern blockieren* konfiguriert, **folgt der Schalter dem Eingang** (beim Start und bei jeder Änderung) und lässt sich dazwischen von Hand überschreiben |
| Schalter *Fahrzeiten ausblenden* | aus | blendet Laufzeiten/Kalibrierung aus |

## Logik

**Nacht** (oberste Ebene): erlaubt nur die Fahrten aus den Einstellungen *Nacht Fenster offen / geschlossen / gekippt*. Jede davon ist **Position** (mit %-Wert) oder **MyPosition** – nur diese beiden Arten, kein Hoch/Runter. Es gelten nachts ausschließlich Nachtwerte, nie Beschattungswerte. Sie wird beim Wechsel auf Nacht und bei jeder Änderung des Fensterkontakts ausgeführt (unbekannter Kontakt = geschlossen). Mit Lamellen wird danach *Nacht Lamellen Fenster offen / geschlossen / gekippt* gesetzt.

**Aussperrschutz** (Schalter an; Vorgabe bei Gerätetyp *Tür* an, sonst aus): greift **nur**, wenn das Rollo **oben** ist, der Kontakt `open` meldet und eine **automatische** Fahrt beginnen würde. Diese Fahrt wird zurückgehalten. Meldet der Kontakt etwas anderes, wird sie nach der **Nachhol-Verzögerung** nachgeholt – und zwar zum dann **aktuell gültigen Ziel**, nicht zur ursprünglichen Position. Geht der Kontakt vorher wieder auf `open`, wird das Nachholen verworfen. Ist das Rollo nicht oben, wird normal gefahren.

**Tag**: Wechsel auf Tag fährt auf die **Tagesposition** (*Tag Höhe Art*: Position oder MyPosition, mit *Tag Höhe*), außer die Beschattung ist sofort fällig. **Beschattung** startet sofort, wenn **alle** konfigurierten Bedingungen erfüllt sind: Elevation ≥ Grenze, Azimut im Bereich von–bis (auch über Norden), Außentemperatur ≥, Zimmertemperatur ≥, Helligkeit ≥ *Start*. Sie fährt auf *Beschattung Höhe* oder (Einstellung *Beschattung Art* = MyPosition) auf die MyPosition. Fensterkontakte haben tagsüber keine Wirkung. Lamellen: *Beschattung Lamellen*, danach *Tag Lamellen*.

**Ende der Beschattung**: Ist **eine** Bedingung nicht mehr erfüllt (Helligkeit jetzt gegen den *Ende*-Wert), startet **ein** Timer (*Beschattung Ende-Verzögerung*). Sind wieder alle erfüllt, wird er zurückgesetzt. Läuft er ab, fährt das Rollo je nach *Beschattung Ende* auf die **vorherige Position** (vor der Beschattung; nach der Nacht = oben) oder auf die **Tagesposition** (*Beschattung Ende* = „Tagesposition“). Die Ziele werden dabei als Position angefahren.

**Fahrverzögerung automatisch** (Zahl, Sekunden, Vorgabe 0 = aus): verzögert jede **automatisch** erzeugte Fahrt (Tag/Nacht, Beschattung, Nachholen) um diese Zeit. Sinnvoll, damit sich Befehle bei „alle Rollos runter“ nicht stören – pro Rollo unterschiedliche Werte einstellen (z. B. 0, 2, 4 s …). Manuelle Fahrten (Taster, Zurück, Positions-/Lamellenänderung, Externes Kommando) werden **nie** verzögert. Kommt während der Wartezeit ein neues Ziel, ersetzt es das wartende.

**Markise** (Gerätetyp *Markise*): Die Steuerlogik ist dieselbe wie bei Rollos, also **100 % = eingefahren, 0 % = ausgefahren**. Das Tag/Nacht-Verhalten ist aber anders:

* **Nacht**: Mit Beginn der Nacht wird **eingefahren** (100 %). Nachts fährt die Automatik nie aus. Fensterkontakt und Aussperrschutz haben keine Wirkung, die Einstellungen *Nacht …*, *Lamellen* und *Aussperrschutz* entfallen.
* **Tag**: Der Wechsel auf Tag fährt **nichts**. Ausgefahren wird nur durch die **Beschattung** (Sonne, Helligkeit, Temperatur …) auf *Beschattung Höhe* (Vorgabe **0 %**, also ganz aus). Ist die Beschattung beim Tagesbeginn sofort fällig, fährt sie dann aus.
* **Ende der Beschattung** und Nachtbeginn fahren ein (je nach *Beschattung Ende* auf die vorherige Position oder die *Tag Höhe*, Vorgabe 100 %).
* Verzögerungen, *Zurück*, *MyPosition* und die Sperre der Automatik funktionieren wie bei Rollos. Die Wind-/Regensicherung ist nicht Teil der Integration; sie kann über das externe Kommando `up` und den Eingang *Extern blockieren* angebunden werden.

**Automatik sperren (Party-Modus, Wind/Regen)**: Ist der Schalter *Automatik gesperrt* an (er folgt dem Eingang *Extern blockieren*: `on`/`true` schaltet ihn ein, `off`/`false` aus; von Hand ist er jederzeit schaltbar, die nächste Änderung des Eingangs gilt wieder), fährt die Automatik **nicht**; manuelle Fahrten (Taster, externes Kommando) gehen weiter. Was die Automatik in der Zeit fahren wollte (Tag/Nacht, Beschattung, Kontaktänderung), wird **gemerkt**. Wenn die Sperre endet (Schalter aus, ob von Hand oder durch den Eingang), wird **einmal zum dann gültigen Ziel** gefahren (Fahrverzögerung und Aussperrschutz gelten dabei weiter). Wurde nichts zurückgehalten, bleibt das Rollo, wie es ist. Ist der Eingang `unknown`/`unavailable`, bleibt der letzte Zustand. Der Schalter bleibt nach einem Neustart erhalten; ist ein Eingang konfiguriert, wird er beim Start gelesen und gibt den Schalterzustand vor; *Fahrt verzögert* zeigt „Automatik gesperrt, Fahrt wartet auf Freigabe“. Beispiel Party: Rollos, die offen bleiben sollen, mit `up` öffnen und den Eingang auf `on` setzen, nach der Party auf `off`. Wind/Regen: Eingang über die eigene Wind-/Regenlogik schalten (z. B. `up` per Kommando, Eingang `on`; Ende der Sperre holt die dann gültige Automatik nach).

## Externes Kommando

Der beim Anlegen gewählte Sensor (z. B. ein `input_select`, Template-Sensor oder MQTT-Sensor) löst bei **jeder Zustandsänderung** ein Kommando aus (Groß-/Kleinschreibung egal). Es zählt als manuell: die Automatik bleibt unberührt, es gibt keine Fahrverzögerung.

| Zustand | Wirkung |
|---|---|
| `up` / `hoch`, `down` / `runter`, `stop` / `stopp` | Taster Hoch / Runter / Stopp |
| `mypos` / `shade` / `beschattung` | MyPosition anfahren |
| `back` / `zurück` | Zurück zur letzten automatischen Position |
| `position:40`, `position 40`, `pos=40`, `40`, `40 %` | **Position** 40 % anfahren (0–100; auch bei Rollos, mit Lamellen bleiben die aktuellen Lamellen) |

Hinweis: Wiederholt der Sensor denselben Zustand, entsteht keine Zustandsänderung und damit kein neues Kommando (z. B. zweimal hintereinander `position:40`).

**Manuelle Befehle** (Taster, Externes Kommando, direkt am Gerät) werden von der Automatik nicht beachtet und blockieren sie nicht. Die Automatik fährt nur bei einem **Ereignis** (Tag/Nacht-Wechsel, Kontakt, Beschattungsstart/-ende, Nachholen), sie prüft die Position nie regelmäßig. Wurde das Rollo während der Beschattung verstellt, fährt es deshalb erst am Ende der Beschattung wieder hoch.

**Zurück**: Der Taster *Zurück* (oder externes Kommando `back`/`zurück`) fährt nach einer manuellen Fahrt die zuletzt **automatisch** angefahrene Position der aktuellen Tageszeit (Nacht bzw. Tag/Beschattung) an. Der Aussperrschutz wirkt hier nicht.

**Fahrzeiten ausblenden**: Der Schalter *Fahrzeiten ausblenden* blendet Laufzeiten, MyPosition-Höhe und Kalibrierung in den Einstellungen aus (Entitätsregister „ausgeblendet“); wieder aus = sichtbar. Die Werte gelten weiter.

## Jalousien und Lamellen

Die Lamellensteuerung ist **nicht** auf Homematic beschränkt. Mit *Lamellen verwenden* wird die Lamellenstellung über die Standard-Funktion von Home Assistant `cover.set_cover_tilt_position` (0–100 %) gesetzt, die Höhe über `cover.set_cover_position`. Jede Jalousie, deren Integration diese beiden Funktionen anbietet (Z-Wave, Zigbee, KNX, Shelly, Somfy, Homematic usw.), lässt sich so mit individuellen Lamellenwerten ansteuern.

Nur das optionale Feld **Homematic-Gerät / Kanal** ist Homematic-spezifisch: Höhe und Lamellen werden dann in **einem** Befehl gesendet (`homematicip_local.put_paramset`, Datenpunkt `COMBINED_PARAMETER`, z. B. `L=50,L2=80`, Werte in Prozent), statt zwei getrennter Befehle. Das lohnt sich bei Aktoren wie dem HmIP-FBL, bei denen ein reiner Höhenbefehl die Lamellen zurücksetzt und es sonst zum Hin und Her von Höhe und Lamellen kommt. Leer lassen = zwei Befehle wie bei jeder anderen Jalousie. Bei anderen Herstellern mit demselben Problem gibt es das noch nicht; die Befehlsfolge ist dann Höhe, danach Lamellen.

## Positionsersatz und Kalibrierung (Quelle „Intern“)

Hat ein Rollo keine Positionsrückmeldung (oder ist sie zu ungenau), schätzt die Integration die Position aus Richtung und Laufzeit und stoppt Teilfahrten per Timer. Einstellregister: *Laufzeit runter* und *Laufzeit hoch* (jeweils für den ganzen Weg 100 % ↔ 0 %), *MyPosition Höhe* (geschätzte Höhe der MyPosition, Standard 50 %).

Werte von Hand eintragen **oder** per Kalibrierung: Auswahl **Kalibrierung** auf *1 Runter* setzen (die Schritte laufen nacheinander durch) und die Taster **Hoch / Runter / MyPosition / Stopp** benutzen. Jede Messung endet mit **Stopp**.

| Schritt | Ausgangslage | Start mit | Stopp bei | Ergebnis |
|---|---|---|---|---|
| 1 Runter | oben | Runter oder MyPosition | unten | *Laufzeit runter* |
| 2 Hoch | unten | Hoch oder MyPosition | oben | *Laufzeit hoch* |
| 3 MyPosition (nur mit MyPosition-Taster) | oben | MyPosition | sobald der Motor von selbst anhält | *MyPosition Höhe* |

Start und Ende jeder Messung richten sich nach den Fahrtmeldungen des Geräts (`opening`/`closing` bis `open`/`closed`), sofern es sie liefert. So zählt weder die Verzögerung eines langen MyPosition-Tastendrucks noch die Reaktionszeit beim Stopp. Fehlen die Meldungen, zählen Tastendruck und *Stopp*. Schritt 3 berechnet die Höhe der MyPosition aus der gemessenen Zeit und der *Laufzeit runter* (Schritt 1 muss also vorher erfolgt sein). Der Motor hält an der MyPosition selbst an – *Stopp* so schnell wie möglich drücken, denn die Reaktionszeit geht in das Ergebnis ein (1 s ≈ 5 % bei 20 s Laufzeit); zur Kontrolle ggf. wiederholen. Danach springt die Auswahl auf *Aus*. Meldet das Rollo selbst `closing → closed` bzw. `opening → open`, endet die Messung auch ohne *Stopp*. Ein Hinweistext steht im Attribut `hint` der Auswahl. Wegen der Latenz zwischen Befehl und Fahrtbeginn lohnt es sich, die Messung mehrfach zu wiederholen.

## Weitere Entitäten

* **Externes Kommando**: wird von dem beim Anlegen gewählten Sensor gespeist (siehe Abschnitt *Externes Kommando*), keine eigene Auswahl am Gerät.
* **Diagnose** (Kategorie Diagnose, im Gerät unter „Diagnose“):
  * *Eingang Tag / Fensterkontakt / Helligkeit / Außentemperatur / Zimmertemperatur / Elevation / Azimut / Externes Kommando / Extern blockieren*: jeweils der Wert, den die Steuerung gerade vom Eingang liest (Attribute: Quelle, Rohwert). Nur für konfigurierte Eingänge.
  * *Fahrt verzögert*: z. B. „Beschattung endet in 120 s“, „Nachholen in 20 s“ oder „Fahrt zurückgehalten (Aussperrschutz, wartet auf Kontakt)“, „Automatische Fahrt in 3 s“, sonst „keine“; Attribut `faellig_um`.
  * *Letzter Befehl*: der zuletzt an das Rollo gesendete Befehl mit Uhrzeit und **Auslöser** (z. B. „Kontakt closed -> tilted: cover.set_cover_position position=20“); Attribut `protokoll` = die letzten 12 Befehle. Taucht am Rollo ein Befehl auf, der hier fehlt, kommt er nicht von dieser Integration.
  * *Diagnose*: `ok` oder fehlende Eingänge; die Attribute enthalten zusätzlich alle Rohwerte, Bedingungen und Zustände.
* Taster *Hoch, Runter, Stopp, Zurück* (und *MyPosition*, wenn ein MyPosition-Taster konfiguriert ist), Sensor *Zustand* (Nacht / Tag / Beschattung / Beschattung endet, Attribute mit den Einzelbedingungen), Zahl *Position* (Ist-Wert, Setzen = manuelle Positionsfahrt) und bei Lamellen *Lamellen*, Binärsensor *Beschattung aktiv*, Schalter *Beschattung* (aus = keine Beschattung).

## Lovelace-Karte „Rollladen Steuerung“

![Karte Rollladen Steuerung](docs/karte.png)

**Was der Screenshot zeigt** (von oben nach unten):

| Zeile | Zeigt |
|---|---|
| Info-Zeile | Uhrzeit, Außentemperatur, Helligkeit, Sonnenhöhe/Azimut (optional, Entitäten im Karteneditor wählbar) |
| Wohnzimmer | Tag: **grünes** Symbol, Rollo oben, Taster *MyPosition* vorhanden |
| Terrasse | **Rotes** Symbol mit Pfeil: Rollo **fährt gerade** (Pfeil nach unten = runter, nach oben = hoch) |
| Esszimmer Jalousie | Beschattung: **gelbes**, ruhendes Symbol; Jalousie mit *Lamellen*-Auswahl neben dem MyPosition-Taster (gemeinsame Spalte *MyPos./Lam.*) |
| Küche | Ende der Beschattung läuft: gelb, Spalte *Zustand* nennt die Restzeit der Ende-Verzögerung |
| Schlafzimmer | Nacht: **blaues** Symbol; **orangefarbenes Dreieck** = Fenster gekippt |
| Haustür | Gerätetyp *Tür*: **Tür-Symbol** mit Klinke. Nacht, Tür **offen** (Dreieck); die Automatik hält die Fahrt zurück (Aussperrschutz), im *Zustand* als Text sichtbar |
| Terrassentür | Tür am Tag: grünes Tür-Symbol, zu 60 % geschlossen (Füllung von oben) |
| Gästezimmer | Kein Fahrzeit-Sensor konfiguriert: Spalten *Auf*/*Zu* zeigen „–“; kein MyPosition-Taster und keine Lamellen: Spalte *MyPos./Lam.* bleibt leer |
| Markise Süd | Gerätetyp *Markise*: **Stoffbahn mit Zacken**; Beschattung (gelb), **ganz ausgefahren (0 %)** |
| Markise Ost | Markise am Tag **eingefahren (100 %)**: nur die schmale Rolle (grün) |
| Markise West | Nachts eingefahren (blau) und gerade **am Einfahren** (rot mit Pfeil nach oben) |

Die Spalten *Auf*/*Zu* (Fahrzeiten) und *Zustand* sind optional (Karteneditor: *Fahrzeiten anzeigen*, *Zustand anzeigen*). Der Mauszeiger über dem Symbol zeigt Zustand, Fahrt, Fenster und Position als Tooltip.

Tabelle zur manuellen Steuerung und Überwachung (eine Zeile je Rollo). Die Spalten sind durch Striche getrennt; die vier Taster zählen als **eine** Spalte *Fahren*: **Name** (Link zur Geräteseite) | **Status** (Spaltenüberschrift *Status*; Fenster-Symbol, Rollo-Stand grafisch; Farbe: grün = Tag, gelb = Beschattung, blau = Nacht; Dreieck = Fenster/Tür offen oder gekippt) | **Höhe** (Auswahl 100…0 %) | **Hoch** | **Stopp** | **Runter** | **Zurück** | **MyPosition** (nur mit MyPosition-Taster) | bei Rollos mit Lamellen zusätzlich die **Lamellen**-Auswahl (gemeinsame Spalte mit MyPosition). Dazu **Fahrzeiten** (Auf/Zu, aus den beim Anlegen gewählten Zeit-Sensoren, z. B. von „Rollladen Zeiten“) und eine kompakte **Überschriftenzeile**. Optional: eine **Info-Zeile** über der Tabelle mit der aktuellen **Uhrzeit** (Option *Uhrzeit in der Info-Zeile*, Standard an, mit Sekunden wenn *Sekunden anzeigen* aktiv ist),  Außentemperatur, Helligkeit, Elevation und Azimut. Mit Bezeichnern und Symbolen (`Temp: 18,1 °C | Hell: 73.110 lx | Sonne Höhe/Az: 25,6°/205,4°`; sind Elevation und Azimut beide gewählt, stehen sie in einem Eintrag). Die Werte werden einmal zentral im Karteneditor gewählt (*Info-Zeile: …*, je eine beliebige Entität; für Elevation/Azimut geht auch `sun.sun`), leere Felder werden nicht angezeigt. Optional (Option *Zustand anzeigen*): zusätzliche Spalte *Zustand* mit Nacht/Tag/Beschattung samt Verzögerung.

Die Karte trägt sich beim Start selbst als Dashboard-Ressource ein und aktualisiert den Eintrag bei Änderungen (Lovelace im Speichermodus; sonst über `extra_module_url`). Nach einem Update Browser-Cache leeren, Strg+F5. Hinzufügen: Dashboard bearbeiten → Karte hinzufügen → **Rollladen Steuerung**, dort die Geräte wählen. Ohne Editor:

```yaml
type: custom:rollladen-steuerung-card
title: Rollläden
devices:            # Geräte-IDs (am einfachsten im Karteneditor wählen)
  - 0123456789abcdef0123456789abcdef
show_state: false
show_times: true      # Fahrzeiten-Spalten (nur wenn Zeit-Sensoren konfiguriert sind)
show_seconds: false   # Zeiten mit Sekunden
show_header: true     # Überschriftenzeile
show_clock: true      # Uhrzeit in der Info-Zeile
show_help: true       # Symbol ? mit Link zu dieser Dokumentation
info_outdoor: sensor.aussentemperatur   # Info-Zeile (alle optional)
info_brightness: sensor.helligkeit
info_elevation: sun.sun
info_azimuth: sun.sun
```

Die Karte bedient die Entitäten *Position* und *Lamellen* (Zahl, zeigt den Ist-Wert, Setzen fährt das Rollo) sowie die Taster. Manuelle Fahrten beeinflussen die Automatik nicht.

## Installation

### Über HACS (empfohlen)

1. HACS öffnen → Menü (⋮) → **Benutzerdefinierte Repositories**.
2. Repository `https://github.com/Reinhard-M/ha-rollladen-steuerung` eintragen, Kategorie **Integration**, hinzufügen.
3. „Rollladen Steuerung“ in HACS suchen, **Herunterladen**, Home Assistant **neu starten**.
4. Einstellungen → Geräte & Dienste → Integration hinzufügen → „Rollladen Steuerung“.

### Manuell

Ordner `custom_components/rollladen_steuerung` aus diesem Repository nach `/config/custom_components/` kopieren, Home Assistant **neu starten**.

## Hilfe

In der Lovelace-Karte führt das Symbol **?** (Kreis mit Fragezeichen) und in den Einstellungsdialogen der Link *Dokumentation (README)* zu dieser Seite. Die Anzeige des Symbols in der Karte lässt sich im Karteneditor abschalten (`show_help: false`). Fehler und Wünsche bitte als [Issue](https://github.com/Reinhard-M/ha-rollladen-steuerung/issues) melden.

## Haftungsausschluss

* Dies ist ein **privates Hobbyprojekt** und eine **inoffizielle Community-Integration**. Sie steht in keiner Verbindung zu Home Assistant, Open Home Foundation, Nabu Casa, eQ-3/Homematic IP, Jarolift, Somfy oder anderen genannten Herstellern; alle Namen und Marken gehören ihren jeweiligen Inhabern und dienen nur der Beschreibung der Kompatibilität.
* Die Software wird **„wie besehen“ ohne jede Gewährleistung** bereitgestellt (siehe [LICENSE](LICENSE)). Die Nutzung erfolgt auf eigene Verantwortung.
* Sie ist **keine Sicherheitseinrichtung**. Sie ersetzt weder Wind-, Regen- oder Frostwächter noch Einklemmschutz oder Hinderniserkennung der Antriebe. Bewegte Rollläden, Jalousien, Markisen und Türen können Personen und Sachen gefährden; die Automatik fährt ohne Anwesenheitserkennung.
* Teste neue Einstellungen zunächst bei Anwesenheit und mache vor Updates ein Backup.

## Lizenz

[MIT-Lizenz](LICENSE) © 2026 Reinhard-M
