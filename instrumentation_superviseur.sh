#!/bin/bash
# =====================================================================
# SUPERVISEUR — relance automatiquement l'entrainement s'il plante
# =====================================================================
# Ceci N'EST PAS un fichier du projet de base : c'est le petit script
# bash qui enveloppe instrumentation_selfplay.py pour le lancer en
# arriere-plan de facon resiliente. Copie a titre d'exemple (le vrai
# run tourne depuis ~/Puissance4/nuit_selfplay/superviseur.sh).
#
# Pourquoi un script bash autour d'un script Python ?
#   - Un `python3 script.py &` tout seul meurt si le processus crashe
#     pour une raison imprevue (erreur non rattrapee, memoire, etc.)
#   - Ce script relance automatiquement le Python s'il s'arrete avec
#     un code d'erreur (!= 0), et s'arrete lui-meme proprement si le
#     Python se termine normalement (code 0 = "j'ai fini mon travail").
#   - Grace a la REPRISE geree dans le script Python (il relit
#     sp_progress.json et poids_sp_partiel.pt au demarrage), un
#     redemarrage ne perd pas la progression : il continue pile ou il
#     s'etait arrete.
# =====================================================================

D=/home/ethanbravard/Puissance4/nuit_selfplay
cd "$D"

while true; do
  python3 -u instrumentation_selfplay.py >> sp.log 2>&1
  code=$?

  if [ $code -eq 0 ]; then
    # code 0 = le script Python a fini normalement (MAX_PARTIES atteint)
    echo "=== SUPERVISEUR: termine normalement, arret ===" >> sp.log
    break
  fi

  # code != 0 = plantage imprevu -> on relance apres une courte pause
  echo "=== SUPERVISEUR: code $code (plantage), relance dans 5s ===" >> sp.log
  sleep 5
done

# Lancement typique (detache du terminal, survit a sa fermeture) :
#   nohup bash instrumentation_superviseur.sh > wrapper.log 2>&1 &
#   disown
