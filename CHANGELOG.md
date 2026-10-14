# Přehled změn

## 0.3.0 — připravená veřejná beta, 2026-10-13

- Podklady pro vlastní repozitář HACS, licence MIT, návody a hlášení problémů.
- Obnovení zrušeného klíče přes opravu připojení v HA bez odstranění integrace.
- Obnovení zachovává elektrárnu, ID entit, název, měřidla, znaménka, stringy i pozastavení.
- Kód jiné elektrárny nikdy nepřepíše existující připojení.
- Aditivní migrace konfigurace 1.1 → 1.2 ze starších verzí 0.1.0/0.2.0.
- Nové stringy se při migraci ani otevření možností neaktivují automaticky.
- Možnosti ponechávají i nezměněné doplňkové volby.
- Automatické testy zachování konfigurace, validace HACS/hassfest a kontrolované vydávání.
- Přeložené volby polarity mají platné názvy; uložená znaménka 1/−1 zůstávají beze změny.
- Odesílání zůstává pouze monitorovací, každých 60 sekund; API formát se nemění.

Stav ověření: viz `docs/TESTING.md`. Označení beta neznamená ověření na všech instalacích HA.

## 0.2.0 — 2026-10-13

- Rozpad výkonu po PV strinzích v jednom společném minutovém požadavku.
- Stabilní anonymní ID stringů a seskupení podle registru střídačů.
- Výslovný souhlas s přenosem nových stringů v možnostech integrace.

## 0.1.0 — 2026-10-13

- Párování jednorázovým kódem, výběr senzorů a potvrzení znamének.
- Výroba, spotřeba domu, síť, baterie a SOC; částečné výpadky nejsou nulová měření.
- Diagnostika bez klíčů, omezená fronta a zpomalené opakování při výpadku portálu.
