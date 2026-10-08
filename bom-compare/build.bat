@echo off
REM ==========================================================================
REM  BOM Compare - creazione dell'eseguibile Windows con PyInstaller
REM
REM  Uso:   build.bat            -> cartella dist\BOMCompare\ (avvio piu' rapido)
REM         build.bat onefile    -> singolo file dist\BOMCompare.exe
REM
REM  Se esiste la cartella "wheels" (creata con scarica_dipendenze.bat) le
REM  dipendenze vengono installate da li', senza connessione internet.
REM ==========================================================================
setlocal
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo === BOM Compare - creazione eseguibile ===
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo [ERRORE] Python non trovato. Installa Python 3.10 o superiore da python.org
    echo          e seleziona "Add Python to PATH" durante l'installazione.
    goto :fail
)

if not exist ".venv\Scripts\python.exe" (
    echo [1/4] Creazione ambiente virtuale .venv ...
    python -m venv .venv
    if errorlevel 1 goto :fail
) else (
    echo [1/4] Ambiente virtuale .venv gia' presente
)
call ".venv\Scripts\activate.bat"

echo [2/4] Installazione dipendenze ...
if exist "wheels\" (
    python -m pip install --no-index --find-links wheels -r requirements-dev.txt
) else (
    python -m pip install --upgrade pip
    python -m pip install -r requirements-dev.txt
)
if errorlevel 1 goto :fail

echo [3/4] Esecuzione test ...
python -m pytest -q
if errorlevel 1 (
    echo [ERRORE] I test non sono passati: build interrotta.
    goto :fail
)

echo [4/4] Creazione eseguibile ...
set "BOMCOMPARE_ONEFILE=0"
set "OUT=dist\BOMCompare"
if /i "%~1"=="onefile" (
    set "BOMCOMPARE_ONEFILE=1"
    set "OUT=dist"
)
python -m PyInstaller --noconfirm --clean bomcompare.spec
if errorlevel 1 goto :fail

REM File modificabili accanto all'eseguibile (config aziendale, esempi, guida)
copy /y config.json "%OUT%\" >nul
if not exist "%OUT%\sample_data" mkdir "%OUT%\sample_data"
copy /y sample_data\*.xlsx "%OUT%\sample_data\" >nul
copy /y sample_data\*.csv "%OUT%\sample_data\" >nul
copy /y README.md "%OUT%\" >nul

echo.
echo === COMPLETATO ===
echo Eseguibile: %OUT%\BOMCompare.exe
echo Per distribuire l'app copia l'intera cartella "%OUT%" sui PC aziendali.
echo.
pause
exit /b 0

:fail
echo.
echo *** Build NON riuscita. Controlla i messaggi sopra. ***
pause
exit /b 1
