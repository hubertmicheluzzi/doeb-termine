#!/usr/bin/env python3
"""Holt die Spieltermine (W1, W2, V1, V2, WCupC, WCupSenB) der Union Döbling
direkt von den öffentlichen XTTV-"Vereinstermine"-Seiten (oettv.xttv.at /
voeb.xttv.at) und legt sie gemeinsam mit den händischen Ergänzungen aus
data/vorlaeufig.json als data/termine.json ab.

- Kein API-Key nötig (anders als beim "cup"-Projekt): die Vereinstermine-Seite
  ist eine ganz normale, öffentliche HTML-Seite und liefert pro Team sowohl
  bereits gespielte Runden (mit Ergebnis) als auch die kommenden Runden mit
  Datum, sobald die Verbände sie eingetragen haben - alles auf einen Blick.
- Veröffentlicht werden nur Mannschafts-Daten (Paarungen, Ergebnisse,
  Termine). Spieler-Felder enthalten ausschließlich die eigene Aufstellung
  aus data/vorlaeufig.json (von Hubert selbst gepflegt), nie Gegner-Spieler.
"""
import json, os, re, sys, time, urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
SJID = 26  # Saison 2026/2027

WOCHENTAGE = r"(Mo|Di|Mi|Do|Fr|Sa|So)"
DATUM_RE = re.compile(WOCHENTAGE + r"\.?\s+(\d{1,2})\.(\d{1,2})\.(\d{4})(?:\s+(\d{1,2}):(\d{2}))?")


def dekodieren(roh, header_charset):
    """XTTV liefert die Seiten nicht immer in UTF-8 (oft windows-1252/
    ISO-8859-1). Reihenfolge: Zeichensatz aus dem HTTP-Header, dann aus dem
    <meta>-Tag, dann UTF-8 streng, zuletzt windows-1252 (kann alles lesen).
    Geschuetzte Leerzeichen (NBSP) werden zu normalen Leerzeichen."""
    kandidaten = []
    if header_charset:
        kandidaten.append(header_charset)
    m = re.search(rb'charset=["\']?([A-Za-z0-9_\-]+)', roh[:4000])
    if m:
        kandidaten.append(m.group(1).decode("ascii", "ignore"))
    kandidaten += ["utf-8", "windows-1252"]
    for cs in kandidaten:
        try:
            text = roh.decode(cs)
            break
        except (LookupError, UnicodeDecodeError):
            continue
    else:
        text = roh.decode("windows-1252", errors="replace")
    return text.replace("\u00a0", " ")


def holen(url):
    req = urllib.request.Request(url, headers={"User-Agent": "doeb-termine/1 (github actions)"})
    last = None
    for versuch in range(3):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                roh = r.read()
                return dekodieren(roh, r.headers.get_content_charset())
        except Exception as e:
            last = type(e).__name__ + (": HTTP %s" % e.code if hasattr(e, "code") else "")
            time.sleep(3 * (versuch + 1))
    raise RuntimeError(f"Abruf fehlgeschlagen ({last}): {url}")


# ---------------------------------------------------------------------------
# Minimaler, abhaengigkeitsfreier HTML-Tabellenparser (nur die Tags, die wir
# brauchen: table/tr/th/td/a/b/br). Kein BeautifulSoup/lxml noetig.
# ---------------------------------------------------------------------------
class Zelle:
    __slots__ = ("teile",)

    def __init__(self):
        self.teile = []  # Liste von ("text", s) | ("a", href, text) | ("b", text) | ("br",)

    def text(self):
        out = []
        for t in self.teile:
            if t[0] in ("text", "b"):
                out.append(t[1])
            elif t[0] == "a":
                out.append(t[2])
            elif t[0] == "br":
                out.append(" ")
        return re.sub(r"\s+", " ", " ".join(out)).strip()

    def find_a(self, muster):
        for t in self.teile:
            if t[0] == "a" and muster in t[1]:
                return t
        return None

    def bold_texte(self):
        return [t[1].strip() for t in self.teile if t[0] == "b" and t[1].strip()]


class TabellenParser(HTMLParser):
    """Sammelt alle <table>-Elemente als Liste von Zeilen (Liste von Zellen)."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tabellen = []
        self._tiefe_table = 0
        self._zeile = None
        self._zeilen = None
        self._zelle = None
        self._a_href = None
        self._a_text = []
        self._b_text = []
        self._in_b = 0

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == "table":
            if self._tiefe_table == 0:
                self._zeilen = []
            self._tiefe_table += 1
        elif tag == "tr" and self._tiefe_table == 1:
            self._zeile = []
        elif tag in ("td", "th") and self._zeile is not None:
            self._zelle = Zelle()
        elif tag == "a" and self._zelle is not None:
            self._a_href = d.get("href", "")
            self._a_text = []
        elif tag == "b" and self._zelle is not None:
            self._in_b += 1
            self._b_text = []
        elif tag == "br" and self._zelle is not None:
            if self._in_b:
                self._b_text.append("\n")
            else:
                self._zelle.teile.append(("br",))

    def handle_endtag(self, tag):
        if tag == "table":
            self._tiefe_table -= 1
            if self._tiefe_table == 0:
                self.tabellen.append(self._zeilen)
                self._zeilen = None
        elif tag == "tr" and self._tiefe_table == 1:
            if self._zeile is not None and self._zeilen is not None:
                self._zeilen.append(self._zeile)
            self._zeile = None
        elif tag in ("td", "th"):
            if self._zelle is not None and self._zeile is not None:
                self._zeile.append(self._zelle)
            self._zelle = None
        elif tag == "a" and self._a_href is not None:
            if self._zelle is not None:
                self._zelle.teile.append(("a", self._a_href, "".join(self._a_text).strip()))
            self._a_href = None
        elif tag == "b":
            if self._in_b:
                self._in_b -= 1
                if self._zelle is not None:
                    self._zelle.teile.append(("b", "".join(self._b_text)))

    def handle_data(self, data):
        if self._a_href is not None:
            self._a_text.append(data)
        elif self._in_b:
            self._b_text.append(data)
        elif self._zelle is not None:
            self._zelle.teile.append(("text", data))


def tabelle_mit_plantermin(html):
    p = TabellenParser()
    p.feed(html)
    for zeilen in p.tabellen:
        if zeilen and zeilen[0] and zeilen[0][0].text() == "Plantermin":
            return zeilen
    return None


def parse_datumsbereich(text):
    # "07.09.2026 - 10.09.2026" -> erstes Datum als ISO
    m = re.search(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", text)
    if not m:
        return None
    dd, mm, yyyy = m.groups()
    return f"{yyyy}-{int(mm):02d}-{int(dd):02d}"


def parse_zelle(zelle):
    """Liefert ein Spiel-Dict oder None (spielfrei)."""
    text = zelle.text()
    if not text or text[0] not in ("H", "A"):
        return None
    ha = text[0]

    tid_link = zelle.find_a("tid=")
    gegner = None
    if tid_link:
        gegner = re.sub(r"\s+", "", tid_link[2])

    meid_link = zelle.find_a("meid=")
    gespielt = False
    punkte_eigen = punkte_gegner = None
    if meid_link and ":" in meid_link[2]:
        a, b = meid_link[2].split(":", 1)
        try:
            punkte_eigen, punkte_gegner = int(a), int(b)
            gespielt = True
        except ValueError:
            pass

    datum_exakt = None
    zeit = None
    hinweis = None
    for btxt in zelle.bold_texte():
        m = DATUM_RE.search(btxt.replace("\n", " "))
        if m:
            _, dd, mm, yyyy, hh, mi = m.groups()
            datum_exakt = f"{yyyy}-{int(mm):02d}-{int(dd):02d}"
            if hh:
                zeit = f"{int(hh):02d}:{mi}"
        elif btxt and len(btxt) <= 6:
            hinweis = btxt

    return {
        "ha": ha,
        "gegner": gegner,
        "gespielt": gespielt,
        "punkteEigen": punkte_eigen,
        "punkteGegner": punkte_gegner,
        "datumExakt": datum_exakt,
        "zeit": zeit,
        "hinweis": hinweis,
    }


def spalten_index(header_zeile, spalte):
    """spalte=None -> erste (einzige) Team-Spalte (Index 3).
    spalte=<Text> -> Spalte, deren zweiter Link-Text passt."""
    for i, th in enumerate(header_zeile[3:], start=3):
        if spalte is None:
            return i
        liga_texte = [t[2] for t in th.teile if t[0] == "a"]
        if len(liga_texte) >= 2 and liga_texte[1].strip() == spalte:
            return i
    return None


def hole_bewerb_spiele(zeilen, spalten_idx):
    spiele = []
    for row in zeilen[1:]:
        if len(row) <= spalten_idx:
            continue
        plan_iso = parse_datumsbereich(row[0].text())
        try:
            dg = int(row[1].text())
            runde = int(row[2].text())
        except ValueError:
            continue
        info = parse_zelle(row[spalten_idx])
        if info is None:
            continue
        datum = info["datumExakt"] or plan_iso
        datum_genau = bool(info["datumExakt"])
        spiele.append({
            "durchgang": dg,
            "runde": runde,
            "ha": info["ha"],
            "gegner": info["gegner"],
            "status": "past" if info["gespielt"] else "upcoming",
            "punkteEigen": info["punkteEigen"],
            "punkteGegner": info["punkteGegner"],
            "datum": datum,
            "datumGenau": datum_genau,
            "zeit": info["zeit"],
            "hinweis": info["hinweis"],
        })
    return spiele


def main():
    cfg = json.load(open(os.path.join(DATA, "bewerbe.json"), encoding="utf-8"))
    vorlaeufig = json.load(open(os.path.join(DATA, "vorlaeufig.json"), encoding="utf-8"))

    # Seiten gruppieren: W1+W2 teilen sich eine Seite, V1+V2 ebenso; die
    # beiden Cup-Bewerbe haben je ein eigenes bwid -> eigene Seite.
    seiten_cache = {}

    def seite(host, vid, bwid):
        key = (host, vid, bwid)
        if key not in seiten_cache:
            url = f"https://{host}/ed/index.php?do=vereinstermine&vid={vid}&sjid={SJID}"
            if bwid:
                url += f"&bwid={bwid}"
            if host == "oettv.xttv.at":
                url += "&oid=196"
            html = holen(url)
            zeilen = tabelle_mit_plantermin(html)
            if zeilen is None:
                raise RuntimeError(f"Plantermin-Tabelle nicht gefunden: {url}")
            seiten_cache[key] = zeilen
        return seiten_cache[key]

    stand = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    ergebnis = {}
    fehler = []

    for b in cfg["bewerbe"]:
        club = cfg["club"]["voeb" if b["verband"] == "voeb" else "oettv"]
        try:
            zeilen = seite(b["host"], club["vid"], b.get("bwid"))
            idx = spalten_index(zeilen[0], b.get("spalte"))
            if idx is None:
                raise RuntimeError(f"Spalte '{b.get('spalte')}' nicht gefunden")
            spiele = hole_bewerb_spiele(zeilen, idx)

            # Ueberlagerung mit data/vorlaeufig.json: Spieler-Aufstellung
            # ergaenzen bzw. noch nicht in XTTV stehende Termine einfuegen.
            for e in vorlaeufig.get("eintraege", []):
                if e.get("bewerb") != b["id"]:
                    continue
                treffer = next((s for s in spiele
                                 if s["runde"] == e.get("runde") and s["gegner"] == e.get("gegner")), None)
                if treffer:
                    if e.get("spieler"):
                        treffer["spieler"] = e["spieler"]
                elif e.get("datum"):
                    spiele.append({
                        "durchgang": None,
                        "runde": e.get("runde"),
                        "ha": e.get("ha"),
                        "gegner": e.get("gegner"),
                        "status": "upcoming",
                        "punkteEigen": None,
                        "punkteGegner": None,
                        "datum": e["datum"],
                        "datumGenau": False,
                        "zeit": None,
                        "hinweis": e.get("hinweis"),
                        "spieler": e.get("spieler"),
                        "vorlaeufig": True,
                    })

            spiele.sort(key=lambda s: (s["datum"] or "", s["runde"] or 0))
            ergebnis[b["id"]] = {
                "label": b["label"],
                "farbe": b["farbe"],
                "liga": b["liga"],
                "spiele": spiele,
            }
            print(f"  {b['label']}: {len(spiele)} Spiele")
        except Exception as e:
            fehler.append(f"{b['label']}: {e}")
            print(f"  {b['label']}: FEHLER {e}")

    out = {"format": "doeb-termine/1", "stand": stand, "bewerbe": ergebnis}
    path = os.path.join(DATA, "termine.json")
    old = None
    if os.path.exists(path):
        old = json.load(open(path, encoding="utf-8"))
        old.pop("stand", None)
    cmp = dict(out)
    cmp.pop("stand")
    if old != cmp:
        json.dump(out, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("data/termine.json aktualisiert")
    else:
        print("data/termine.json unveraendert")

    if fehler and len(fehler) == len(cfg["bewerbe"]):
        sys.exit(1)


if __name__ == "__main__":
    main()
