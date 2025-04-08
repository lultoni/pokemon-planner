import requests
import re

def get_attacken_gen8(pokemon_name):
    url = f"https://www.pokewiki.de/index.php?title={pokemon_name}/Attacken&action=edit"
    response = requests.get(url)

    if response.status_code != 200:
        raise Exception(f"Fehler beim Abrufen der Seite: {response.status_code}")

    # Textbereich aus HTML extrahieren
    match = re.search(r'<textarea[^>]+id="wpTextbox1"[^>]*>(.*?)</textarea>', response.text, re.DOTALL)
    if not match:
        raise Exception("Textarea nicht gefunden.")

    raw_text = match.group(1).replace('&amp;nbsp;', ' ').replace('&nbsp;', ' ')

    # Nur Gen 8 herausfiltern
    gen8_blocks = re.findall(
        r'{{Atk-Table\|g=8\|Art=.*?}}(.*?){{(?:Atk-Table\|g=|/div>)',
        raw_text, re.DOTALL
    )

    attacken = []
    for block in gen8_blocks:
        atk_rows = re.findall(
            r'\{\{AtkRow\|\|([^\|]+)\|([^\|]+)\|([^\|]+)\|([^\|]*)\|([^\|]*)\|([^\|]*)\|G=8\}\}',
            block
        )
        for name, typ, kategorie, staerke, genauigkeit, ap in atk_rows:
            attacken.append({
                'Name': name.strip(),
                'Typ': typ.strip(),
                'Kategorie': kategorie.strip(),
                'Stärke': staerke.strip(),
                'Genauigkeit': genauigkeit.strip(),
                'AP': ap.strip(),
            })

    return attacken


attacken = get_attacken_gen8("Kamalm")
for atk in attacken:
    print(atk)
