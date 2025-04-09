import json



# --- Beispiel-Anwendung ---

# Lade die Tabelle (angenommen, die JSON-Datei ist im selben Verzeichnis)
type_chart = load_type_chart()

if type_chart:
    # Testfälle
    attack = "Feuer"
    defense1 = ["Pflanze", "Gift"] # Reihenfolge spielt keine Rolle mehr
    defense2 = ["Gift", "Pflanze"] # Gleiches Ergebnis erwartet
    defense3 = ["Wasser", "Boden"] # Reihenfolge spielt keine Rolle mehr
    defense4 = ["Boden", "Wasser"] # Gleiches Ergebnis erwartet
    defense5 = ["Stahl"]          # Einzeltyp
    defense6 = ["Wasser", "Fee"]  # Eine andere Kombination
    defense7 = ["KeinTyp"]        # Ungültiger Verteidiger
    attack_invalid = "Holz"     # Ungültiger Angreifer
    defense_invalid_count = ["Wasser", "Feuer", "Eis"] # Zu viele Typen

    print("-" * 20)

    # Test 1: Pflanze/Gift (unsortiert)
    eff1 = get_effectiveness(type_chart, attack, defense1)
    if eff1 is not None:
        print(f"{attack} vs. {defense1}: {eff1}x")
    else:
        print(f"{attack} vs. {defense1}: Konnte nicht ermittelt werden.")

    # Test 2: Gift/Pflanze (anders sortiert)
    eff2 = get_effectiveness(type_chart, attack, defense2)
    if eff2 is not None:
        print(f"{attack} vs. {defense2}: {eff2}x")
    else:
        print(f"{attack} vs. {defense2}: Konnte nicht ermittelt werden.")

    # Test 3: Elektro vs Wasser/Boden (unsortiert)
    attack_ele = "Elektro"
    eff3 = get_effectiveness(type_chart, attack_ele, defense3)
    if eff3 is not None:
        print(f"{attack_ele} vs. {defense3}: {eff3}x")
    else:
        print(f"{attack_ele} vs. {defense3}: Konnte nicht ermittelt werden.")

    # Test 4: Elektro vs Boden/Wasser (anders sortiert)
    eff4 = get_effectiveness(type_chart, attack_ele, defense4)
    if eff4 is not None:
        print(f"{attack_ele} vs. {defense4}: {eff4}x")
    else:
        print(f"{attack_ele} vs. {defense4}: Konnte nicht ermittelt werden.")

    # Test 5: Einzeltyp
    eff5 = get_effectiveness(type_chart, attack, defense5)
    if eff5 is not None:
        print(f"{attack} vs. {defense5}: {eff5}x")
    else:
        print(f"{attack} vs. {defense5}: Konnte nicht ermittelt werden.")

    # Test 6: Andere Kombination
    eff6 = get_effectiveness(type_chart, attack, defense6)
    if eff6 is not None:
        print(f"{attack} vs. {defense6}: {eff6}x")
    else:
        print(f"{attack} vs. {defense6}: Konnte nicht ermittelt werden.")

    # Test 7: Ungültiger Verteidiger-Typ (führt zu Schlüssel nicht gefunden)
    print("-" * 20)
    print("Teste ungültigen Verteidiger-Typ:")
    eff7 = get_effectiveness(type_chart, attack, defense7)
    if eff7 is not None:
        print(f"{attack} vs. {defense7}: {eff7}x")
    else:
        # Erwartet: Warnung und Rückgabe None
        print(f"{attack} vs. {defense7}: Konnte nicht ermittelt werden (erwartet).")


    # Test 8: Ungültiger Angreifer-Typ
    print("-" * 20)
    print("Teste ungültigen Angreifer-Typ:")
    eff8 = get_effectiveness(type_chart, attack_invalid, defense1)
    if eff8 is not None:
        print(f"{attack_invalid} vs. {defense1}: {eff8}x")
    else:
        # Erwartet: Fehler und Rückgabe None
        print(f"{attack_invalid} vs. {defense1}: Konnte nicht ermittelt werden (erwartet).")

    # Test 9: Ungültige Anzahl Verteidiger-Typen
    print("-" * 20)
    print("Teste ungültige Anzahl Verteidiger-Typen:")
    eff9 = get_effectiveness(type_chart, attack, defense_invalid_count)
    if eff9 is not None:
        print(f"{attack} vs. {defense_invalid_count}: {eff9}x")
    else:
        # Erwartet: Fehler und Rückgabe None
        print(f"{attack} vs. {defense_invalid_count}: Konnte nicht ermittelt werden (erwartet).")