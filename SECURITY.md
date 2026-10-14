# Bezpečnost a soukromí

Tato integrace jen odesílá vybraná měření přes ověřené HTTPS. Neposílá hlavní token
Home Assistantu, nemá příchozí ovládací kanál a nezasahuje do EMS nebo zařízení.
Párovací kód platí 10 minut, do konfigurace HA se neukládá. Uložený portálový klíč
smí jen přidávat měření do jedné elektrárny. Zálohy HA ho obsahují: chraňte je.

Odesílají se potvrzené veličiny, čas, anonymní identifikátory stringů a jejich
uživatelem potvrzené názvy/střídače. Názvy mohou odhalovat informace o domě;
nepoužívejte v nich citlivé údaje. Zveřejnění domácnosti na portálu je samostatná
volba a instalace integrace ji sama neaktivuje.

Diagnostika integrace neobsahuje klíč, párovací kód, URL, názvy domácností ani
názvy/ID měřidel. Nesdílejte celý export konfigurace ani soubory `.storage`.
Do veřejného hlášení problému neposílejte `secrets.yaml`, konfiguraci ani zálohu HA.

Při podezření na únik klíč zrušte v portálu a obnovte připojení novým kódem
stejné elektrárny. Smazání integrace v HA klíč na portálu nezruší.

Citlivou chybu hlaste prostřednictvím GitHubu **Security → Report a vulnerability**,
pokud správce zapnul soukromé hlášení. Nezveřejňujte tajné údaje v běžném issue.
Pokud soukromé hlášení není dostupné, vytvořte pouze obecné oznámení žádající
o soukromý kontakt, bez reprodukce s klíči nebo daty domácností.

Podporovaná větev je poslední vydaná beta/stabilní verze. Před aktualizací zálohujte HA.
