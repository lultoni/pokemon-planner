import os

# --- BASE PROGRAMM FUNCTIONALITY (no changes required) ---

pokemon_types = [
    "Normal", "Feuer", "Wasser", "Elektro", "Pflanze", "Eis",
    "Kampf", "Gift", "Boden", "Flug", "Psycho", "Käfer",
    "Gestein", "Geist", "Drache", "Unlicht", "Stahl", "Fee"
]

POKEMON_CACHE_FILE_PATH = os.path.join('information_storage', 'pokemon_knowledge_cache.json')
ATTACK_CACHE_FILE_PATH = os.path.join('information_storage', 'attack_cache.json')

EFFECTIVENESS_GROUPS = [0.0, 0.25, 0.5, 1.0, 2.0, 4.0]
EFFECTIVENESS_LABELS = ["0×", "¼×", "½×", "1×", "2×", "4×"]

TYPE_ICON_FOLDER = "type_icons"
TYPE_ICON_FILENAME_PATTERN = "Typ-Icon_{typ}_KAPU.png"

# --- FROM MAIN ---

fields_per_move = ['Level', 'Name', 'Typ', 'Kategorie', 'Stärke', 'Genauigkeit', 'AP']
global_level_cap = 70
grouping_key = "Art"
minimum_strength_move = 70
ALLOW_TP_MOVES = False
# filter funktion wird nach der gegnerischen team analyse unten gemacht
def filter_funktion_error(atk):
    # Beispiel: Suche nach Stahl-Attacken, die keine Status-Attacken sind
    return ((atk['Typ'] == 'Stahl'
             and atk['Kategorie'] != 'Status'
             and is_strong_enough(atk['Stärke'], minimum_strength_move))
            and is_allowed_level(atk['Level']))
trainer_name = "asdf"
backup_typen = ['Geist', 'Unlicht', 'Feuer', 'Boden']

def is_allowed_level(level):
    if ALLOW_TP_MOVES:
        return True
    if isinstance(level, str) and level.upper().startswith("TP"):
        return False
    return True

def is_strong_enough(stärke, minimum):
    try:
        return int(stärke) >= minimum
    except (ValueError, TypeError):
        return True

# --- INDIVIDUAL LEVEL DATA (change to fit your playthrough) ---

starter_pokemon_list = [
    "Chimpep", "Chimstix", "Gortrom",
    "Hopplo", "Kickerlo", "Liberlo",
    "Memmeon", "Phlegleon", "Intelleon"
]

# Kann 1 von diesen 3 sein:
# - 0 (Pflanze)
# - 3 (Feuer)
# - 6 (Wasser)
starter_pokemon = starter_pokemon_list[6]

owned_pokemon_list = [
    "Vulnona", "Rexblisar", "Flunschlik", "Golgantes", "Strepoli", "Piondragi",
    "Intelleon", "Psiaugon", "Smogon", "Schalellos", "Olangaar", "Maritellit",
    "Barrakiefa", "Garados", "Irokex", "Salanga", "Schlaraffel", "Laukaps",
    "Bronzong", "Snomnom", "Keifel", "Wailmer", "Kingler", "Rizeros"
]