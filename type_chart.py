# -*- coding: utf-8 -*-
import json
from collections import defaultdict

# Liste aller Pokémon-Typen auf Deutsch
pokemon_typen = [
    "Normal", "Feuer", "Wasser", "Elektro", "Pflanze", "Eis",
    "Kampf", "Gift", "Boden", "Flug", "Psycho", "Käfer",
    "Gestein", "Geist", "Drache", "Unlicht", "Stahl", "Fee"
]

# Basis-Effektivitätstabelle (Angreifer -> Verteidiger -> Multiplikator)
# Fehlende Einträge bedeuten eine Effektivität von 1 (neutral)
base_effectiveness = {
    # Angreifer: Verteidiger: Multiplikator
    "Normal":  {"Gestein": 0.5, "Geist": 0,   "Stahl": 0.5},
    "Feuer":   {"Feuer": 0.5, "Wasser": 0.5, "Pflanze": 2,   "Eis": 2,   "Käfer": 2,   "Gestein": 0.5, "Drache": 0.5, "Stahl": 2},
    "Wasser":  {"Feuer": 2,   "Wasser": 0.5, "Pflanze": 0.5, "Boden": 2,   "Gestein": 2,   "Drache": 0.5},
    "Elektro": {"Wasser": 2,   "Elektro": 0.5,"Pflanze": 0.5, "Boden": 0,   "Flug": 2,   "Drache": 0.5},
    "Pflanze": {"Feuer": 0.5, "Wasser": 2,   "Pflanze": 0.5, "Gift": 0.5, "Boden": 2,   "Flug": 0.5, "Käfer": 0.5, "Gestein": 2, "Drache": 0.5, "Stahl": 0.5},
    "Eis":     {"Feuer": 0.5, "Wasser": 0.5, "Pflanze": 2,   "Eis": 0.5, "Boden": 2,   "Flug": 2,   "Drache": 2,   "Stahl": 0.5},
    "Kampf":   {"Normal": 2,   "Eis": 2,   "Gift": 0.5, "Flug": 0.5, "Psycho": 0.5, "Käfer": 0.5, "Gestein": 2,   "Geist": 0,   "Unlicht": 2, "Stahl": 2,   "Fee": 0.5},
    "Gift":    {"Pflanze": 2,   "Gift": 0.5, "Boden": 0.5, "Käfer": 1,   "Gestein": 0.5, "Geist": 0.5, "Stahl": 0,   "Fee": 2},
    "Boden":   {"Feuer": 2,   "Elektro": 2, "Pflanze": 0.5, "Gift": 2,   "Flug": 0,   "Käfer": 0.5, "Gestein": 2,   "Stahl": 2},
    "Flug":    {"Elektro": 0.5,"Pflanze": 2,   "Kampf": 2,   "Käfer": 2,   "Gestein": 0.5, "Stahl": 0.5},
    "Psycho":  {"Kampf": 2,   "Gift": 2,   "Psycho": 0.5, "Unlicht": 0, "Stahl": 0.5},
    "Käfer":   {"Feuer": 0.5, "Pflanze": 2,   "Kampf": 0.5, "Gift": 0.5, "Flug": 0.5, "Psycho": 2,   "Geist": 0.5, "Unlicht": 2, "Stahl": 0.5, "Fee": 0.5},
    "Gestein": {"Feuer": 2,   "Eis": 2,   "Kampf": 0.5, "Boden": 0.5, "Flug": 2,   "Käfer": 2,   "Stahl": 0.5},
    "Geist":   {"Normal": 0,   "Psycho": 2,   "Geist": 2,   "Unlicht": 0.5},
    "Drache":  {"Drache": 2,   "Stahl": 0.5, "Fee": 0},
    "Unlicht": {"Kampf": 0.5, "Psycho": 2,   "Geist": 2,   "Unlicht": 0.5, "Fee": 0.5},
    "Stahl":   {"Eis": 2,   "Gestein": 2,   "Fee": 2,   "Feuer": 0.5, "Wasser": 0.5, "Elektro": 0.5, "Stahl": 0.5},
    "Fee":     {"Kampf": 2,   "Gift": 0.5, "Drache": 2,   "Unlicht": 2, "Feuer": 0.5, "Stahl": 0.5},
}

# Vervollständige die Basis-Effektivitätstabelle: Jeder Typ gegen sich selbst ist standardmäßig 1,
# es sei denn, es ist oben anders definiert. Und alle anderen nicht definierten Interaktionen sind auch 1.
for attacker in pokemon_typen:
    if attacker not in base_effectiveness:
        base_effectiveness[attacker] = {} # Initialisiere, falls der Angreifer keine Schwächen/Resistenzen hat
    for defender in pokemon_typen:
        if defender not in base_effectiveness[attacker]:
            base_effectiveness[attacker][defender] = 1.0 # Setze Standard-Effektivität auf 1

# --- Erstelle die vollständige Tabelle ---
full_type_chart = {}

# Gehe jeden möglichen Angriffstyp durch
for attacker_type in pokemon_typen:
    defending_effectiveness = {} # Hier speichern wir Effektivität gegen alle Verteidiger-Kombis

    # Gehe alle möglichen Verteidiger-Typenkombinationen durch
    processed_dual_types = set() # Um doppelte (wie Wasser/Feuer vs Feuer/Wasser) zu vermeiden

    for type1 in pokemon_typen:
        # Verteidiger mit Einzeltyp
        defender_key_single = f"{type1}, None"
        effectiveness_single = base_effectiveness[attacker_type][type1]
        defending_effectiveness[defender_key_single] = effectiveness_single

        # Verteidiger mit Doppeltyp
        for type2 in pokemon_typen:
            if type1 == type2:
                continue # Schon als Einzeltyp behandelt

            # Sortiere Typen alphabetisch für konsistenten Schlüssel (z.B. "Feuer, Wasser")
            sorted_types = tuple(sorted((type1, type2)))
            defender_key_dual = f"{sorted_types[0]}, {sorted_types[1]}"

            # Nur einmal pro Paar berechnen
            if defender_key_dual in processed_dual_types:
                continue

            # Berechne kombinierte Effektivität
            effectiveness1 = base_effectiveness[attacker_type][sorted_types[0]]
            effectiveness2 = base_effectiveness[attacker_type][sorted_types[1]]
            combined_effectiveness = effectiveness1 * effectiveness2

            defending_effectiveness[defender_key_dual] = combined_effectiveness
            processed_dual_types.add(defender_key_dual)

    # Füge das Ergebnis für diesen Angreifer zur Haupttabelle hinzu
    full_type_chart[attacker_type] = defending_effectiveness

# --- Speichere die Tabelle als JSON-Datei ---
output_filename = "pokemon_type_chart.json"
try:
    with open(output_filename, 'w', encoding='utf-8') as f:
        # json.dump schreibt das Python-Dictionary in die Datei
        # indent=4 sorgt für eine schöne, lesbare Formatierung
        # ensure_ascii=False erlaubt Zeichen wie "ä", "ü", "ö" direkt in der JSON
        json.dump(full_type_chart, f, indent=4, ensure_ascii=False, sort_keys=True) # sort_keys für konsistente Reihenfolge

    print(f"Die vollständige Typen-Effektivitätstabelle wurde erfolgreich in '{output_filename}' gespeichert.")

except IOError as e:
    print(f"Fehler beim Schreiben der Datei '{output_filename}': {e}")
except Exception as e:
    print(f"Ein unerwarteter Fehler ist aufgetreten: {e}")


# --- Beispiel: Wie man die JSON-Datei später lädt ---
# import json
#
# def load_type_chart(filename="pokemon_type_chart.json"):
#     try:
#         with open(filename, 'r', encoding='utf-8') as f:
#             chart = json.load(f)
#         print(f"Typen-Effektivitätstabelle erfolgreich aus '{filename}' geladen.")
#         return chart
#     except FileNotFoundError:
#         print(f"Fehler: Datei '{filename}' nicht gefunden.")
#         return None
#     except json.JSONDecodeError:
#         print(f"Fehler: Datei '{filename}' enthält kein gültiges JSON.")
#         return None
#     except Exception as e:
#         print(f"Ein unerwarteter Fehler beim Lesen der Datei ist aufgetreten: {e}")
#         return None
#
# # Später in deinem anderen Skript:
# # type_chart = load_type_chart()
# # if type_chart:
# #     # Beispielabfrage: Wie effektiv ist Feuer gegen Pflanze/Gift?
# #     effectiveness = type_chart["Feuer"].get("Pflanze, Gift", None) # .get ist sicher, falls Schlüssel fehlt
# #     if effectiveness is not None:
# #          print(f"Feuer vs. Pflanze/Gift: {effectiveness}x") # Erwartet: 2.0
# #     else:
# #          print("Kombination 'Pflanze, Gift' nicht gefunden.")
# #
# #     # Beispielabfrage: Wie effektiv ist Elektro gegen Wasser/Boden?
# #     effectiveness = type_chart["Elektro"].get("Boden, Wasser", None) # Alphabetisch sortiert!
# #     if effectiveness is not None:
# #          print(f"Elektro vs. Wasser/Boden: {effectiveness}x") # Erwartet: 0.0
# #     else:
# #          print("Kombination 'Boden, Wasser' nicht gefunden.")