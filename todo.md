transform this into a web app!
-> on demand github webapp?
--> how do cookies work / can i save the data of own pkm and selection and calcs in there?
--> or do it need to save it in a file which you can upload?

UI-Things:
- type effektivitäts ui als einen der tabs dort einfügen
- own pokemon settings
  - starter pokemon selection
  - tabelle von eigenen pokemon
- pokemon info view
- oppoent data view (and selector of opponent)
- raw data view of:
  - (remind of levelcap here)
  - best moves player to opponent
  - best moves opponent to player
  - show both with calculation
- own calculation screen of expected damage
  - select own pokemon and opponent
    - funny little button in the middle with arrow that shows in which direction the move looks
  - select move
  - see the calc and result of it
- battle analysis screen
  - notice about max level searched
  - show each opponent pkm
    - per pokemon make a scrollable list of my own pokemon
      - name
      - best attack with damage
      - best incoming attack with damage
      - faster or slower than opp "You're [faster/slower] / Speed Tie"

- global infos
  - (weights für die analyse)
  - [IMPLEMENT] level cap für das suchen der moves
    - toggle ob einfach max level von gegnerischen trainer genommen werden soll
  - [IMPLEMENT] zucht moves auch nehmen?
- main 
  - [IMPLEMENT] save every calc somewhere and only recalc when called
  - [IMPLEMENT] better utility scoring with looking at status moves and assigning categories and ratings inside those
  - [IMPLEMENT] do we really need exposure score? it want to look at survivability against the whole team mainly

-----------------------

- ui für overview screen (von eingestellten sachen und was die analyse sagt)
- ui für das suchen von gegnerischen kämpfen
- ui für das eingeben von eigenen pokemon (die man besitzt)
- so einen screen für die fight-analysis mit "can hit super-effective, can't be hit super-effective" (und was diese moves sind die super-effektiv-hitten)


BATTLE JSON GENERATOR MUSS BEI JEDEM RUN AUSGEFÜHRT WERDEN WEGEN STARTER!!!
-> oder wenn der starter anders ist als davor oder wenn er im ui geändert wird ig