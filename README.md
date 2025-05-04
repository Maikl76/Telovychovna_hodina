# Aplikace Tělovýchovná Jednotka

Aplikace pro vytváření a správu příprav na školní tělovýchovné hodiny s podporou umělé inteligence.

## Funkce aplikace

- Vytváření strukturovaných příprav na tělovýchovné hodiny
- Výběr škol a jejich kategorií (experimentální, semi-experimentální)
- Výběr prostředí a vybavení pro hodinu
- Nastavení rolí vedoucích jednotlivých částí hodiny
- Výběr cvičebních konstruktů
- Časové rozdělení hodiny
- Generování promptu pro AI model
- Export přípravy do PDF nebo Word formátu
- Ukládání a načítání příprav

## Instalace a spuštění

### Lokální spuštění

1. Naklonujte repozitář
   ```
   git clone <URL_REPOZITÁŘE>
   cd Aplikace_tělovýchovná_jednotka
   ```

2. Nainstalujte potřebné závislosti
   ```
   pip install -r requirements.txt
   ```

3. Spusťte aplikaci
   ```
   streamlit run app.py
   ```

### Nasazení na Streamlit Cloud

1. Forkněte tento repozitář na GitHub
2. Přihlaste se na [Streamlit Cloud](https://streamlit.io/cloud)
3. Vytvořte novou aplikaci a vyberte váš fork repozitáře
4. Nastavte potřebné tajné klíče v sekci "Secrets"

## Struktura projektu

- `app.py` - Hlavní soubor aplikace
- `requirements.txt` - Seznam závislostí
- `.streamlit/` - Konfigurace Streamlit
- `assets/` - Statické soubory (fonty, obrázky)
- `output/` - Složka pro ukládání vygenerovaných příprav

## Licence

Tento projekt je licencován pod [MIT licencí](LICENSE).

## Kontakt

Pro více informací kontaktujte autora projektu.
