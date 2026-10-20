#!/usr/bin/env python3
"""Sestaví data.json z exportů Monitoru Státní pokladny ve složce data/.

Povinné:  Odvětvový rozklikávací rozpočet pro výdaje   (název souboru končí RRRR-MM.xlsx)  -> výdaje podle oddílů
Volitelné: Souhrnný rozklikávací rozpočet               (v názvu slovo "Souhrnný", konec RRRR-MM.xlsx) -> celkové příjmy
Pro každý rok a typ se použije soubor s nejvyšším měsícem. Částky ve výstupu jsou v tis. Kč, vždy SKUTEČNOST
(sch = schválený rozpočet, sk = skutečnost, z = Kč z každých 1000 Kč skutečných výdajů, prij = skutečné příjmy).
Při jakékoli nesrovnalosti skončí chybou, takže se nikdy nezveřejní poškozená data.
"""
import glob, json, re, sys, datetime, pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
MAP = {"Tělovýchova a zájmová činnost": "Sport a zájmová činnost",
       "Ostatní činnosti související se službami pro obyvatelstvo": "Ostatní činnosti související se službami pro fyzické osoby"}
DAV_SRC = "Dávky a podpory v sociálním zabezpečení"
DAV = "Dávky a podpory v sociálním zabezpečení (jen 2010–2012)"
REM = "Ostatní oddíly mimo výběr"
KNOWN_REM = {"Spoje", "Civilní připravenost na krizové stavy", "Obrana", "Politika zaměstnanosti"}  # záměrně mimo výběr
ROWS = ["Doprava", "Státní moc, státní správa, územní samospráva a politické strany", "Kultura, církve a sdělovací prostředky", "Bydlení, komunální služby a územní rozvoj", "Vzdělávání a školské služby", "Sport a zájmová činnost", "Sociální služby a společné činnosti v sociálním zabezpečení a politice zaměstnanosti", "Ochrana životního prostředí", "Vodní hospodářství", "Bezpečnost a veřejný pořádek", "Finanční operace", "Zdravotnictví", "Ostatní činnosti", "Požární ochrana a integrovaný záchranný systém", "Průmysl, stavebnictví, obchod a služby", "Ostatní činnosti související se službami pro fyzické osoby", "Ostatní výzkum a vývoj", "Zemědělství, lesní hospodářství a rybářství", "Jiné veřejné služby a činnosti", DAV, REM]
SHORT = ["Doprava", "Státní správa a samospráva", "Kultura a církve", "Bydlení a komunální služby", "Školství", "Sport a volný čas", "Sociální služby", "Životní prostředí", "Vodní hospodářství", "Bezpečnost a pořádek", "Finanční operace", "Zdravotnictví", "Ostatní činnosti", "Požární ochrana", "Průmysl a obchod", "Služby pro fyzické osoby", "Výzkum a vývoj", "Zemědělství a lesnictví", "Jiné veřejné služby", "Dávky (jen 2010–2012)", "Mimo výběr (ostatní oddíly)"]

def clean(s):
    return s.replace("\xa0", " ").strip() if isinstance(s, str) else s

def read_sheet(path, sheet=0):
    """Vrátí (tabulka, přepočet na tis. Kč). Hlavičku hledá podle řádku, který začíná 'Obec'."""
    raw = pd.read_excel(path, sheet_name=sheet, header=None)
    col0 = raw.iloc[:, 0].map(lambda x: str(x).strip())
    hits = col0[col0 == "Obec"]
    if hits.empty:
        sys.exit(f"{path}: nenalezen hlavičkový řádek 'Obec'; změnil se formát exportu?")
    h = hits.index[0]
    if not ("Skutečnost" in str(raw.iloc[h, 7]) and "Schválený" in str(raw.iloc[h + 1, 5]) and "Po změnách" in str(raw.iloc[h + 1, 6])):
        sys.exit(f"{path}: sloupce nejsou Schválený / Po změnách / Skutečnost ({raw.iloc[h, 5:8].tolist()} {raw.iloc[h + 1, 5:8].tolist()})")
    unit = " ".join(col0[:h][col0[:h].str.contains("částek")])
    if "tisíce" in unit: k = 1.0
    elif "milion" in unit or "miliony" in unit: k = 1000.0
    elif "jednotky" in unit: k = 0.001
    else: sys.exit(f"{path}: neznámý řád částek '{unit}'")
    d = raw.iloc[h + 2:, :8].copy()
    d.columns = ["obec", "a", "b", "c", "d", "sch", "zm", "sk"]
    for c in ("a", "b", "c", "d"): d[c] = d[c].map(clean)
    for c in ("sch", "zm", "sk"): d[c] = pd.to_numeric(d[c], errors="coerce").fillna(0) * k
    return d.reset_index(drop=True)

def pick(kind):
    files = {}
    for f in glob.glob(str(ROOT / "data" / "*.xlsx")):
        name = pathlib.Path(f).name
        m = re.search(r"(20\d\d)-(\d\d)\.xlsx$", name)
        if not m or name.startswith("~$"): continue
        is_sum = "souhrnn" in name.lower()
        if (kind == "sum") != is_sum: continue
        y, mo = int(m.group(1)), int(m.group(2))
        if y not in files or mo > files[y][0]: files[y] = (mo, f)
    return files

exp_files, inc_files = pick("exp"), pick("sum")
if not exp_files:
    sys.exit("Ve složce data/ nejsou žádné odvětvové exporty *-RRRR-MM.xlsx")

out = {"ob": [{"s": s, "n": n} for s, n in zip(SHORT, ROWS)], "yrs": [], "mes": {}, "z": {}, "sch": {}, "sk": {}, "prij": {}, "pmes": {}}
for y in sorted(exp_files):
    mo, f = exp_files[y]
    d = read_sheet(f)
    total = d.iloc[0]
    if not (1e3 < total.sch < 1e9):
        sys.exit(f"{f}: celkový řádek vypadá divně (sch={total.sch}); změnil se formát exportu?")
    od = d[(d.b != "-") & (d.c == "-")]
    if od.empty: sys.exit(f"{f}: nenalezeny řádky oddílů; změnil se formát exportu?")
    sums = {k: {r: 0.0 for r in ROWS} for k in ("sch", "sk")}
    for r in od.itertuples():
        name = MAP.get(r.b, r.b)
        if name == DAV_SRC: name = DAV
        if name not in ROWS:
            if name not in KNOWN_REM: print(f"UPOZORNĚNÍ {y}: neznámý oddíl '{r.b}' zařazen do '{REM}'")
            name = REM
        sums["sch"][name] += r.sch; sums["sk"][name] += r.sk
    for k in ("sch", "sk"):
        if abs(sum(sums[k].values()) - total[k]) > 0.5:
            sys.exit(f"{y} ({k}): součet oddílů {sum(sums[k].values()):.1f} != celkem {total[k]:.1f} tis. Kč")
    tot = sum(sums["sk"].values())
    if tot <= 0: sys.exit(f"{y}: nulová skutečnost")
    out["yrs"].append(y); out["mes"][str(y)] = mo
    out["z"][str(y)] = [round(sums["sk"][r] / tot * 1000, 1) for r in ROWS]
    out["sch"][str(y)] = [round(sums["sch"][r], 1) for r in ROWS]
    out["sk"][str(y)] = [round(sums["sk"][r], 1) for r in ROWS]
    print(f"{y}-{mo:02d}: výdaje skutečnost {tot:,.0f} tis. Kč")

for y in sorted(inc_files):
    mo, f = inc_files[y]
    if y not in out["yrs"]:
        print(f"UPOZORNĚNÍ: příjmy {y} bez odvětvového exportu výdajů, přeskočeno"); continue
    d = read_sheet(f, sheet="Příjmy")
    t = d.iloc[0]
    if not (t.a == "-" and t.b == "-" and t.c == "-" and t.sk > 0):
        sys.exit(f"{f}: první řádek listu Příjmy není celkový součet")
    out["prij"][str(y)] = round(float(t.sk), 1); out["pmes"][str(y)] = mo
    if mo == out["mes"][str(y)]:   # kontrola proti výdajům ze stejného období, pokud je v souboru list Výdaje
        try:
            e = read_sheet(f, sheet="Výdaje").iloc[0]
            if abs(e.sk - sum(out["sk"][str(y)])) > 1.0:
                sys.exit(f"{y}: výdaje ze souhrnného exportu ({e.sk:.1f}) se liší od odvětvového ({sum(out['sk'][str(y)]):.1f})")
        except ValueError:
            pass
    print(f"{y}-{mo:02d}: příjmy skutečnost {t.sk:,.0f} tis. Kč")

out["generovano"] = datetime.date.today().isoformat()
(ROOT / "data.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
print("data.json OK:", len(out["yrs"]), "let,", len(out["prij"]), "let s příjmy")
