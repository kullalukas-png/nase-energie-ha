# Ověření bety 0.3.0 (2026-10-14)

Provedeno lokálně a v GitHub Actions, bez připojení k produkčnímu HA, portálu
nebo jeho databázi:

- 65 regresních testů: všechny prošly lokálně i na GitHubu. Obsahují převody, výpadky,
  souhlas, migrace ze starých konfigurací, zachování voleb, obnovu klíče,
  zachování identity, bezpečnou diagnostiku a balení/verzování.
- Kontrola veřejných zdrojů, syntaxe Pythonu a JSON, parity českých/anglických
  překladů a souladu verzí: prošla.
- Syntaxe pěti souborů YAML a struktura podmíněného vydání/matice HA: ověřena.
- Syntaxe sedmi shellových kroků workflow: ověřena bez jejich spuštění.
- Přibalená místní brand ikona ve velikostech 256/512 px, podle aktuálních
  pravidel HA/HACS. Žádná validace HACS není vynechávaná.
- Reprodukovatelnost archivů, kontrola jejich obsahu a odmítnutí přepsání vydání:
  pokryté místními testy. Instalační ZIP neobsahuje vývojové testy/workflow.
- Skutečný framework HA 2026.9.0 a 2026.10.1: obě sady prošly. Každá obsahuje
  šest testů migrace, reloadu, obnovy klíče a možností se zachovanou polaritou.
  API odpovědi a měření jsou smyšlené a síť v testech blokovaná.
- Oficiální Home Assistant hassfest: prošel po opravě názvů přeložených voleb
  polarity; uložená znaménka 1/−1 se touto změnou nemění.
- HACS včetně metadat, licence, dokumentace, témat a přibalené ikony: prošel
  bez vypnutí kterékoliv validace.

[Úspěšná kompletní kontrola kódu](https://github.com/kullalukas-png/nase-energie-ha/actions/runs/38519424711)
se vztahuje ke commitu `de2b26827184c487485c4b8e934b110c4c28e65d`.
Publikační workflow všechny kontroly znovu spouští na commitu vydání a release
vytvoří pouze při jejich úspěchu. Výsledky jsou veřejné na stránce Actions.

Co automatické testy nenahrazují:

- Pilotní instalace/aktualizace přes skutečný HACS a živý přenos do portálu.
- Zařazení do hlavního katalogu HACS. Přibalená ikona custom integrace nevyžaduje
  samostatný PR do upstream brands podle současných pravidel HA a validátoru HACS.

Úspěch automatických kontrol není schválením do hlavního katalogu ani zárukou
každé instalace. Beta je předběžné vydání a přenos na živou instalaci se musí
ověřit samostatně, bez zásahu do řízení FVE.
Pro stabilní release dokončete i [živý kontrolní seznam](TESTING.md).
