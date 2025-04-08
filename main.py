import requests
import re

def get_attacken(pokemon_name, generation='8'):
    url = f"https://www.pokewiki.de/index.php?title={pokemon_name}/Attacken&action=edit"
    response = requests.get(url)

    if response.status_code != 200:
        raise Exception(f"Fehler beim Abrufen der Seite: {response.status_code}")

    # HTML parsen und den Textbereich extrahieren
    html_text = response.text
    textarea_content = re.search(r'<textarea[^>]+id="wpTextbox1"[^>]*>(.*?)</textarea>', html_text, re.DOTALL)

    if not textarea_content:
        raise Exception("Textarea nicht gefunden!")

    raw_text = textarea_content.group(1)

    # Text dekodieren (HTML-Entities)
    raw_text = raw_text.replace('&amp;nbsp;', ' ').replace('&nbsp;', ' ')

    # Optional: Nur den relevanten Bereich für die gewünschte Generation
    gen_block = re.search(rf'== {generation}\. Generation ==(.*?)==', raw_text, re.DOTALL)
    relevant_text = gen_block.group(1) if gen_block else raw_text

    # Alle Attackenzeilen finden
    atk_rows = re.findall(r'\{\{AtkRow\|\|([^\|]+)\|([^\|]+)\|([^\|]+)\|([^\|]*)\|([^\|]*)\|([^\|]*)\|G=' + generation + r'\}\}', relevant_text)

    attacken = []
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

attacken = get_attacken("Kamalm", '8')
for atk in attacken:
    print(atk)
