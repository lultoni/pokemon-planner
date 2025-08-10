import sys

import global_infos
import information_manager
import type_effectiveness

# --- Hauptlogik ---

# Laden der Typentabelle
type_chart = type_effectiveness.load_type_effectiveness_data()

# TODO replace this with an access to fight data
# Liste der angreifenden Pokémon (Name, Attacken-Typen-Tupel)
attack_list = (
    ("Durengard", ("Geist", "Kampf", "Stahl")),
    ("Katapuldra", ("Geist", "Feuer", "Elektro", "Drache")),
    ("Maxax", ("Gift", "Stahl", "Drache", "Boden")),
    ("Rihornior", ("Boden", "Gestein", "Käfer", "Feuer")),
    ("Gortrom", ("Pflanze", "Unlicht", "Boden")),
    ("Glurak", ("Feuer", "Flug", "Pflanze", "Gestein")),
)

# Dictionary, um die detaillierten Effektivitäten pro Angreifer/Verteidiger zu speichern
# Struktur: { attacker_name: { defender_name: { attack_type: effectiveness, ... }, ... }, ... }
detailed_effectiveness = {}

# --- ANSI Color Codes ---
# Prüfen, ob das Terminal wahrscheinlich Farben unterstützt
# (Einfache Prüfung - funktioniert möglicherweise nicht in allen Umgebungen, z.B. Dateiumleitung)
supports_color = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()
supports_color = True

# Farben definieren (nur verwenden, wenn unterstützt)
COLOR = {
    "RED": "\033[91m" if supports_color else "",        # Super effektiv (> 1.0)
    "GREEN": "\033[92m" if supports_color else "",      # Nicht sehr effektiv (< 1.0, > 0)
    "YELLOW": "\033[93m" if supports_color else "",     # Neutral (== 1.0) - Optional, könnte auch default sein
    "BLUE": "\033[94m" if supports_color else "",       # Immun (== 0.0)
    "GREY": "\033[90m" if supports_color else "",       # N/A (Nicht verfügbar) - Optional
    "RESET": "\033[0m" if supports_color else "",       # Reset aller Formatierungen
}
# --- Ende ANSI Color Codes ---


# Nur fortfahren, wenn die Typentabelle erfolgreich geladen wurde
if type_chart:
    print("\n--- Analyse der detaillierten Pokémon-Effektivitäten ---")

    # Gehe jeden Angreifer durch
    for attacker_name, attacker_move_types in attack_list:
        # Initialisiere das Unter-Dictionary für diesen Angreifer
        effectiveness_for_this_attacker = {}

        # Gehe jedes verteidigende Pokémon durch
        for defender_name in global_infos.owned_pokemon_list:
            # Initialisiere das Dictionary für die Effektivitäten der Attacken dieses Angreifers gegen diesen Verteidiger
            effectiveness_per_move = {}

            # Gehe jede Attacke des aktuellen Angreifers durch
            for attack_type in attacker_move_types:
                # Ermittle die Effektivität dieser Attacke gegen den Verteidiger
                effectiveness = type_effectiveness.get_effectiveness(type_chart, attack_type, information_manager.get_type_of_pokemon(defender_name))

                # Speichere die Effektivität (oder 'N/A' bei Fehler)
                if effectiveness is None:
                    effectiveness_per_move[attack_type] = 'N/A'
                else:
                    effectiveness_per_move[attack_type] = effectiveness

            # Speichere die gesammelten Effektivitäten für diesen Verteidiger unter dem Angreifer
            effectiveness_for_this_attacker[defender_name] = effectiveness_per_move

        # Speichere die Ergebnisse für den aktuellen Angreifer im Haupt-Dictionary
        detailed_effectiveness[attacker_name] = effectiveness_for_this_attacker

    # Ausgabe der Ergebnisse im gewünschten Format, jetzt mit Sortierung und Farben
    print("\n\n--- Ergebnis: Detaillierte Effektivitäten pro Angreifer (sortiert von Bester zu Schlechtester Verteidigung) ---")
    for attacker_name, defender_effectiveness_map in detailed_effectiveness.items():
        attacker_header = f"=== {attacker_name} ==="
        print(f"\n{attacker_header}") # Kopfzeile für den Angreifer

        # --- Sortierlogik (unverändert) ---
        def calculate_sort_score(defender_item_tuple):
            move_effectiveness_map = defender_item_tuple[1]
            total_score = 0.0
            calculation_possible = True
            for effectiveness in move_effectiveness_map.values():
                if isinstance(effectiveness, (int, float)):
                    total_score += effectiveness
                else:
                    calculation_possible = False
                    break
            return total_score if calculation_possible else float('inf')

        sorted_defenders = sorted(defender_effectiveness_map.items(), key=calculate_sort_score)
        # --- Ende Sortierlogik ---


        # Gehe durch die *sortierte* Liste der Verteidiger
        for defender_name, move_effectiveness_map in sorted_defenders:
            # Baue den String für die Effektivitätsdetails zusammen
            details_parts = []
            # Sortiere die Attacken-Typen für eine konsistente Reihenfolge in der Ausgabe
            sorted_moves = sorted(move_effectiveness_map.items())

            # --- NEU: Farbige Ausgabe der Effektivitäten ---
            for move, eff in sorted_moves:
                color_code = ""
                eff_str = str(eff) # Standard-String-Repräsentation

                if isinstance(eff, (int, float)):
                    if eff > 1.0:
                        color_code = COLOR["RED"]
                    elif eff == 1.0:
                        # Optional: Farbe für neutral oder keine Farbe
                        # color_code = COLOR["YELLOW"] # Gelb für Neutral
                        color_code = "" # Keine spezielle Farbe für Neutral
                    elif eff == 0.0:
                        color_code = COLOR["BLUE"]
                    elif eff < 1.0: # Hier sind Werte zwischen 0 und 1
                        color_code = COLOR["GREEN"]
                    # Optional: Formatierung der Zahl (z.B. auf eine Nachkommastelle)
                    # eff_str = f"{eff:.1f}"
                else: # Behandlung für 'N/A'
                    color_code = COLOR["GREY"] # Blau für 'N/A' oder "" für keine Farbe
                    eff_str = "N/A" # Stelle sicher, dass 'N/A' angezeigt wird

                # Füge den formatierten Teil mit Farbe hinzu
                details_parts.append(f"{move}: {color_code}{eff_str}{COLOR['RESET']}")
            # --- Ende Farbige Ausgabe ---

            details_string = ", ".join(details_parts)

            # Finde die Typen des Verteidigers für die Ausgabe (unverändert)
            defender_types_str = ""
            for d_name in global_infos.owned_pokemon_list:
                if d_name == defender_name:
                    defender_types_str = f" {information_manager.get_type_of_pokemon(d_name)}"
                    break

            # Gib die Zeile für den Verteidiger aus
            print(f"- {defender_name}{defender_types_str} ({details_string})")


        # Fußzeile für den Angreifer
        print("=" * len(attacker_header)) # Trennlinie gleicher Länge wie die Kopfzeile

else:
    print("\nAnalyse kann nicht durchgeführt werden, da die Typen-Effektivitätstabelle nicht geladen werden konnte.")