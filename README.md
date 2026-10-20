# Výdaje Brna na tisícikoruně

Grafy se načítají z `data.json`, který se při každém nasazení sestaví z exportů v `data/`.

## Jednorázové nastavení
1. Zkopírujte všech 17 exportů (`Odvětvový_rozklikávací_rozpočet_pro_výdaje_RRRR-MM.xlsx`) do složky `data/`.
2. GitHub → Settings → Pages → Build and deployment → Source: **GitHub Actions**.
3. Pokud v repozitáři už je jiný workflow pro Pages, smažte ho (jinak se budou nasazení přebíjet).
4. Commit a push do větve `main`.

## Každý rok
1. V Monitoru stáhněte export „Odvětvový rozklikávací rozpočet pro výdaje“ pro Statutární město Brno, období prosinec.
2. Soubor pojmenujte `Odvětvový_rozklikávací_rozpočet_pro_výdaje_2026-12.xlsx` (rok a měsíc na konci názvu) a dejte do `data/`.
3. Commit a push. Workflow sám sestaví data a nasadí web (cca 1 minuta).

Pro každý rok se použije soubor s nejvyšším měsícem, takže starší neúplný export (např. `2026-08`) nemusíte mazat.
Když se něco nesrovná (jiný formát, nesedí součty), workflow skončí chybou a na webu zůstanou původní data.

## Příjmy (volitelné, pro graf příjmů a výdajů)
Přidejte i export „Souhrnný rozklikávací rozpočet“ (období prosinec každého roku) pro Statutární město Brno. V názvu musí být slovo `Souhrnný` a na konci `RRRR-MM.xlsx`, například `Souhrnný rozklikávací rozpočet 2025-12.xlsx`. Bez nich graf příjmů ukáže jen hlášku, že data chybí.

## Odkazy na grafy
Adresa `brno-grafy.html` s parametrem `graf`:
- `?graf=zmena` kdo získal a kdo ztratil z tisícovky (volitelně `&od=2010&do=2025`)
- `?graf=plan` schválený rozpočet a skutečnost (volitelně `&oblast=0`)
- `?graf=vyvoj` vývoj podílu oblastí na tisícikoruně (volitelně `&oblasti=0,2,5`)
- `?graf=vydaje` skutečná velikost výdajů podle oblastí v mld. Kč
- `?graf=prijmy` příjmy a výdaje města v mld. Kč
- `?graf=cashflow` roční saldo (příjmy minus výdaje) v mld. Kč
Pro všechny: `&nadpis=0` skryje nadpis, `&ovladani=0` skryje ovládací prvky. Bankovka: `brno-bankovka-vyvoj-2010-2026.html` (`?rok=2016`, `&auto=1`).

## Místní náhled
`python scripts/build_data.py` a pak `python -m http.server` (stránky načítají `data.json`, přes `file://` nefungují).
