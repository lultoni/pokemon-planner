import requests
import re

def get_attacken_gen8_sortiert(pokemon_name, max_level=None):
    url = f"https://www.pokewiki.de/index.php?title={pokemon_name}/Attacken&action=edit"
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f"Fehler beim Abrufen der Seite: {response.status_code}")

    # Text extrahieren
    match = re.search(r'<textarea[^>]+id="wpTextbox1"[^>]*>(.*?)</textarea>', response.text, re.DOTALL)
    if not match:
        raise Exception("Textarea nicht gefunden.")

    raw_text = match.group(1).replace('&amp;nbsp;', ' ').replace('&nbsp;', ' ')

    # Alle Tabellen mit g=8 finden
    tables = re.findall(r'{{Atk-Table\|g=8\|Art=([^\|}]+).*?}}(.*?)(?={{Atk-Table|\Z)', raw_text, re.DOTALL)

    attacken_pro_art = {}

    for art, content in tables:
        atk_rows = re.findall(
            r'\{\{AtkRow\|([^\|]*)\|([^\|]+)\|([^\|]+)\|([^\|]+)\|([^\|]*)\|([^\|]*)\|([^\|]*)\|G=8\}\}',
            content
        )
        attacken = []
        for level, name, typ, kategorie, staerke, genauigkeit, ap in atk_rows:
            level_clean = level.strip()
            try:
                lvl = int(level_clean)
            except ValueError:
                lvl = None  # z. B. bei Zucht, TM, etc.

            if art == "Level" and max_level is not None:
                if lvl is None or lvl > max_level:
                    continue  # Level zu hoch oder nicht parsbar

            attacken.append({
                'Level': lvl,
                'Name': name.strip(),
                'Typ': typ.strip(),
                'Kategorie': kategorie.strip(),
                'Stärke': staerke.strip(),
                'Genauigkeit': genauigkeit.strip(),
                'AP': ap.strip()
            })

        attacken_pro_art[art] = attacken

    return attacken_pro_art

attacken = get_attacken_gen8_sortiert("Kamalm", max_level=35)

for art, liste in attacken.items():
    print(f"\n== {art} ==")
    for atk in liste:
        print(atk)
