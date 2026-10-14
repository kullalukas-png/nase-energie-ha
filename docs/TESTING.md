# Ověření před veřejným/stabilním vydáním

## Rozlišení kontrol

- `tests/`: regresní testy skutečných převodních modulů, senderu a migrací;
  adaptéry používají dvojníky API HA. Žádný kontakt s živým HA/portálem.
- `tests_ha/`: testy skutečného frameworku HA na Linuxu, s dočasnou konfigurací
  a smyšlenými stavy/odpověďmi. Zahrnují migraci, reload i reauth stejné config entry.
- `hassfest`: oficiální kontrola metadat/HA struktury, nikoli záruka funkčního přenosu.
- `HACS`: struktura veřejného repozitáře, dostupnost podkladů a místní brand ikona.
  Žádná validace není vynechávaná; žádost o zařazení do katalogu je samostatná.

Frameworkové testy a oficiální validační Actions je nutné skutečně spustit na
GitHubu po nahrání repozitáře. Přítomnost workflow není důkaz úspěšného běhu.

## Živá pilotní kontrola (provádí správce s oprávněním vlastníka)

- [ ] Záloha HA před instalací; plán případného restartu.
- [ ] HACS stáhne správnou verzi bez kopírování souborů.
- [ ] Nová elektrárna se spáruje kódem, až po výběru a souhlasu.
- [ ] Minutová měření odpovídají HA; směry sítě a baterie ověřeny při obou tocích.
- [ ] Více střídačů: společný dům/síť se nezapočítají dvakrát.
- [ ] Stringy jsou oddělený rozpad; denní celková výroba se nezvýší jejich přidáním.
- [ ] Dočasně nedostupný senzor není falešná nula; chybějící část nezmenší PV součet.
- [ ] Výpadek internetu se obnoví bez nového párování; neovlivní EMS.
- [ ] Přechod ze skutečné 0.1.0/0.2.0 zachová klíč, entry/unique ID, měřidla a znaménka.
- [ ] Existující stringy a jejich ID zůstanou; žádné nové se nezapnou samy.
- [ ] Pozastavení zůstane po restartu/aktualizaci.
- [ ] Zrušení testovacího klíče nabídne opravu; stejná elektrárna obnoví klíč bez nové entry.
- [ ] Klíč jiné testovací elektrárny se odmítne; vzniklý nepoužitý klíč následně zrušen.
- [ ] Diagnostika a logy neobsahují klíče, kódy nebo citlivé údaje.
- [ ] Starý YAML odesílač deaktivován, pokud existoval; EMS automatiky ponechány.

Smazání integrační konfigurace není test aktualizace. Nedotýkejte se měničů,
reálných přístupových klíčů jiné osoby ani výroby kvůli testu. Pro zrušení klíče
použijte vyhrazenou pilotní elektrárnu/klíč, ne jediný produkční přístup.
