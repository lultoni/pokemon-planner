import json
import sys

def load_type_chart(filename="pokemon_type_chart.json"):
    """
    Lädt die Typen-Effektivitätstabelle aus einer JSON-Datei.

    Args:
        filename (str): Der Pfad zur JSON-Datei.

    Returns:
        dict: Das geladene Dictionary mit der Typen-Effektivitätstabelle.
        None: Wenn die Datei nicht gefunden wurde, kein gültiges JSON enthält
              oder ein anderer Fehler auftritt.
    """
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            chart = json.load(f)
        print(f"Typen-Effektivitätstabelle erfolgreich aus '{filename}' geladen.")
        return chart
    except FileNotFoundError:
        print(f"Fehler: Datei '{filename}' nicht gefunden.")
        return None
    except json.JSONDecodeError:
        print(f"Fehler: Datei '{filename}' enthält kein gültiges JSON.")
        return None
    except Exception as e:
        print(f"Ein unerwarteter Fehler beim Lesen der Datei ist aufgetreten: {e}")
        return None

def get_effectiveness(type_chart, attack_type, defense_types):
    """
    Ermittelt die Effektivität einer Attacke gegen einen oder zwei Verteidiger-Typen.

    Behandelt automatisch die korrekte Schlüsselbildung für Einzel- und Doppeltypen
    (Doppeltypen werden alphabetisch sortiert für den Lookup).

    Args:
        type_chart (dict): Die geladene Typen-Effektivitätstabelle.
        attack_type (str): Der Typ der angreifenden Attacke (z.B. "Feuer").
        defense_types (list[str]): Eine Liste mit einem oder zwei Verteidiger-Typen
                                   (z.B. ["Pflanze"] oder ["Pflanze", "Gift"]).

    Returns:
        float: Der Effektivitätsmultiplikator (z.B. 0.0, 0.5, 1.0, 2.0).
        None: Wenn die Eingabe ungültig ist (z.B. falsche Anzahl an Typen,
              ungültiger Angriffstyp) oder die Kombination nicht gefunden wurde.
              Letzteres sollte bei korrekt generierter JSON nicht passieren.
    """
    if not type_chart:
        print("Fehler: Type Chart wurde nicht korrekt geladen.")
        return None

    # Überprüfe, ob defense_types eine Liste oder ein Tupel ist
    if not isinstance(defense_types, (list, tuple)):
        print(f"Fehler: defense_types muss eine Liste oder ein Tupel sein, erhalten: {type(defense_types)}")
        return None

    # Überprüfe die Anzahl der Typen in defense_types
    if not 1 <= len(defense_types) <= 2:
        print(f"Fehler: defense_types muss 1 oder 2 Typen enthalten, erhalten: {len(defense_types)}")
        return None

    # Stelle sicher, dass alle Typen in defense_types Strings sind
    if not all(isinstance(t, str) for t in defense_types):
        print(f"Fehler: Alle Elemente in defense_types müssen Strings sein, erhalten: {defense_types}")
        return None

    # Hole das Unter-Dictionary für den Angriffstyp (sicher mit .get)
    attacker_effectiveness_map = type_chart.get(attack_type)
    if not attacker_effectiveness_map:
        print(f"Fehler: Angriffstyp '{attack_type}' nicht in der Type Chart gefunden.")
        return None

    # Baue den Schlüssel für die Abfrage basierend auf der Anzahl der Verteidiger-Typen
    lookup_key = None
    if len(defense_types) == 1:
        # Einzeltyp-Verteidiger: Format "Typ, None"
        lookup_key = f"{defense_types[0]}, None"
    elif len(defense_types) == 2:
        # Doppeltyp-Verteidiger: Sortiere alphabetisch für das Format "TypA, TypB"
        type1, type2 = defense_types[0], defense_types[1]
        # Stelle sicher, dass die Typen gültig sind (optional, aber gute Praxis)
        # if type1 not in type_chart or type2 not in type_chart: # Prüft nur, ob sie als Angreifer existieren
        #     print(f"Warnung: Einer der Verteidiger-Typen '{type1}'/'{type2}' ist möglicherweise ungültig.")

        sorted_types = sorted((type1, type2))
        lookup_key = f"{sorted_types[0]}, {sorted_types[1]}"

    # Mache den Lookup im Dictionary des Angreifers
    effectiveness = attacker_effectiveness_map.get(lookup_key)

    if effectiveness is None:
        # Dieser Fall sollte eigentlich nicht auftreten, wenn die JSON korrekt ist
        # und die Typnamen übereinstimmen. Wir geben trotzdem eine Meldung aus.
        print(f"Warnung: Schlüssel '{lookup_key}' für Angreifer '{attack_type}' nicht gefunden.")
        # Hier *könnte* man einen Fallback einbauen, aber bei korrekter JSON ist er unnötig.
        # Die Logik oben stellt sicher, dass immer der korrekte, sortierte Schlüssel verwendet wird.
        return None # Oder vielleicht 1.0 als Standard zurückgeben? None ist klarer bei Fehlern.

    # Konvertiere das Ergebnis sicherheitshalber in ein float
    try:
        return float(effectiveness)
    except (ValueError, TypeError):
        print(f"Fehler: Ungültiger Effektivitätswert '{effectiveness}' für Schlüssel '{lookup_key}' bei Angreifer '{attack_type}'.")
        return None


# --- Hauptlogik ---

# Laden der Typentabelle
type_chart = load_type_chart()

# Liste der verteidigenden Pokémon (Name, Typen-Tupel)
name_liste = (
    ("Vulnona", ("Feuer",)),
    ("Rexblisar", ("Pflanze", "Eis")),
    ("Flunschlik", ("Boden", "Stahl")),
    ("Golgantes", ("Geist", "Boden")),
    ("Strepoli", ("Kampf",)),
    ("Piondragi", ("Gift", "Unlicht")),
    ("Intelleon", ("Wasser",)),
    ("Psiaugon", ("Psycho",)),
    ("Smogon", ("Gift",)),
    ("Schalellos", ("Wasser",)),
    ("Olangaar", ("Unlicht", "Fee")),
    ("Maritellit", ("Käfer", "Psycho")),
    ("Barrakiefa", ("Wasser",)),
    ("Garados", ("Wasser", "Flug")),
    ("Irokex", ("Unlicht", "Kampf")),
    ("Salanga", ("Boden",)),
    ("Schlaraffel", ("Normal",)),
    ("Laukaps", ("Käfer",)),
    ("Bronzong", ("Stahl", "Psycho")),
    ("Snomnom", ("Eis", "Käfer")),
    ("Keifel", ("Eis", "Boden")),
    ("Wailmer", ("Wasser",)),
    ("Kingler", ("Wasser",)),
    ("Rizeros", ("Boden", "Gestein")),
)

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
        for defender_name, defender_types in name_liste:
            # Initialisiere das Dictionary für die Effektivitäten der Attacken dieses Angreifers gegen diesen Verteidiger
            effectiveness_per_move = {}

            # Gehe jede Attacke des aktuellen Angreifers durch
            for attack_type in attacker_move_types:
                # Ermittle die Effektivität dieser Attacke gegen den Verteidiger
                effectiveness = get_effectiveness(type_chart, attack_type, defender_types)

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
            for d_name, d_types in name_liste:
                if d_name == defender_name:
                    defender_types_str = f" {d_types}"
                    break

            # Gib die Zeile für den Verteidiger aus
            print(f"- {defender_name}{defender_types_str} ({details_string})")


        # Fußzeile für den Angreifer
        print("=" * len(attacker_header)) # Trennlinie gleicher Länge wie die Kopfzeile

else:
    print("\nAnalyse kann nicht durchgeführt werden, da die Typen-Effektivitätstabelle nicht geladen werden konnte.")