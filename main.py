import requests
import re
from collections import defaultdict
from typing import List, Dict, Any, Optional, Callable
from bs4 import BeautifulSoup

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

trainer_name = "Papella"
backup_typen = ["Fee"]

# --------------- FUNCTION DEFINITIONS ---------------

def get_team_from_trainer(trainer_name: str) -> Optional[List[str]]:
    """
    Holt die Pokémon-Namen aus dem Arenakampf-Abschnitt eines Trainers (z.B. Papella).
    Wenn nichts gefunden wird, gib None zurück.
    """
    url = f"https://www.pokewiki.de/{trainer_name}"
    response = requests.get(url)
    if response.status_code != 200:
        print(f"⚠️ Trainerseite nicht gefunden: {url}")
        return None

    soup = BeautifulSoup(response.content, "html.parser")

    list_available_pokemon = []

    # Teams suchen
    teams = soup.find_all("div", class_="team")
    for team in teams:
        # Schritt 1: sicherstellen, dass das richtige Spiel (SW/SH) gemeint ist
        game_tags = team.find_all("span", class_="sk_item")
        if not game_tags:
            continue
        contains_only_sw = False
        for tag in game_tags:
            if "EX" in tag.text:
                continue
            if "SW" == tag.text.strip():
                contains_only_sw = True
        if not contains_only_sw:
            continue

        # Pokémon-Daten extrahieren
        pokes = team.find_all("div", class_="clicktoggle", attrs={"data-type": "set"}) + team.find_all("div", class_="clicktoggle clicktoggle-active", attrs={"data-type": "set"})

        for poke_div in pokes:
            # Basisdaten: Pokémonname, Geschlecht, Level
            text = poke_div.get_text(separator=" ", strip=True)
            name = text.split("♀")[0].split("♂")[0].split()[0].strip()  # Nur das erste Wort
            level = text.split("Lv.")[1].strip() if "Lv." in text else "?"

            # In die Liste einfügen
            list_available_pokemon.append((name, int(level) if level.isdigit() else level))

    # Duplikate entfernen und nur relevante Pokémon-Namen behalten
    list_available_pokemon = list(dict.fromkeys(list_available_pokemon))

    return list_available_pokemon

def get_attacken_gen8_structured(pokemon_name, max_level=None):
    url = f"https://www.pokewiki.de/index.php?title={pokemon_name}/Attacken&action=edit"
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f"Fehler beim Abrufen der Seite: {response.status_code}")

    # Text extrahieren
    match = re.search(r'<textarea[^>]+id="wpTextbox1"[^>]*>(.*?)</textarea>', response.text, re.DOTALL)
    if not match:
        raise Exception(f"Textarea nicht gefunden.\n{response.text}")

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

    # Duplikate entfernen anhand eines eindeutigen Hash-Schlüssels
    unique_attacks = {}
    for atk in attacken_liste:
        # Wir ignorieren "Art" und "Level" beim Duplikatvergleich
        key = (
            atk['Name'],
            atk['Typ'],
            atk['Kategorie'],
            atk['Stärke'],
            atk['Genauigkeit'],
            atk['AP']
        )
        if key not in unique_attacks:
            unique_attacks[key] = atk

    return list(unique_attacks.values())

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

# --------------- PROGRAMM RUNNING ---------------

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
        print(">> ⚠️ Kein passender Move nach den Filtern gefunden!")
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

# Hole Pokémon-Team des Trainers
gegner_team = get_team_from_trainer(trainer_name)

if gegner_team:
    list_available_pokemon = [(name, global_level_cap) for name in gegner_team]
    print(f"🎯 Gegner-Team von {trainer_name}: {[name for name, _ in list_available_pokemon]}")
else:
    print(f"⚠️ Kein Team gefunden – verwende Typ-Backup: {backup_typen}")
    # Filterfunktion wird hier automatisch auf Typen angepasst
    filter_funktion = lambda atk: atk['Typ'] in backup_typen and atk['Kategorie'] != 'Status'
