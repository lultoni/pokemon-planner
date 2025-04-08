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

# --------------- GLOBAL VARS ---------------

list_available_pokemon = (
    ("Vulnona", 39),
    ("Shnebedeck", 28),
    ("Flunschlik", 29),
    ("Golbit", 33),
    ("Golbit", 33),
    ("Strepoli", 34),
    ("Pionskora", 34),
    ("Kamalm", 32),
    ("Phlegleon", 31),
    ("Psiaugon", 32),
    ("Smogon", 30),
    ("Schalellos", 30),
    ("Pelzebub", 38),
    ("Maritellit", 36),
    ("Barrakiefa", 30),
    ("Garados", 35),
    ("Zurrokex", 32),
    ("Salanga", 29),
    ("Schlaraffel", 24),
)

fields_per_move = ['Level', 'Name', 'Typ', 'Kategorie', 'Stärke', 'Genauigkeit', 'AP']
global_level_cap = 55
nutze_individuellen_level = False  # <== hier schalten!
grouping_key = "Art"
def filter_funktion(atk):
    return atk['Typ'] == 'Stahl' and atk['Kategorie'] != 'Status'

# --------------- GLOBAL VARS ---------------


alle_erfuellen_kriterium = True  # wird auf False gesetzt, wenn ein Pokémon keinen passenden Move hat

for pokemon_name, max_level_individuell in list_available_pokemon:
    level_cap = max_level_individuell if nutze_individuellen_level else global_level_cap

    print(f"\n\n\n==================== {pokemon_name} (bis Level {level_cap}) ====================")

    attacken = get_attacken_gen8_structured(pokemon_name, level_cap)

    gruppen = gruppiere_attacken(attacken, schluessel=grouping_key, filter_funktion=filter_funktion)

    hat_passenden_move = any(gruppen.values())  # mind. 1 Attacke vorhanden?
    if not hat_passenden_move:
        alle_erfuellen_kriterium = False

    if not hat_passenden_move:
        print(">> ⚠️ Kein passender Stahl-Angriff gefunden!")
    else:
        for art, liste in gruppen.items():
            print(f"\n== {art} ==")
            formatierte_attacken_ausgabe(liste, fields_per_move)

# Zusammenfassung
print("\n\n==============================================")
if alle_erfuellen_kriterium:
    print("✅ Alle Pokémon haben mindestens eine Stahl-Attacke (kein Status)!")
else:
    print("❌ Mindestens ein Pokémon hat KEINE passende Stahl-Attacke.")


