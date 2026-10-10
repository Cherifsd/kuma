@echo off
chcp 65001 >nul
title Kuma - serveur
cd /d "%~dp0"

rem --- Trouver Python ---
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY (where python >nul 2>nul && set "PY=python")
if not defined PY (
  echo.
  echo  Python n'est pas installe.
  echo  Installez-le depuis https://www.python.org/downloads/
  echo  en cochant la case "Add python.exe to PATH", puis relancez ce fichier.
  echo.
  pause
  exit /b 1
)

rem --- Premiere fois : installation ---
if not exist ".venv\Scripts\python.exe" (
  echo.
  echo  Premiere installation de Kuma. Patientez 2 a 5 minutes...
  echo.
  %PY% -m venv .venv
  if errorlevel 1 goto erreur
  ".venv\Scripts\python.exe" -m pip install --upgrade pip
  ".venv\Scripts\python.exe" -m pip install -r requirements-base.txt
  if errorlevel 1 goto erreur
)

if not exist ".env" copy ".env.example" ".env" >nul

echo.
echo  Demarrage de Kuma...
echo  Si Windows demande l'autorisation du pare-feu, cliquez sur "Autoriser".
echo.
".venv\Scripts\python.exe" -m uvicorn server:app --host 0.0.0.0 --port 8000
pause
exit /b 0

:erreur
echo.
echo  L'installation a echoue. Verifiez votre connexion Internet et relancez.
echo  Si cela recommence, faites une photo de cette fenetre et envoyez-la.
echo.
pause
exit /b 1
