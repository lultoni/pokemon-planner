from __future__ import annotations

from collections import defaultdict
from typing import List, Dict, Any, Optional, Callable

import information_manager
from global_infos import *
import type_effectiveness

# --------------- FUNCTION DEFINITIONS ---------------

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

def determine_optimal_attack_types(type_chart: dict, opponent_team: List[Dict[str, Any]]) -> List[str]:
    # Hier gehen wir davon aus, dass type_chart ein Dictionary ist, in dem für jeden Angriffstyp die
    # Effektivitätswerte gegenüber einzelnen Verteidiger-Typen hinterlegt sind.
    # Erstelle zunächst eine Liste aller Angriffstypen:
    attack_types = list(type_chart.keys())
    scores = {}
    for atk_type in attack_types:
        total_multiplier = 0
        count = 0
        for opp in opponent_team:
            # Für jedes Gegner-Pokémon holen wir dessen Verteidigungstypen (als Liste)
            defense_types = opp.get('types', [])
            # get_effectiveness liefert uns den Multiplikator für den Angriffstyp gegen die Verteidigungstypen
            eff = type_effectiveness.get_effectiveness_from_type_chart(type_chart, atk_type, defense_types)
            if eff is None:
                eff = 1.0  # Standard, falls kein Wert gefunden wird
            total_multiplier += eff
            count += 1
        # Durchschnittlicher Multiplikator für diesen Angriffstyp
        avg_multiplier = total_multiplier / count if count > 0 else 1.0
        scores[atk_type] = avg_multiplier
    # Sortieren – höhere Durchschnittswerte deuten auf höhere Effektivität hin.
    sorted_types = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    # Wähle die Typen aus, deren durchschnittlicher Multiplikator > 1 liegt (also effektiv)
    optimal_types = [atype for atype, score in sorted_types if score > 1]
    return optimal_types


def main():
    global optimal_attack_types
    # 1. Gegner-Team analysieren
    print(f"--- Analyse GEGNER-Team ({opponent_trainer_name}) ---")
    gegner_team_daten = []
    aktive_filter_funktion = filter_funktion_error  # Behalte die ursprüngliche Funktion
    # Hole Pokémon-Team des Trainers
    gegner_team_liste = information_manager.get_trainer_team_from_trainer_name(opponent_trainer_name)[0]
    if gegner_team_liste:
        print(f"🎯 Gegner-Team von {opponent_trainer_name} (SW) gefunden:")
        # Liste der Gegner-Pokémon mit Typen ausgeben
        for pkm in gegner_team_liste["team"]:
            name = information_manager.get_name_from_id(pkm["id"])
            level = pkm["level"]
            typen = information_manager.get_type_of_pokemon(name)
            typen_str = "/".join(typen) if typen else "Typ unbekannt"
            level_str = f"Lv. {level}" if isinstance(level, int) else f"Lv. {level}"  # Handle '?' Level
            print(f"- {name} ({typen_str}) {level_str}")
            gegner_daten = {
                'name': name,
                'level': level,
                'types': typen,
                'attacken': []  # Wird später gefüllt, wenn Analyse gewünscht
            }
            gegner_team_daten.append(gegner_daten)
    else:
        print(f"⚠️ Kein SW-Team für {opponent_trainer_name} gefunden oder Fehler beim Abruf.")
        # Fallback: Verwende Backup-Typen für die Filterfunktion, um zu sehen,
        # welche DEINER Pokémon Attacken gegen diese Typen hätten.
        if backup_typen:
            print(f"⚠️ Verwende Backup-Typen für Filterung der EIGENEN Pokémon: {backup_typen}")
            # Passe die Filterfunktion an, um Attacken zu finden, die gegen die Backup-Typen effektiv sind
            # HINWEIS: Dies erfordert eine komplexere Logik (Typ-Effektivitäten)
            # Einfacher Ansatz: Finde Attacken mit den Backup-Typen (was nicht das Ziel ist)
            # Wir ändern hier die **aktive** Filterfunktion für die ZUSAMMENFASSUNG unten
            aktive_filter_funktion = lambda atk: ((atk['Typ'] in backup_typen
                                                   and atk['Kategorie'] != 'Status'
                                                   and is_strong_enough(atk['Stärke'], minimum_strength_move))
                                                  and is_allowed_level(atk['Level']))
            print(f"Filter für eigene Pokémon angepasst, um Attacken vom Typ {backup_typen} zu suchen.")
            # Erneute Analyse der eigenen Pokémon mit dem neuen Filter wäre hier sinnvoll, wenn gewünscht.
        else:
            print("Keine Backup-Typen definiert.")
    # --- Teamanalyse mit Typ-Effektivität ---
    type_chart = type_effectiveness.load_type_effectiveness_data("information_storage/pokemon_type_effectiveness.json")
    optimal_attack_types = determine_optimal_attack_types(type_chart, gegner_team_daten)
    if optimal_attack_types:
        print(f"Optimale Angriffs-Typen gegen {opponent_trainer_name}: {optimal_attack_types}")
        # Setze aktive_filter_funktion: Akzeptiere nur Attacken, die einen der optimalen Typen haben, und keine Status-Attacken
        aktive_filter_funktion = lambda atk: (atk['Typ'] in optimal_attack_types
                                              and atk['Kategorie'] != 'Status'
                                              and is_strong_enough(atk['Stärke'], minimum_strength_move)
                                              and is_allowed_level(atk['Level']))
    else:
        print("Keine optimalen Angriffs-Typen gefunden. Verwende Backup-Typen.")
        aktive_filter_funktion = lambda atk: (atk['Typ'] in backup_typen
                                              and atk['Kategorie'] != 'Status'
                                              and is_strong_enough(atk['Stärke'], minimum_strength_move)
                                              and is_allowed_level(atk['Level']))
    # Zusätzliche Analyse: Für jedes gegnerische Pokémon bestimmen, welche Angriffstypen am effektivsten sind
    print("\n--- Effektivste Angriffstypen pro gegnerischem Pokémon ---")
    attack_types = list(type_chart.keys())
    for opp in gegner_team_daten:
        best_multiplier = 0.0
        best_types = []
        for atk_type in attack_types:
            eff = type_effectiveness.get_effectiveness_from_type_chart(type_chart, atk_type, opp.get('types', []))
            if eff is None:
                eff = 1.0  # Standardwert, falls kein Wert vorhanden ist
            if eff > best_multiplier:
                best_multiplier = eff
                best_types = [atk_type]
            elif eff == best_multiplier:
                best_types.append(atk_type)
        opp_types = "/".join(opp.get('types', [])) if opp.get('types') else "unbekannt"
        print(
            f"- Gegen {opp['name']} ({opp_types}): optimale Angriffstypen: {best_types} (Effektivität: {best_multiplier})")
    # 2. Eigene Pokémon-Liste analysieren (falls definiert und nicht überschrieben)
    print("--- Analyse EIGENER Pokémon (aus global_infos.owned_pokemon_list) ---")
    alle_eigenen_erfuellen_kriterium = True
    pokemon_daten_eigen = []
    if owned_pokemon_list:  # Nur ausführen, wenn die Liste nicht leer ist
        for pokemon_name in owned_pokemon_list:
            level_cap = global_level_cap
            pokemon_typen = information_manager.get_type_of_pokemon(pokemon_name)
            typen_str = "/".join(pokemon_typen) if pokemon_typen else "Typ unbekannt"

            print(f"\n\n==================== {pokemon_name} ({typen_str}) (bis Level {level_cap}) ====================")

            attacken = information_manager.get_attacken_of_pokemon_structured(pokemon_name, level_cap)
            pokemon_daten_eigen.append({
                'name': pokemon_name,
                'level_cap': level_cap,
                'types': pokemon_typen,
                'attacken': attacken
            })

            gruppen = gruppiere_attacken(attacken, schluessel=grouping_key, filter_funktion=aktive_filter_funktion)

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
        print("Keine eigenen Pokémon in 'global_infos.owned_pokemon_list' definiert.")
        alle_eigenen_erfuellen_kriterium = True  # Oder False? Hängt von der Logik ab. Sagen wir True, wenn Liste leer.
    # Zusammenfassung für eigene Pokémon
    print("\n----------------------------------------------")
    if not owned_pokemon_list:
        print("ℹ️ Keine eigenen Pokémon analysiert.")
    elif alle_eigenen_erfuellen_kriterium:
        print(
            f"✅ Alle eigenen Pokémon ({len(owned_pokemon_list)}) scheinen mindestens eine passende Attacke gemäß Filter zu haben.")
    else:
        print(f"❌ Mindestens ein eigenes Pokémon hat KEINE passende Attacke gemäß Filter.")
    print("----------------------------------------------\n")
    # Finale Zusammenfassung basierend auf dem AKTIVEN Filter
    # (Entweder der Originalfilter oder der angepasste wg. Backup-Typen)
    print("\n\n==============================================")
    print("           FINALE ZUSAMMENFASSUNG")
    print("==============================================")
    # Hier könntest du eine komplexere Zusammenfassung einfügen, die sowohl
    # eigene Pokémon als auch das (gefundene oder angenommene) Gegnerteam berücksichtigt.
    # Beispielhafte einfache Zusammenfassung basierend auf dem ursprünglichen Skript-Ziel:
    if not owned_pokemon_list:
        pass  # Bereits oben behandelt
    elif alle_eigenen_erfuellen_kriterium:
        print("✅ Alle EIGENEN Pokémon scheinen (basierend auf dem initialen Filter) passende Attacken zu haben.")
    else:
        # Finde die Pokémon, die das Kriterium nicht erfüllen
        nicht_erfuellt = []
        for p_data in pokemon_daten_eigen:
            gruppen = gruppiere_attacken(p_data['attacken'], schluessel=grouping_key,
                                         filter_funktion=aktive_filter_funktion)
            if not any(gruppen.values()):
                nicht_erfuellt.append(p_data['name'])
        print(
            f"❌ Folgende EIGENE Pokémon haben KEINEN passenden Move gemäß dem aktiven Filter gefunden: {', '.join(nicht_erfuellt)}")
    if gegner_team_liste:
        print(f"ℹ️ Gegner-Team von {opponent_trainer_name} wurde analysiert.")
        # Hier könntest du weitere Logik hinzufügen, z.B. Bedrohungsanalyse
    elif backup_typen:
        print(
            f"ℹ️ Kein Gegner-Team gefunden, Backup-Typen ({backup_typen}) wurden berücksichtigt (Filter evtl. angepasst).")
    else:
        print(f"ℹ️ Kein Gegner-Team gefunden und keine Backup-Typen vorhanden.")


if __name__ == "__main__":
    main()