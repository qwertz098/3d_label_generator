# Anforderungen 3D-Schilder-Generator (Web UI)

## Ziel
- Per Web-UI konfigurierbare, rechteckige Schilder als 3D-Modelle erzeugen.

## Geometrie
- Flaches Rechteck mit Vorgaben:
  - Hoehe
  - Breite
  - Materialstaerke
  - Eckenradius
  - optional Druckplattengröße

## Eingabe Text
    - bei mehreren mit ";" getrennten texten sollen mehrere Schilder pro Druckplatte (Maße oben) im selben Modell erstellt werden und innerhalb der Platte bleiben, sonst fehlermeldung
    - dazu sollen mehrere Schilder neben und untereinander angeordnet werden, bis die maximalen Druckmaße erreicht werden
    - Abstand der Schilder 0,5mm

## Schriftparameter
- Schriftart konfigurierbar.
    - font preview in pulldown menu
    - offer at least 10 fonts, all sans serif
    - incl. these three at the top of the list Osifont, Overpass, Arial Rounded
- Schriftgroesse:
  - Feste Groesse oder
  - Automatisch an Schildbreite anpassen.
- fett und kursiv optionen
- Schriftstaerke (<= Schildstaerke) konfigurierbar.
- Randabstand konfigurierbar.
- Optional Zeilenumbruch unterstuetzen.
- Schriftmodus: subtrahieren oder extrudieren von der Platte (default=extrudieren)
- Schrift als separaten Körper erhalten (default=ja)
     -d.h. als eingebettet in Schild bei subtrahieren
     -d.h. auf dem Schild liegend bei extrudieren

## Exportformate
- STEP
- STL
- ~~3MF~~ (suspendiert - Qualitätsprobleme bei Text-Tessellierung)

## Backend / Web
- Web-UI mit atualisierung der Vorschau ohne seitenrefresh
- UI language EN as default
- wähle passendes framework, wenn möglich mit Flask (single file python app)
- Spaeter leicht dockerisierbar.
- 3D-Generierung via cadquery anbinden.
- 2D-Vorschau im UI anzeigen.
- 3D vorschau mit cadquery vis oder three.js inkl. pan, rotate, zoom also on mobile


## Tests
- [x] Unit Tests für 3D-Generierung implementieren:
  - [x] Einzelne Schilder mit verschiedenen Geometrien (Größe, Dicke, Eckenradius)
  - [x] Verschiedene Schrift-Optionen (bold, italic, auto-size, fixed size)
  - [x] Text-Modi (extrudiert vs. subtrahiert)
  - [x] Separate Körper vs. verschmolzen
  - [x] Zeilenumbruch-Funktionalität
  - [x] Multi-Schild Plate Arrangements
  - [x] Edge Cases (leerer Text, zu große Schilder, zu viele Schilder)
- [x] Export-Tests (STEP, STL)

## UI Verbesserungen
- [x] Text als separater Körper: andere Farbe (orange) für Text in 3D-Vorschau
- [x] 2D-Vorschau: tatsächliche Größenverhältnisse der Labels
- [x] 2D-Vorschau: Plate-Arrangement mit korrekter Anordnung
- [x] 2D-Vorschau: Font-Parameter berücksichtigen (Schriftart, Bold, Italic)
  - [x] Google Fonts für Web-Vorschau geladen
  - [x] Dynamische Aktualisierung bei Font-Änderungen
- [x] Hover-Texte mit Erklärungen für alle UI-Elemente
  - [x] Export-Buttons: STEP (beste Wahl für separate Körper), STL
  - [x] Geometry, Font, Text Mode Optionen
- [x] Font Size Feld: korrekte Anzeige beim Seitenladen
- [x] Debounce für 3D-Preview: 1 Sekunde Wartezeit nach letzter Texteingabe
- [x] Dimension Felder: mm-Einheit überlappte mit Spinner-Buttons (behoben)
- [x] STL Export: Bessere Tessellierung für feine Text-Details (0.01mm Toleranz)
- [x] Model-Caching: Kein erneutes Generieren beim Export wenn Parameter unverändert
- [x] Model-Caching Tests: Hash-Berechnung, Cache-Hit/Miss, Parameter-Extraktion

## Bugfixes
- [x] Fonts müssen heruntergeladen werden (fonts-Ordner war leer)
- [x] Font-Wechsel, Bold, Italic funktionieren erst nach Font-Download
- [x] Fallback auf System-Fonts wenn keine Custom-Fonts vorhanden
- [x] Font-Registrierung mit OpenCASCADE Font_FontMgr (plattformübergreifend)

## Font-System
- [x] 9 Font-Familien verfügbar (25 TTF-Dateien inkl. Bold/Italic)
  - Osifont, Overpass, Roboto, Open Sans, Lato, Montserrat, Source Sans 3, Nunito, Poppins
- [x] Fonts werden beim App-Start mit OpenCASCADE registriert
- [x] Plattformübergreifend: Windows, macOS, Linux, Docker
- [x] Tests für Font-Registrierung und verschiedene Schriftarten

## Docker
- [x] Dockerfile mit allen Abhängigkeiten
- [x] Font-Download während Docker-Build
- [x] Fontconfig-Backup für System-Font-Discovery
- [x] Healthcheck-Endpoint

## Offene Punkte / spaetere Ergaenzungen
- Hier ergaenzen (z. B. Dateiformat-Details, Validierungen, UI-Mockups).
- Parasolid-Export: Bibliothek/Workflow klaeren.
