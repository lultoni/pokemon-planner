import os

# --- BASE PROGRAMM FUNCTIONALITY (no changes required) ---

pokemon_types = [
    "Normal", "Feuer", "Wasser", "Elektro", "Pflanze", "Eis",
    "Kampf", "Gift", "Boden", "Flug", "Psycho", "Käfer",
    "Gestein", "Geist", "Drache", "Unlicht", "Stahl", "Fee"
]

HEALING_MOVES = {
    "morgengrauen","mondschein","genesung","ruheort","synthese","heilbefehl","tagedieb",
    "sandsammler","lunargebet","weichei","milchgetränk","läuterung","erholung","verzehrer",
    "heilwoge","florakur","pollenknödel","lebentropfen","dschungelheilung","giga-lichtblick",
    "wunschtraum","lunartanz","heilopfer","wasserring","verwurzler","egelsamen","vitalsegen",
    "vitalglocke","heilung","aromakur","mutschub"  # "Heilblockade" ist kein Heil-Move, daher nicht enthalten
}

POKEMON_CACHE_FILE_PATH = os.path.join('information_storage', 'pokemon_knowledge_cache.json')
ATTACK_CACHE_FILE_PATH = os.path.join('information_storage', 'attack_cache.json')

EFFECTIVENESS_GROUPS = [0.0, 0.25, 0.5, 1.0, 2.0, 4.0]
EFFECTIVENESS_LABELS = ["0×", "¼×", "½×", "1×", "2×", "4×"]

TYPE_ICON_FOLDER = "type_icons"
TYPE_ICON_FILENAME_PATTERN = "Typ-Icon_{typ}_KAPU.png"

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

default_strength_move = 10

# Weights für Berechnungen in der Analyse
w_dmg = 2.0
w_surv = 3.0
w_util = 0.5
w_expo = 1.0

owned_pokemon_list = [
    "Vulnona", "Rexblisar", "Flunschlik", "Golgantes", "Strepoli", "Piondragi",
    "Intelleon", "Psiaugon", "Smogon", "Schalellos", "Olangaar", "Maritellit",
    "Barrakiefa", "Garados", "Irokex", "Salanga", "Schlaraffel", "Laukaps",
    "Bronzong", "Snomnom", "Keifel", "Wailmer", "Kingler", "Rizeros"
]

opponent_trainer_name = "Hop 4"