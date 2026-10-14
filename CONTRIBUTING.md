# Vývoj a bezpečné vydávání

Integrace je pouze monitorovací. Přidání ovládání EMS, dalších typů údajů nebo
zvýšení četnosti odesílání vyžaduje samostatný návrh a výslovný souhlas uživatele.
Do repozitáře ani testů nevkládejte reálné klíče, entity/domácnosti nebo export HA.

## Kontroly

```text
python tools/release.py check
python -B -m unittest discover -s tests -v
```

Tyto testy vyžadují Python 3.12+ a používají dvojníky HA. Živé testy frameworku
spouštějte odděleně na Linuxu s Pythonem 3.14.2+:

```text
python -m pip install -r requirements/current/requirements.txt
python -m pytest tests_ha -v
```

Na GitHubu se testují HA 2026.9.0 a 2026.10.1 pomocí odpovídajících připnutých
testovacích balíčků. Sítě jsou v těchto testech blokované a API odpovědi smyšlené.
To není náhrada za první pilotní přenos na živý portál.

## Nová verze

1. Upravte kód. Neměňte domain, existující unique ID/string ID ani umístění nastavení.
2. Spusťte např. `python tools/release.py bump 0.3.1` a doplňte novou sekci
   `CHANGELOG.md`. Tento mechanický nástroj zvýší číslo kódu, nikoli schéma konfigurace.
3. Spusťte testy, zkontrolujte změny a odešlete je do `main`. Počkejte na zelené kontroly.
4. **Actions → Publish tested release → Run workflow**: zadejte verzi z manifestu.
   Beta je výchozí. Stabilní vydání vyžaduje potvrzení živého kontrolního seznamu.

Workflow opět provede všechny kontroly, vytvoří ZIP a kontrolní součet a vydá
nový GitHub release `vX.Y.Z` z přesně testovaného commitu. Existující vydání
nepřepisuje. Žádný osobní GitHub token není potřeba: zapisuje jen vestavěný token
GitHub Actions v jediném publikačním jobu. Změna na `main` sama nic nezveřejní.

Verze vydání, manifestu a diagnostiky musí souhlasit. HACS nabízí jen vydané
verze, ne rozpracovanou hlavní větev. Zálohy a klíče zůstávají u uživatele v HA.

## Změna schématu konfigurace

Hlavní `CONFIG_VERSION` nezvyšujte pro běžnou změnu kódu. Pro kompatibilní změny
použijte aditivní migraci minor verze v `migrations.py`, s testy původní konfigurace
včetně vlastních voleb a vypnutého odesílání. Nikdy nemigrujte přidáním nově
odesílaných měřidel bez souhlasu. Neznámé klíče zachovávejte.

Nekompatibilní změna hlavního schématu vyžaduje samostatné migrační testy, úpravu
kontroly vydání a jasný návod k návratu ze zálohy. Žádné mazání konfigurace jako oprava.

## Závislosti a katalog

Dependabot navrhuje aktualizace Actions a testů aktuálního HA; přijímejte je až
po kontrole. Minimální podporovaná verze zůstává připnutá samostatně.
Integrace obsahuje místní `brand/icon.png` a `brand/icon@2x.png` odvozené ze
stávající značky portálu. HA 2026.3+ a současný validátor HACS je podporují;
kontrola HACS nemá žádné vypnuté validace. Pro žádost o hlavní katalog spusťte
také **Full HACS catalogue validation** a dodržte aktuální podmínky katalogu.
