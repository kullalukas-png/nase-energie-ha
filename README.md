# Naše energie — integrace Home Assistant (0.3.0, beta)

Integrace **pouze sleduje** FVE. Čte potvrzené senzory ve vašem HA a po minutě
odesílá měření přes ověřené HTTPS do portálu. Nemění nastavení střídače, baterie,
bojleru ani klimatizace. Nepotřebuje hlavní token HA ani otevřený port domácí sítě.

## Instalace přes HACS

Určeno pro Home Assistant **2026.9 a novější**. HACS musí být v HA již nainstalovaný.
Stahujte vydané verze ze sekce [Releases](https://github.com/kullalukas-png/nase-energie-ha/releases).
Beta je určena pro pilotní použití; přehled automatických kontrol je v
[ověření verze](docs/VALIDATION.md). Postup vydávání pro správce je odděleně
v [návodu pro správce](docs/PUBLISHING.md).

1. V HACS otevřete nabídku **⋮ → Vlastní repozitáře**.
2. Zadejte `https://github.com/kullalukas-png/nase-energie-ha`, typ **Integrace**.
3. Vyhledejte **Naše energie**, stáhněte zveřejněnou verzi a restartujte HA.
   Pokud instalujete betu, v HACS povolte zobrazení předběžných vydání.
4. Na portálu vytvořte elektrárnu a v **Připojení a nastavení → Připojit Home Assistant
   → Párovat integraci** vytvořte jednorázový kód; platí 10 minut.
5. V HA: **Nastavení → Zařízení a služby → Přidat integraci → Naše energie**.
   Potvrďte adresu portálu, kód, měřidla, znaménka a souhlas.
6. Ověřte první měření na portálu. HACS pouze instaluje kód; samotné spárování
   každé elektrárny se provádí zvlášť v Nastavení HA.

[Přehled změn](CHANGELOG.md) · [Aktualizace a zachování nastavení](docs/UPDATING.md)
· [Soukromí a bezpečnost](SECURITY.md) · [English quick start](docs/ENGLISH.md)

## Instalace z připraveného ZIPu

1. Správce portálu musí nejprve nasadit aktualizaci **1.3.0** a ve **Správě webu**
   potvrdit **Aktivovat ukládání PV stringů**. Přidá se samostatná tabulka, bez
   změny původních tabulek. Starší odesílače bez stringů nadále fungují.
2. Rozbalte ZIP. Složku `custom_components/nase_energie` zkopírujte do
   `/config/custom_components/nase_energie` svého HA. Ne do `/config/packages`.
   Existující ostatní integrace ani konfiguraci nepřepisujte.
3. Restartujte HA, aby načetl novou integraci. Tato příprava žádný restart neprovedla.
4. Na portálu v **Připojení a nastavení → Připojit Home Assistant → Párovat integraci**
   vytvořte jednorázový kód. Platí 10 minut.
5. V HA otevřete **Nastavení → Zařízení a služby → Přidat integraci → Naše energie**.
   Vyplňte HTTPS adresu portálu a kód; potvrďte nabízené senzory, směry a souhlas.
6. V portálu ověřte první měření. Ve starém YAML odesílači poté vypněte pouze
   jeho minutovou odesílací automatizaci, pokud ji již používáte. Dva souběžné
   odesílače mohou zkreslit integraci energie. Nedotýkejte se automatizací EMS.

Beta vyžaduje ověření přenosu na skutečné instalaci HA a portálu před stabilním
vydáním. Lokální testy s dvojníky HA nejsou totéž co ověření živého HA.
[Rozsah testování a kontrolní seznam](docs/TESTING.md).

## Aktualizace již spárované integrace

Před aktualizací vytvořte zálohu HA. V HACS aktualizujte **Naše energie** a
restartujte HA. Při ruční instalaci nahraďte jen složku integrace.
**Integraci neodstraňujte a nepárujte znovu.** Klíč, elektrárna, výběr měřidel,
znaménka, existující stringy i pozastavení zůstávají v konfiguraci HA.
HACS nenahrazuje úložiště `.storage`, kde HA tyto volby uchovává.

Migrace ze starších verzí nic dalšího nezačne odesílat. Chcete-li přidat stringy,
nejprve ověřte podporu portálu 1.3.0+ a tabulku výše, potom je výslovně vyberte
v **Naše energie → Možnosti** a potvrďte souhlas. Nemusíte měnit klíč.

## Jednotlivé PV stringy

- GoodWe PV1–PV4 se navrhují podle registru, včetně přejmenovaných entit.
- Každý string má stabilní anonymní ID, název ze senzoru HA, přiřazený střídač
  podle registru zařízení a aktuální výkon ve W. Kdo má jiné střídače, vybere
  senzory z nabídky; bez známého zařízení může být přiřazení prázdné.
- Zobrazované názvy a technické parametry můžete měnit v portálu v **Stringy a střídače**
  (vyžaduje novější portál). Výchozí názvy pocházejí z HA; lze je upravit v HA a
  znovu potvrdit Možnosti. Stávající anonymní ID se tím nemění.
- Stringy se odesílají **ve stejném minutovém požadavku**, nejvýše 32.
- Nezvyšují `pv_w` ani celkové kWh FVE. Původní výběr zdrojů výroby zůstává oddělený.
- V portálu jsou v **Grafy a historie → Den**, s denními kWh a pokrytím záznamy.
- Data začínají prvním přijatým vzorkem. Starší historie se zpětně nevytváří.
- Napětí, proud a čítače kWh jednotlivých stringů tato verze neposílá.
- Stav `pv_strings_not_ready` znamená, že správce ještě nepřipravil tabulku
  v portálu; sender nevymaže čekající vzorky a další pokus odloží o 15 minut.

## Automatické rozpoznání

- GoodWe senzory se rozpoznávají podle integrace a jejich stabilního unique_id,
  nikoli podle přejmenovatelného názvu nebo koncovky entity.
- Výroba: nabídne se PV vstup každého GoodWe, jehož senzor není zakázán. Sčítají
  se zvolené PV zdroje. **Nevybírejte současně součet a jeho dílčí senzory.**
- AC výstup není výchozí zdroj výroby, protože může obsahovat vybíjení baterie.
- U více střídačů nejsou celkový dům a síť automaticky sečteny ani hádány.
  Je třeba zvolit jeden společný údaj podle zapojení. Ne všechny instalace mají
  stejnou topologii; spolehlivá plná automatika zde vyžaduje další profily.
- U jedné dostupné baterie se nabídne SOC a její výkon. Více baterií zatím
  vyžaduje předem připravené agregované měření v HA.
- Ostatní výrobci: senzory lze vybrat z nabídky podle jejich názvu; automatické
  profily zatím nejsou implementovány. Žádné psaní ID není nutné.
- Jednotky W/kW se načtou ze senzorů a převedou. kWh čítače se nepřijímají jako výkon.
- Portál používá **+ odběr ze sítě / − export**, **+ nabíjení / − vybíjení**.
  U známých GoodWe senzorů se nabídne opačné znaménko. U jiných je nutné směr potvrdit.

## Provoz, soukromí a výpadky

V možnostech integrace změníte senzory a znaménka nebo vypnete odesílání.
Diagnostický senzor ukáže stav, poslední úspěch, počet čekajících a vynechaných
vzorků. Diagnostický export neobsahuje klíč, párovací kód, názvy ani ID senzorů.

Při nedostupném senzoru se odešle `null`, ne vymyšlená nula. Při výpadku jednoho
PV zdroje je celý součet nedostupný, místo zobrazení falešně nižší výroby.
Při výpadku internetu se uchová nejvýše **120 vzorků v paměti** a po obnově se
odesílají maximálně tři za minutu s původním časem. Starší vzorky se při zaplnění
zahodí; restart/reload HA nebo změna možností tuto paměť vymaže. Není to trvalý archiv.
Odpojení internetu neovlivní lokální řízení FVE. Přesměrování HTTP se nenásledují.

Klíč uložený v konfiguraci HA smí pouze přidávat měření do jedné elektrárny.
Neumožňuje číst soukromá data ani ovládat HA. Přesto chraňte zálohy HA — obsahují
uložený klíč. Kód se po párování neukládá. Klíč zrušíte na portálu.
Po zrušení klíče sender přestane opakovat neplatné požadavky a HA nabídne opravu
připojení. V portálu vytvořte nový kód **pro stejnou elektrárnu** a vložte jej
do opravy. Změní se jen klíč; měřidla, ID entit a ostatní nastavení zůstanou.
Kód jiné elektrárny se odmítne, původní připojení se nepřepíše. Protože portál
vydá klíč už při výměně kódu, takový nepoužitý klíč jiné elektrárny zrušte ručně.
Odebrání integrace samo klíč na portálu nezruší. Při duplicitním párování také
zrušte nově vydaný nepoužitý klíč. Přerušení internetu nové párování nevyžaduje.

## Instalace ostatními uživateli / HACS

Stejný ZIP může nainstalovat jiný uživatel do svého HA. Každý si vytvoří vlastní
elektrárnu a párovací kód; nepředává se váš klíč ani hlavní token HA.

Kód a vydání spravuje `kullalukas-png/nase-energie-ha` s licencí MIT. Aktualizace
se vydávají až po automatických testech, hassfest a HACS; uživatelům je nabízí
HACS. Pro první připojení každý použije svoji elektrárnu a svůj jednorázový kód.
Vlastní repozitář HACS a zařazení do hlavního katalogu jsou odlišné kroky.

## Vývojové testy

`python -m unittest discover -s tests -v`

Testují skutečné převodní moduly, rozpoznání, HTTPS klient a sender se
syntetickými odpověďmi. HA adaptéry vyžadují další test na skutečném HA;
samotná kompilace Pythonu jej nenahrazuje. Skutečné testy frameworku jsou odděleně
v `tests_ha`, aby dvojníci nezastínili moduly HA. Viz [vývoj a vydávání](CONTRIBUTING.md).
