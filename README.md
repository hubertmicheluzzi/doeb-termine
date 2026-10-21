# doeb-termine

Übersicht aller Spiele der Union Döbling (WTTV W1, W2 · VÖB V1, V2 · WTTV-Cup C & Senioren B)
als eine HTML-Seite für PC und Handy, automatisch aktuell gehalten über GitHub Actions.

- `index.html` – die Seite selbst, lädt `data/termine.json` zur Laufzeit.
- `data/bewerbe.json` – Konfiguration: welche Döbling-Mannschaft/Bewerb kommt von welcher
  XTTV-Vereinstermine-Seite (oettv.xttv.at bzw. voeb.xttv.at), kein API-Key nötig.
- `data/vorlaeufig.json` – **händisch von Hubert gepflegt**: eigene Spieler-Aufstellungen für
  kommende Spiele (die XTTV nicht liefert) sowie Termine, die XTTV/Cup-Referat noch nicht
  offiziell eingetragen hat. Zuordnung über `bewerb` + `runde` + `gegner`.
- `data/termine.json` – von `tools/fetch_termine.py` automatisch erzeugt (nicht händisch
  bearbeiten, wird von der GitHub Action überschrieben).
- `.github/workflows/abruf.yml` – holt zweimal täglich die aktuellen Termine und committet sie.

Veröffentlicht werden nur Mannschafts-Daten (Paarungen, Ergebnisse, Termine). Das Feld
"Spieler" zeigt ausschließlich die eigene Aufstellung (aus `data/vorlaeufig.json`), nie
Angaben zu gegnerischen Spielern.

## Händisch aktuell halten

Wenn ein Termin noch nicht in XTTV steht (z. B. ein Cup-Termin, der erst vom Cup-Referat
bestätigt werden muss) oder wenn eine Aufstellung für ein kommendes Spiel feststeht, trägst
du das in `data/vorlaeufig.json` ein und committest/pusht die Datei – beim nächsten Lauf der
Action wird es berücksichtigt (sobald XTTV den echten Termin liefert, übernimmt der
automatische Abruf automatisch den echten Termin, die Aufstellung bleibt aber erhalten).
