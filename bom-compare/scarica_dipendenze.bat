@echo off
REM ==========================================================================
REM  Scarica i pacchetti necessari nella cartella "wheels" (richiede internet
REM  UNA SOLA VOLTA, su un PC qualsiasi). Copiando poi l'intera cartella del
REM  progetto su un PC senza internet, build.bat installera' tutto offline.
REM ==========================================================================
cd /d "%~dp0"
python -m pip download -r requirements-dev.txt -d wheels
if errorlevel 1 (
    echo [ERRORE] Download non riuscito.
) else (
    echo Pacchetti salvati nella cartella "wheels".
)
pause
