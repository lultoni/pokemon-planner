import requests
import re
from collections import defaultdict
from typing import List, Dict, Any, Optional, Callable

def get_attacken_gen8_structured(pokemon_name, max_level=None):
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

    attacken_liste = []

    for art, content in tables:
        atk_rows = re.findall(
            r'\{\{AtkRow\|([^\|]*)\|([^\|]+)\|([^\|]+)\|([^\|]+)\|([^\|]*)\|([^\|]*)\|([^\|]*)\|G=8\}\}',
            content
        )
        for level, name, typ, kategorie, staerke, genauigkeit, ap in atk_rows:
            level_clean = level.strip()
            try:
                lvl = int(level_clean)
            except ValueError:
                lvl = None

            if art == "Level" and max_level is not None:
                if lvl is None or lvl > max_level:
                    continue

            attacken_liste.append({
                'Pokemon': pokemon_name,
                'Art': art,
                'Level': lvl,
                'Name': name.strip(),
                'Typ': typ.strip(),
                'Kategorie': kategorie.strip(),
                'Stärke': staerke.strip(),
                'Genauigkeit': genauigkeit.strip(),
                'AP': ap.strip()
            })

    return attacken_liste

def gruppiere_attacken(
        attacken: List[Dict[str, Any]],
        schluessel: str,
        filter_funktion: Optional[Callable[[Dict[str, Any]], bool]] = None
        ) -> Dict[str, List[Dict[str, Any]]]:
    """
    Gruppiert Attacken nach dem angegebenen Schlüssel (z.B. 'Art', 'Typ', 'Kategorie').

    :param attacken: Liste der Attacken (strukturierte Dicts)
    :param schluessel: Nach welchem Feld gruppiert werden soll
    :param filter_funktion: Optional: Funktion, die eine Attacke filtert (z.B. nur physisch, nur Wasser etc.)
    :return: Dictionary: {Gruppenwert: [Attacken]}
    """
    gruppiert = defaultdict(list)

    for atk in attacken:
        if filter_funktion and not filter_funktion(atk):
            continue
        key = atk.get(schluessel, "Unbekannt")
        gruppiert[key].append(atk)

    return dict(gruppiert)

def formatierte_attacken_ausgabe(
        attacken: List[Dict[str, Any]],
        felder: List[str]
        ) -> None:
    """
    Gibt die Attacken mit nur den gewünschten Feldern formatiert aus.

    :param attacken: Liste von Attacken (Dicts)
    :param felder: Liste von Feldnamen, die angezeigt werden sollen, z. B. ['Name', 'Typ', 'Stärke']
    """
    for atk in attacken:
        werte = [f"{feld}: {atk.get(feld, '')}" for feld in felder]
        print(" | ".join(werte))

list_available_pokemon = (
    ("Kamalm", 35),
    #("Garados", 33),
    #("Vulnona", 36),
)
fields_per_move = ['Level', 'Name', 'Typ', 'Stärke', 'Genauigkeit', 'AP']

for pokemon_name, max_level in list_available_pokemon:
    print(f"\n\n\n==================== {pokemon_name} ====================")

    attacken = get_attacken_gen8_structured(pokemon_name, max_level)

    # Beispiel mit Filter: Nur physische Attacken, gruppiert nach Typ
    filter_funktion = lambda atk: atk['Kategorie'] == 'Physisch'
    group_key = "Typ"
    gruppen = gruppiere_attacken(attacken, schluessel=group_key, filter_funktion=filter_funktion)

    for key, liste in gruppen.items():
        print(f"\n== {key} ==")
        formatierte_attacken_ausgabe(liste, fields_per_move)

