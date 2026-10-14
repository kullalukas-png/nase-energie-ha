# Výsledek místní přípravy 0.3.0 (2026-10-13)

Provedeno bez připojení k produkčnímu HA, portálu nebo jeho databázi:

- 63 místních regresních testů: všechny prošly. Obsahují převody, výpadky,
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
- Metadata testovacích balíčků ověřena na PyPI: 0.13.363 → HA 2026.9.0,
  0.13.372 → HA 2026.10.1; tyto běhy jsou připravené v GitHub Actions.

Dosud neprovedeno:

- Nahrání veřejného repozitáře ani vytvoření release na GitHubu.
- Testy `tests_ha` se skutečným frameworkem na Linuxu (místní dostupný Python
  je 3.12/Windows; HA 2026.9+ vyžaduje Python 3.14.2+).
- Oficiální Actions hassfest/HACS. Jejich výsledky závisí také na skutečně
  zveřejněném repozitáři a dokumentaci; workflow jsou připravené, ne proběhlé.
- Pilotní instalace/aktualizace přes skutečný HACS a živý přenos do portálu.
- Zařazení do hlavního katalogu HACS. Přibalená ikona custom integrace nevyžaduje
  samostatný PR do upstream brands podle současných pravidel HA a validátoru HACS.

Výsledky místních testů nejsou certifikací HACS ani zárukou každé instalace.
Pro beta release je nutné nechat projít všechny připravené kontroly na GitHubu.
Pro stabilní release dokončete i [živý kontrolní seznam](TESTING.md).
