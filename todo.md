### Brainstorming
- Was soll überhaput gemacht werden mit dem Programm?
- Ich will global settings (auch mit run file und sowas, was wie gemacht werden soll)
- Basierend auf einem Gegner-Team soll eine Gewinnende-Strategie gefunden werden
  - Damage Calcs
  - Gegner Team einladen, entweder trainer name und spezifischer kampf oder einfach die liste der pokemon mit allen eckdaten die vorhanden sind
  - Eigene Pokemon einladen (muss detailiert sein, aber wenn es einmal drin ist, ist es geil sag ich)
  - pro gegnerpokemon schauen welches eigene pokemon mit welcher attacke am schnellsten einen kill bekommt

### Code TODOs
- Nur einmal alle Moves und Types und so fetchen, das irgendwo speichern und dann später einfach nur check ob vorhanden
- Es gibt eine TM/TP liste die man hat
- Entwicklungen mit rein machen, welche möglich sind
- Arena fight can be pulled from trainer page as well with more infos on top
- Verbessere die ausgäbe vom Programm
    - was soll überhaupt ausgegeben werden
    - Was ist das Ziel vom Programm genau -> basierend auf dem Gegnerteam in einem typechart gucken welche move-typen am besten sind und in meinen Pokemon gucken wer solche moves hat (sekundär dann wer am besten defensiv auch noch aufgestellt ist)
    - Ausgabe:
        - Gegner-team (alle pokemon und deren typing)
        - Welche typen gut offensiv und defensiv sind (pro pokemon auch maybe)
        - Alle pokemon von mir die Attacken haben die matchen und diese Attacken (kompakte ausgabe)
        - MAYBE: Jedes pokemon von mir bekommt einen defensive score (was dann aber eher auf den Attacken des Gegners basieren müsste und dafür muss ich iwwie es hinbekommen die Attacken auch noch zu Parsen und dann die infos von denen auch zu suchen (pfui, arbeit))
            - Wenn ich das hinbekommen habe kann ich sagen welches team ich am ende aufstellen sollte
            - Stab bonus maybe as well
- MAYBE: vergleichen basierend auf einem type chart ob meine pokemon auch defensiv passen zu dem gegnerischen team (dafür wird moves Parsen der Gegner gebraucht), aber auch passende moves haben um das gegnerische team auszuschalten (das zweite wird aus den moves meiner pokemon gezogen und hat vorrang beim squad bauen)
- Teste andere trainer :)


### In-Game TODOs
- finale encounter bekommen, wenn es welche gibt (nachgucken)
  - [ ] turffield -
  - [ ] treffprunkt -
  - [ ] claw city -
  - [ ] passbeck -
  - [ ] fairballey -
  - [ ] circhester -
  - [ ] milza-see (auge) -
  - [ ] wutanfall-see -
  - [ ] route-09-tunnel -
  - [ ] spikeford -
  - [ ] score city - 
- Zauberschein durch reset farmen
- Dyna-raids machen um finale level zu farmen für teams