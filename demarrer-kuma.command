#!/bin/bash
# Kuma — démarrage en double-clic (Mac) ou ./demarrer-kuma.command (Linux)
cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 n'est pas installé : https://www.python.org/downloads/"
  read -r -p "Appuyez sur Entrée pour fermer."
  exit 1
fi

if [ ! -x .venv-unix/bin/python ]; then
  echo "Première installation de Kuma. Patientez 2 à 5 minutes…"
  python3 -m venv .venv-unix && .venv-unix/bin/python -m pip install --upgrade pip \
    && .venv-unix/bin/python -m pip install -r requirements-base.txt || {
      echo "L'installation a échoué. Vérifiez votre connexion Internet et relancez."
      read -r -p "Appuyez sur Entrée pour fermer."; exit 1; }
fi

[ -f .env ] || cp .env.example .env
.venv-unix/bin/python -m uvicorn server:app --host 0.0.0.0 --port 8000
