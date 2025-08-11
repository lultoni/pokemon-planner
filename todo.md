UI-Things:
- 

-----------------------

- ui für overview screen (von eingestellten sachen und was die analyse sagt)
- ui für das suchen von gegnerischen kämpfen
- ui für das eingeben von eigenen pokemon (die man besitzt)
- so einen screen für die fight-analysis mit "can hit super-effective, can't be hit super-effective" (und was diese moves sind die super-effektiv-hitten)


BATTLE JSON GENERATOR MUSS BEI JEDEM RUN AUSGEFÜHRT WERDEN WEGEN STARTER!!!
-> oder wenn der starter anders ist als davor oder wenn er im ui geändert wird ig

-----------------------

was machen die Dateien:
- defense calc
    - hat das gegnerische team
    - schaut welche von gegner-Attacken die
      eigenen pokemon wie effektiv treffen
      kann
    - gibt detaillierte liste pro Gegner
      pokemon aus
    - goal: defensiv am besten passende
      pokemon finden gegen gegnerisches team
- dual type effectivness gui
    - implementation of type weaknesses calc
    - goal: show weakness of type combi
- global info
    - settings for Programm pretty much
- information manager
    - can be called to give back every
      needed information for rest of
      Programm
- main (right now)
    - what types are the opponents pkm
    - what are their weaknesses
    - which moves do my pkm have that hit
      that