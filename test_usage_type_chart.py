# --- Beispiel: Wie man die JSON-Datei später lädt ---
import json

def load_type_chart(filename="pokemon_type_chart.json"):
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

# Später in deinem anderen Skript:
type_chart = load_type_chart()
if type_chart:
    # Beispielabfrage: Wie effektiv ist Feuer gegen Pflanze/Gift?
    effectiveness = type_chart["Feuer"].get("Pflanze, Gift", None) # .get ist sicher, falls Schlüssel fehlt
    if effectiveness is not None:
         print(f"Feuer vs. Pflanze/Gift: {effectiveness}x") # Erwartet: 2.0
    else:
         print("Kombination 'Pflanze, Gift' nicht gefunden.")

    # Beispielabfrage: Wie effektiv ist Elektro gegen Wasser/Boden?
    effectiveness = type_chart["Elektro"].get("Boden, Wasser", None) # Alphabetisch sortiert!
    if effectiveness is not None:
         print(f"Elektro vs. Wasser/Boden: {effectiveness}x") # Erwartet: 0.0
    else:
         print("Kombination 'Boden, Wasser' nicht gefunden.")