# doeb-termine

Übersicht aller Spiele der Union Döbling (WTTV W1, W2 · VÖB V1, V2 · WTTV-Cup C & Senioren B)
für PC und Handy.

## Seiten

- `index.html` – Terminübersicht: kommende und gespielte Spiele mit Ergebnis und Aufstellung.
- `spieler.html` – Bilanz der Spieler und Doppel-Paarungen, aufklappbare Einzelspiele.

## Daten

- `data/termine.json` – alle Spiele samt Einzelspielen
- `data/spieler.json` – Spieler-Bilanzen und Doppel-Paarungen
- `data/tabellen.json` – Ligatabellen je Bewerb

Alle drei Dateien werden automatisch erzeugt. **Nicht händisch bearbeiten** – sie werden beim
nächsten Lauf überschrieben.

## Woher die Daten kommen

Einzige Quelle ist das Vereins-Verwaltungstool (Nextcloud). Ein Rechner des Vereins erzeugt
daraus alle 30 Minuten einen gefilterten Auszug und lädt ihn hier hoch – aber nur, wenn sich
inhaltlich etwas geändert hat. Es gibt keine GitHub Action.

Termine, Verschiebungen und Aufstellungen werden **im Verwaltungstool** eingetragen, nicht hier.

## Was öffentlich ist

Je Spiel: Datum und Uhrzeit, Mannschaft, Runde, Gegner (Mannschaft), Heim/Auswärts, Status,
Ergebnis, ob das Ergebnis bestätigt ist, Aufstellung und Einzelspiele.

Eigene Spieler erscheinen nur mit Rufnamen (und nur, wenn sie zugestimmt haben), gegnerische
Spieler nur mit Vornamen. Nicht veröffentlicht werden: Nachnamen gegnerischer Spieler,
Passnummern, Spielorte, interne Notizen, Trainings- und Schiedsrichter-Termine.
