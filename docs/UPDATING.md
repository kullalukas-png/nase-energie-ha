# Aktualizace bez ztráty nastavení

## Uživatel

1. Přečtěte přehled změn a vytvořte zálohu HA.
2. V HACS zvolte **Naše energie → Aktualizovat** a po instalaci restartujte HA.
3. Ověřte stav připojení a nové měření na portálu.

Integraci neodstraňujte. Při přechodu z ručně nahrané 0.1.0/0.2.0 přidejte
vlastní repozitář HACS a stáhněte novou verzi do téže složky/domain `nase_energie`.
HACS sám migraci dat nespouští; provede ji HA při načtení aktualizované integrace.

Zachová se klíč, ID elektrárny, entry ID/unique ID, název, diagnostická entita,
výběr senzorů, vlastní znaménka, stringy, jejich anonymní ID i pozastavení.
Nevybírají se automaticky nové senzory. Změna formátu konfigurace má samostatnou
migraci a testy; běžná změna kódu nevyžaduje nové párování.

HACS vyměňuje kód v `custom_components`, nastavení je v úložišti HA `.storage`.
Do složky integrace nepatří uživatelské soubory, klíče nebo vlastní nastavení.

## Obnovení klíče není aktualizace

Po odpovědi 401/403 se další přenos zastaví a HA nabídne opravu připojení.
Vytvořte nový kód ve stejné elektrárně a potvrďte opravu. Výměna klíče nesmí
změnit měřidla ani zapnout pozastavené odesílání. Kód jiné elektrárny se odmítne;
v portálu následně zrušte nepoužitý klíč, který při výměně tohoto kódu vznikl.

## Výpadek nebo návrat ke starší verzi

Při výpadku internetu nemažte integraci a nepárujte znovu. Přenos se opakuje
se zpomalením. Fronta 120 vzorků je jen v paměti; restart ji vymaže.
Zachování nastavení tedy neznamená zachování neodeslaných vzorků.

Konfigurace nyní má schéma 1.2. Přechod 1.1 → 1.2 je pouze aditivní.
Budoucí nekompatibilní hlavní schéma se nesmí automaticky vracet nebo mazat.
Pro návrat po nekompatibilní migraci obnovte odpovídající zálohu HA včetně kódu.
Neslibujeme libovolný downgrade bez zálohy.

## Portál

Portál není součástí HACS balíčku. Jeho aktualizace a databázové změny se provádějí
samostatně. Nové volitelné API pole nejprve podporujte na serveru, potom nabídněte
v integraci se souhlasem. Verze 0.3.0 nemění protokol přenosu z 0.2.0.
