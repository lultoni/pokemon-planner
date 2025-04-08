from __future__ import annotations
import requests
import re
from collections import defaultdict
from typing import List, Dict, Any, Optional, Callable, Tuple
from bs4 import BeautifulSoup

# --------------- GLOBAL VARS ---------------

list_available_pokemon = (
    ("Vulnona", 39),
    ("Shnebedeck", 28),
    ("Flunschlik", 29),
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
    # Beispiel: Suche nach Stahl-Attacken, die keine Status-Attacken sind
    return atk['Typ'] == 'Stahl' and atk['Kategorie'] != 'Status'

trainer_name = "Papella"
backup_typen = ["Fee"]

# --------------- FUNCTION DEFINITIONS ---------------

def get_pokemon_typen(pokemon_name: str) -> List[str]:
    """
    Holt die Typen eines Pokémon von seiner Pokewiki-Seite (Bearbeiten-Ansicht),
    wobei Galar-Formen priorisiert werden.
    Gibt eine Liste der Typen (Strings) zurück, z.B. ['Unlicht', 'Normal'] für Galar-Zigzachs.
    Gibt eine leere Liste zurück, wenn Typen nicht gefunden werden oder ein Fehler auftritt.
    """
    url = f"https://www.pokewiki.de/index.php?title={pokemon_name}&action=edit"
    try:
        response = requests.get(url)
        response.raise_for_status()  # Löst einen Fehler aus für HTTP-Fehlercodes

        # Text extrahieren
        match = re.search(r'<textarea[^>]+id="wpTextbox1"[^>]*>(.*?)</textarea>', response.text, re.DOTALL)
        if not match:
            print(f"⚠️ Textarea für {pokemon_name} nicht gefunden.")
            return []

        raw_text = match.group(1)

        # --- Datenstrukturen ---
        # suffix -> region_name (z.B. 'a' -> 'Galar', 'b' -> 'Alola')
        # Suffix wird kleingeschrieben gespeichert
        region_map: Dict[str, str] = {}
        # suffix -> [Typ1, Typ2] (z.B. '' -> ['Feuer', None], 'a' -> ['Unlicht', 'Normal'])
        # Suffix wird kleingeschrieben gespeichert, Typen können None sein
        type_map: Dict[str, List[Optional[str]]] = defaultdict(lambda: [None, None])

        # --- Schritt 1: Regionale Marker extrahieren ---
        # Sucht nach: |TypZusatzSUFFIX = (REGION)
        zusatz_matches = re.findall(r'\|\s*TypZusatz(\w*)\s*=\s*\(([^)]+)\)', raw_text, re.IGNORECASE)
        for suffix, region in zusatz_matches:
            region_map[suffix.lower()] = region.strip()

        # --- Schritt 2: Alle Typ-Definitionen extrahieren ---
        # Sucht nach: |Typ[2][SUFFIX] = WERT
        type_matches = re.findall(r'\|\s*Typ(2?)(\w*)\s*=\s*([^\|\n}]+)', raw_text, re.IGNORECASE)
        for is_typ2, suffix, value in type_matches:
            suffix_lower = suffix.lower()
            cleaned_value = value.strip().replace("[[", "").replace("]]", "")
            if not cleaned_value:  # Überspringe leere Werte
                continue

            type_index = 1 if is_typ2 else 0  # 0 für Typ1, 1 für Typ2
            # Überschreibe den Wert, falls er mehrfach definiert ist (letzter gewinnt)
            type_map[suffix_lower][type_index] = cleaned_value

        # --- Schritt 3: Korrekte Typen bestimmen (Galar priorisieren) ---
        galar_suffix = None
        for suffix, region in region_map.items():
            # Suche nach dem Suffix, der explizit als 'Galar' markiert ist
            if region.lower() == 'galar':
                galar_suffix = suffix
                break  # Nimm den ersten gefundenen Galar-Suffix

        final_types_list: List[str] = []
        used_source = "unbekannt" # Zur Nachverfolgung

        if galar_suffix is not None and galar_suffix in type_map:
            # Galar-Form gefunden und Typen dafür definiert?
            potential_types = type_map[galar_suffix]
            # Füge nur Typen hinzu, die nicht None sind
            final_types_list = [t for t in potential_types if t]
            if final_types_list: # Nur wenn tatsächlich Typen gefunden wurden
                used_source = f"Galar (Suffix: '{galar_suffix}')"


        if not final_types_list:
            # Keine Galar-Typen gefunden oder definiert, nutze Basis-Form (Suffix '')
            if '' in type_map:
                potential_types = type_map['']
                final_types_list = [t for t in potential_types if t]
                if final_types_list:
                    used_source = "Basis ('')"


            # Zusätzlicher Fallback, falls Basisform mit |Typ1= / |Typ2= definiert wurde (selten)
            # Dieser Fall sollte durch das Hauptregex `Typ(2?)(\w*)` bereits abgedeckt sein,
            # da es `Typ1` als `Typ` mit suffix `1` sehen würde. Aber zur Sicherheit:
            if not final_types_list:
                typ1_val = type_map.get('1', [None, None])[0]
                typ2_val = type_map.get('2', [None, None])[0] # Beachte: Typ2 wird oft ohne Suffix '2' gefunden
                temp_list = []
                if typ1_val: temp_list.append(typ1_val)
                # Suche korrekten Typ2 für Typ1 als Basis
                typ2_fallback_val = type_map.get('', [None, None])[1] # Standard Typ2
                if typ2_fallback_val:
                    if typ2_fallback_val not in temp_list: # Verhindere Duplikat wenn Typ1=Typ, Typ2=Typ2
                        temp_list.append(typ2_fallback_val)
                elif typ2_val and typ2_val not in temp_list: # Fallback auf Typ2=
                    temp_list.append(typ2_val)

                if temp_list:
                    final_types_list = temp_list
                    used_source = "Basis (Fallback 'Typ1'/'Typ2')"


        # Debug-Ausgabe (kann entfernt werden)
        # print(f"ℹ️ Typen für {pokemon_name} extrahiert aus Quelle '{used_source}': {final_types_list}")

        if not final_types_list:
            print(f"⚠️ Typen für {pokemon_name} konnten nicht final extrahiert werden (weder Galar noch Basis).")

        return final_types_list

    except requests.exceptions.RequestException as e:
        print(f"Fehler beim Abrufen der Seite für {pokemon_name}: {e}")
        return []
    except Exception as e:
        print(f"Ein unerwarteter Fehler ist beim Holen der Typen für {pokemon_name} aufgetreten: {e}")
        return []

def get_team_from_trainer(trainer_name: str) -> Optional[List[Tuple[str, int | str]]]:
    """
    Holt die Pokémon-Namen und Level aus dem Arenakampf-Abschnitt eines Trainers (z.B. Papella).
    Sucht nach Teams für das Spiel Schwert (SW).
    Wenn nichts gefunden wird, gib None zurück.
    Gibt eine Liste von Tupeln zurück: [(Name, Level), ...]. Level kann '?' sein.
    """
    url = f"https://www.pokewiki.de/{trainer_name}"
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Trainerseite nicht gefunden oder Fehler beim Abruf: {url} ({e})")
        return None

    soup = BeautifulSoup(response.content, "html.parser")

    pokemon_list_with_levels = []
    found_sw_team = False

    # Teams suchen
    teams = soup.find_all("div", class_="team")
    for team in teams:
        # Schritt 1: sicherstellen, dass das richtige Spiel (SW) gemeint ist
        game_tags_container = team.find("span", class_="hidden") # Oft sind die Tags hier drin
        if not game_tags_container:
            continue

        game_tags = game_tags_container.find_all("span", class_="sk_item")
        if not game_tags:
            continue

        is_sw_team = False
        # Überprüfen, ob 'SW' als Tag vorhanden ist und nicht 'EX' etc. dominant ist
        tag_texts = {tag.text.strip() for tag in game_tags}
        if "SW" in tag_texts and "EX" not in tag_texts and "KA" not in tag_texts and "PU" not in tag_texts: # Fokus auf SW
            is_sw_team = True

        if not is_sw_team:
            continue

        found_sw_team = True # Wir haben mindestens ein SW-Team gefunden

        # Pokémon-Daten extrahieren (sowohl aktive als auch inaktive Toggles)
        poke_divs = team.find_all("div", class_=lambda c: c and 'clicktoggle' in c, attrs={"data-type": "set"})

        for poke_div in poke_divs:
            # Basisdaten: Pokémonname, Geschlecht, Level
            header_div = poke_div.find("div", class_="header")
            if not header_div: continue # Sicherheitscheck

            # Namen extrahieren (manchmal im <a> Tag, manchmal direkt)
            name_tag = header_div.find("a")
            if name_tag:
                name = name_tag.get_text(strip=True)
            else: # Fallback, falls kein Link da ist
                text_content = header_div.get_text(separator=" ", strip=True)
                # Versuchen, bekannte Marker wie Level oder Geschlecht zu entfernen
                name = text_content.split("♀")[0].split("♂")[0].split("Lv.")[0].strip()
                # Oft steht der Name als erstes Wort da
                if ' ' in name: name = name.split()[0]

            # Level extrahieren
            level = "?"
            level_tag = header_div.find("span", title=lambda t: t and t.startswith("Level"))
            if level_tag:
                level_text = level_tag.get_text(strip=True)
                if level_text.isdigit():
                    level = int(level_text)

            # In die Liste einfügen (nur wenn Name vorhanden)
            if name:
                pokemon_list_with_levels.append((name, level))

    # Duplikate entfernen (basierend auf Name und Level) und nur zurückgeben, wenn SW-Team gefunden wurde
    if found_sw_team:
        # `dict.fromkeys` entfernt Duplikate und behält die Reihenfolge bei (ab Python 3.7)
        unique_pokemon = list(dict.fromkeys(pokemon_list_with_levels))
        return unique_pokemon
    else:
        print(f"Kein spezifisches SW-Team für {trainer_name} gefunden.")
        return None


def get_attacken_gen8_structured(pokemon_name, max_level=None):
    url = f"https://www.pokewiki.de/index.php?title={pokemon_name}/Attacken&action=edit"
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Fehler beim Abrufen der Attacken-Seite für {pokemon_name}: {e}")
        return [] # Leere Liste bei Fehler

    # Text extrahieren
    match = re.search(r'<textarea[^>]+id="wpTextbox1"[^>]*>(.*?)</textarea>', response.text, re.DOTALL)
    if not match:
        print(f"Textarea für Attacken von {pokemon_name} nicht gefunden.")
        return []

    raw_text = match.group(1).replace('&amp;nbsp;', ' ').replace('&nbsp;', ' ')

    # Alle Tabellen mit g=8 finden
    # Verbessertes Regex, um sicherzustellen, dass wir nicht über Tabellengrenzen hinaus matchen
    tables = re.findall(r'\{\{Atk-Table\|g=8\|Art=([^\|}]+).*?\}\}(.*?)(?=\{\{Atk-Table|\Z)', raw_text, re.DOTALL)

    attacken_liste = []

    for art, content in tables:
        # Regex für AtkRow, etwas fehlertoleranter bei Leerzeichen
        atk_rows = re.findall(
            r'\{\{AtkRow\s*\|\s*([^\|]*?)\s*\|\s*([^\|]+?)\s*\|\s*([^\|]+?)\s*\|\s*([^\|]+?)\s*\|\s*([^\|]*?)\s*\|\s*([^\|]*?)\s*\|\s*([^\|]*?)\s*\|\s*G=8\s*\}\}',
            content
        )
        for level, name, typ, kategorie, staerke, genauigkeit, ap in atk_rows:
            level_clean = level.strip()
            lvl = None
            # Versuch, Level zu interpretieren (Startlevel ist oft 'Start')
            if level_clean.isdigit():
                lvl = int(level_clean)
            elif level_clean.lower() == 'start':
                lvl = 1 # Behandle 'Start' wie Level 1 für die Filterung

            # Filtern nach max_level, wenn die Attacke durch Levelaufstieg erlernt wird
            if art == "Level" and max_level is not None:
                if lvl is None or lvl > max_level:
                    continue

            attacken_liste.append({
                'Pokemon': pokemon_name,
                'Art': art.strip(),
                'Level': lvl if lvl is not None else level_clean, # Behalte Originalstring, wenn keine Zahl
                'Name': name.strip(),
                'Typ': typ.strip(),
                'Kategorie': kategorie.strip(),
                'Stärke': staerke.strip(),
                'Genauigkeit': genauigkeit.strip(),
                'AP': ap.strip()
            })

    # Duplikate entfernen anhand eines eindeutigen Hash-Schlüssels der Kern-Attackendaten
    unique_attacks = {}
    for atk in attacken_liste:
        # Schlüssel basiert auf den wesentlichen Eigenschaften der Attacke
        key = (
            atk['Name'],
            atk['Typ'],
            atk['Kategorie'],
            atk['Stärke'],
            atk['Genauigkeit'],
            atk['AP']
        )
        # Behalte die Attacke mit dem niedrigsten Level (oder 'Start'), falls Duplikate existieren
        if key not in unique_attacks:
            unique_attacks[key] = atk
        else:
            # Wenn die neue Attacke ein niedrigeres Level hat (oder 'Start' ist)
            current_lvl = unique_attacks[key]['Level']
            new_lvl = atk['Level']
            # Einfache Logik: Bevorzuge numerische Level über 'Start', wenn beide vorhanden sind?
            # Oder nimm immer die erste gefundene? Wir nehmen hier die erste gefundene.
            pass # Aktuell wird die erste gefundene behalten.

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
        key_value = atk.get(schluessel, "Unbekannt")
        gruppiert[key_value].append(atk)

    # Sortiere die Gruppen nach dem Schlüssel (z.B. A-Z für Typen)
    # und die Attacken innerhalb jeder Gruppe (z.B. nach Level, dann Name)
    sortierte_gruppen = {}
    for key in sorted(gruppiert.keys()):
        # Sortiere Attacken: Priorisiere numerisches Level, dann Name
        gruppiert[key].sort(key=lambda x: (
            float('inf') if not isinstance(x.get('Level'), int) else x.get('Level'), # Unbekannte/Start Level nach hinten? Oder 0/1? -> 1 für Start
            1 if isinstance(x.get('Level'), int) and x.get('Level') > 0 else (0 if x.get('Level') == 1 else float('inf')), # Sortierhilfe für Level
            x.get('Name', '') # Sekundäre Sortierung nach Name
        ))
        sortierte_gruppen[key] = gruppiert[key]


    return sortierte_gruppen # Gebe sortiertes Dictionary zurück


def formatierte_attacken_ausgabe(
        attacken: List[Dict[str, Any]],
        felder: List[str]
) -> None:
    """
    Gibt die Attacken mit nur den gewünschten Feldern formatiert aus.

    :param attacken: Liste von Attacken (Dicts)
    :param felder: Liste von Feldnamen, die angezeigt werden sollen, z. B. ['Name', 'Typ', 'Stärke']
    """
    if not attacken:
        print("  (Keine Attacken in dieser Gruppe)")
        return

    # Bestimme die maximale Breite für jede Spalte für eine schönere Ausrichtung
    max_breiten = {feld: len(feld) for feld in felder}
    for atk in attacken:
        for feld in felder:
            max_breiten[feld] = max(max_breiten[feld], len(str(atk.get(feld, ''))))

    # Header drucken
    header = " | ".join(f"{feld:<{max_breiten[feld]}}" for feld in felder)
    print(header)
    print("-" * len(header))

    # Attacken drucken
    for atk in attacken:
        werte = [f"{str(atk.get(feld, '')):<{max_breiten[feld]}}" for feld in felder]
        print(" | ".join(werte))

# --------------- PROGRAMM RUNNING ---------------

# 1. Eigene Pokémon-Liste analysieren (falls definiert und nicht überschrieben)
print("--- Analyse EIGENER Pokémon (aus list_available_pokemon) ---")
alle_eigenen_erfuellen_kriterium = True
pokemon_daten_eigen = []

if list_available_pokemon: # Nur ausführen, wenn die Liste nicht leer ist
    for pokemon_name, max_level_individuell in list_available_pokemon:
        level_cap = max_level_individuell if nutze_individuellen_level else global_level_cap
        pokemon_typen = get_pokemon_typen(pokemon_name)
        typen_str = "/".join(pokemon_typen) if pokemon_typen else "Typ unbekannt"

        print(f"\n\n==================== {pokemon_name} ({typen_str}) (bis Level {level_cap}) ====================")

        attacken = get_attacken_gen8_structured(pokemon_name, level_cap)
        pokemon_daten_eigen.append({
            'name': pokemon_name,
            'level_cap': level_cap,
            'types': pokemon_typen,
            'attacken': attacken
        })

        gruppen = gruppiere_attacken(attacken, schluessel=grouping_key, filter_funktion=filter_funktion)

        hat_passenden_move = any(gruppen.values())  # mind. 1 Attacke in den gefilterten Gruppen vorhanden?
        if not hat_passenden_move:
            alle_eigenen_erfuellen_kriterium = False
            print(f">> ⚠️ {pokemon_name} hat KEINE passende Attacke nach Filter gefunden!")
        else:
            print(f">> Gefundene passende Attacken für {pokemon_name}:")
            for gruppen_name, liste in gruppen.items():
                print(f"\n== {grouping_key}: {gruppen_name} ==")
                formatierte_attacken_ausgabe(liste, fields_per_move)
else:
    print("Keine eigenen Pokémon in 'list_available_pokemon' definiert.")
    alle_eigenen_erfuellen_kriterium = True # Oder False? Hängt von der Logik ab. Sagen wir True, wenn Liste leer.

# Zusammenfassung für eigene Pokémon
print("\n----------------------------------------------")
if not list_available_pokemon:
    print("ℹ️ Keine eigenen Pokémon analysiert.")
elif alle_eigenen_erfuellen_kriterium:
    print(f"✅ Alle eigenen Pokémon ({len(list_available_pokemon)}) scheinen mindestens eine passende Attacke gemäß Filter zu haben.")
else:
    print(f"❌ Mindestens ein eigenes Pokémon hat KEINE passende Attacke gemäß Filter.")
print("----------------------------------------------\n")


# 2. Gegner-Team analysieren
print(f"--- Analyse GEGNER-Team ({trainer_name}) ---")
gegner_team_daten = []
aktive_filter_funktion = filter_funktion # Behalte die ursprüngliche Funktion

# Hole Pokémon-Team des Trainers
gegner_team_liste = get_team_from_trainer(trainer_name)

if gegner_team_liste:
    print(f"🎯 Gegner-Team von {trainer_name} (SW) gefunden:")
    # Liste der Gegner-Pokémon mit Typen ausgeben
    for name, level in gegner_team_liste:
        typen = get_pokemon_typen(name)
        typen_str = "/".join(typen) if typen else "Typ unbekannt"
        level_str = f"Lv. {level}" if isinstance(level, int) else f"Lv. {level}" # Handle '?' Level
        print(f"- {name} ({typen_str}) {level_str}")
        gegner_daten = {
            'name': name,
            'level': level,
            'types': typen,
            'attacken': [] # Wird später gefüllt, wenn Analyse gewünscht
        }
        gegner_team_daten.append(gegner_daten)

    # Hier könntest du jetzt eine ähnliche Analyse wie für deine Pokémon durchführen,
    # wenn du z.B. wissen willst, welche Attacken die Gegner haben könnten.
    # Beispiel (optional - auskommentieren, wenn nicht benötigt):
    print(f"\n--- Analyse der möglichen Attacken des GEGNER-Teams (bis zu ihrem Level) ---")
    alle_gegner_erfuellen_kriterium = True # Beispiel-Kriterium für Gegner
    gegner_filter = lambda atk: atk['Kategorie'] != 'Status' # Beispiel: Alle nicht-Status Attacken des Gegners anzeigen

    for daten in gegner_team_daten:
        poke_name = daten['name']
        # Gegner-Level als Cap nehmen, wenn es eine Zahl ist, sonst global_level_cap? Oder keinen Cap?
        # Wir nehmen hier das bekannte Level des Gegners als Cap. Wenn '?', dann keinen Level-Cap.
        gegner_level_cap = daten['level'] if isinstance(daten['level'], int) else None
        # Holen der Attacken für den Gegner
        gegner_attacken = get_attacken_gen8_structured(poke_name, gegner_level_cap)
        daten['attacken'] = gegner_attacken # Speichern für spätere Verwendung

        print(f"\n-- Mögliche Attacken für {poke_name} (bis {f'Level {gegner_level_cap}' if gegner_level_cap else 'höchstem Level'}) --")
        gegner_gruppen = gruppiere_attacken(gegner_attacken, schluessel="Typ", filter_funktion=gegner_filter) # Nach Typ gruppieren

        if not any(gegner_gruppen.values()):
            print(">> Keine Attacken nach Filter gefunden.")
            # alle_gegner_erfuellen_kriterium = False # Anpassen, falls nötig
        else:
            for typ, liste in gegner_gruppen.items():
                print(f"\n== Typ: {typ} ==")
                # Angepasste Felder für Gegner-Ausgabe
                formatierte_attacken_ausgabe(liste, ['Name', 'Kategorie', 'Stärke', 'Genauigkeit'])


else:
    print(f"⚠️ Kein SW-Team für {trainer_name} gefunden oder Fehler beim Abruf.")
    # Fallback: Verwende Backup-Typen für die Filterfunktion, um zu sehen,
    # welche DEINER Pokémon Attacken gegen diese Typen hätten.
    if backup_typen:
        print(f"⚠️ Verwende Backup-Typen für Filterung der EIGENEN Pokémon: {backup_typen}")
        # Passe die Filterfunktion an, um Attacken zu finden, die gegen die Backup-Typen effektiv sind
        # HINWEIS: Dies erfordert eine komplexere Logik (Typ-Effektivitäten)
        # Einfacher Ansatz: Finde Attacken mit den Backup-Typen (was nicht das Ziel ist)
        # Wir ändern hier die **aktive** Filterfunktion für die ZUSAMMENFASSUNG unten
        aktive_filter_funktion = lambda atk: atk['Typ'] in backup_typen and atk['Kategorie'] != 'Status'
        print(f"Filter für eigene Pokémon angepasst, um Attacken vom Typ {backup_typen} zu suchen.")
        # Erneute Analyse der eigenen Pokémon mit dem neuen Filter wäre hier sinnvoll, wenn gewünscht.
    else:
        print("Keine Backup-Typen definiert.")


# Finale Zusammenfassung basierend auf dem AKTIVEN Filter
# (Entweder der Originalfilter oder der angepasste wg. Backup-Typen)
print("\n\n==============================================")
print("           FINALE ZUSAMMENFASSUNG")
print("==============================================")

# Hier könntest du eine komplexere Zusammenfassung einfügen, die sowohl
# eigene Pokémon als auch das (gefundene oder angenommene) Gegnerteam berücksichtigt.

# Beispielhafte einfache Zusammenfassung basierend auf dem ursprünglichen Skript-Ziel:
if not list_available_pokemon:
    pass # Bereits oben behandelt
elif alle_eigenen_erfuellen_kriterium:
    print("✅ Alle EIGENEN Pokémon scheinen (basierend auf dem initialen Filter) passende Attacken zu haben.")
else:
    # Finde die Pokémon, die das Kriterium nicht erfüllen
    nicht_erfuellt = []
    for p_data in pokemon_daten_eigen:
        gruppen = gruppiere_attacken(p_data['attacken'], schluessel=grouping_key, filter_funktion=aktive_filter_funktion)
        if not any(gruppen.values()):
            nicht_erfuellt.append(p_data['name'])
    print(f"❌ Folgende EIGENE Pokémon haben KEINE passende Attacke gemäß dem aktiven Filter gefunden: {', '.join(nicht_erfuellt)}")


if gegner_team_liste:
    print(f"ℹ️ Gegner-Team von {trainer_name} wurde analysiert.")
    # Hier könntest du weitere Logik hinzufügen, z.B. Bedrohungsanalyse
elif backup_typen:
    print(f"ℹ️ Kein Gegner-Team gefunden, Backup-Typen ({backup_typen}) wurden berücksichtigt (Filter evtl. angepasst).")
else:
    print(f"ℹ️ Kein Gegner-Team gefunden und keine Backup-Typen vorhanden.")