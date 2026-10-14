# Zveřejnění na GitHubu a HACS

Tento soubor je předávací návod, nikoli potvrzení již provedeného zveřejnění.
Připravená identita: **kullalukas-png/nase-energie-ha**, licence **MIT**.

## První veřejná beta

1. Na účtu `kullalukas-png` vytvořte **public** repozitář `nase-energie-ha`
   s hlavní větví `main`. Nenahrávejte celou pracovní složku EMS.
2. Rozbalte **zdrojový/repository ZIP** a nahrajte jeho obsah do kořene repozitáře,
   včetně skryté složky `.github`, nikoli samotný ZIP nebo obalovou složku.
3. Popis: `Read-only Home Assistant monitoring for the Naše energie solar portal.`
   Témata: `home-assistant`, `hacs`, `solar`, `goodwe`, `photovoltaic`, `monitoring`.
4. V **Settings → Actions** povolte workflow. Pokud máte možnost, chraňte `main`
   pravidlem vyžadujícím testy. Zapněte **Security → Private vulnerability reporting**.
5. Počkejte na úspěšné **Validate integration**: regresní testy, oba frameworky HA,
   hassfest a úplná kontrola HACS včetně přibalené ikony.
   Chyby opravte; nevypínejte ostatní kontroly kvůli vydání.
6. V **Actions → Publish tested release → Run workflow** vyberte `main`, verzi
   `0.3.0` a ponechte **Beta / pre-release** zapnuté. Workflow znovu spustí kontroly
   a teprve potom vytvoří release `v0.3.0` s ZIPem a kontrolním součtem.
7. Na zálohované pilotní instalaci přidejte repozitář v HACS jako **Integration**,
   povolte bety, nainstalujte a proveďte [živý kontrolní seznam](TESTING.md).

HACS běžně stahuje obsah `custom_components/nase_energie` z GitHubu; nepoužíváme
`zip_release`, tudíž uživatel nemusí ručně rozbalovat přiložený instalační ZIP.
Samotný tag bez GitHub release není naším publikačním postupem.

## Aktualizace

Postup je v [CONTRIBUTING.md](../CONTRIBUTING.md). Uživatel nepotřebuje nový kód
ani opětovné vyplnění měřidel. HACS nabízí novou vydanou verzi, instalace vyžaduje
restart HA. Nikdy nepublikujte automatické restarty uživatelů nebo přístup do jejich HA.

## Ikona a hlavní katalog

V `docs/branding/icon.svg` je zdroj stávající značky portálu. PNG 256/512 px jsou
přibalené v `custom_components/nase_energie/brand/`. Home Assistant 2026.3+
podporuje vlastní brand obrázky a aktuální validátor HACS je přijímá. Pro tuto
custom integraci tedy není samostatné zaslání ikony do upstream brands nutné.

Před žádostí o hlavní katalog spusťte **Full HACS catalogue validation** a ověřte
aktuální podmínky `hacs/default`. Vlastní repozitář a žádost o katalog nejsou
totéž; příprava balíčku nezaručuje schválení katalogu. Pokud by se integrace
později přidávala přímo do HA Core, jsou upstream brand obrázky samostatný krok.

Oficiální vysvětlení místních značek:
https://developers.home-assistant.io/docs/core/integration/brand_images/

## Oficiální podklady

- https://www.hacs.dev/docs/publish/integration/
- https://www.hacs.dev/docs/publish/start/
- https://www.hacs.dev/docs/publish/action/
- https://www.hacs.dev/docs/publish/include/
- https://developers.home-assistant.io/docs/core/integration/config_flow/
