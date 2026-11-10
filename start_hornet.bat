@echo off
setlocal EnableExtensions EnableDelayedExpansion

title HornetAI Startup

set "ROOT=%~dp0"
set "TTS_DIR=%ROOT%tts"

echo.
echo ========================================
echo          HORNETAI STARTUP
echo ========================================
echo.

:: -----------------------------------------
:: 1. Docker Desktop
:: -----------------------------------------

echo [1/5] Checking Docker Desktop...

tasklist /FI "IMAGENAME eq Docker Desktop.exe" 2>NUL | find /I "Docker Desktop.exe" >NUL

if errorlevel 1 (
    echo Starting Docker Desktop...

    if exist "%ProgramFiles%\Docker\Docker\Docker Desktop.exe" (
        start "" "%ProgramFiles%\Docker\Docker\Docker Desktop.exe"
    ) else (
        echo ERROR: Docker Desktop not found.
        goto :error
    )
) else (
    echo Docker Desktop is running.
)

echo Waiting for Docker engine...
set /a COUNT=0

:docker_wait
docker info >NUL 2>&1
if not errorlevel 1 goto :docker_ready

set /a COUNT+=1
if !COUNT! GEQ 60 (
    echo ERROR: Docker engine failed to start.
    goto :error
)

timeout /t 2 /nobreak >NUL
goto :docker_wait

:docker_ready
echo Docker engine is ready.

:: -----------------------------------------
:: 2. Ollama
:: -----------------------------------------

echo.
echo [2/5] Checking Ollama...

curl.exe -fsS --max-time 3 http://127.0.0.1:11434/api/tags >NUL 2>&1

if errorlevel 1 (
    echo Ollama is not responding. Starting Ollama...
    start "HornetAI Ollama" /min cmd /c "ollama serve"
)

set /a COUNT=0

:ollama_wait
curl.exe -fsS --max-time 3 http://127.0.0.1:11434/api/tags >NUL 2>&1
if not errorlevel 1 goto :ollama_ready

set /a COUNT+=1
if !COUNT! GEQ 30 (
    echo ERROR: Ollama failed to start.
    goto :error
)

timeout /t 2 /nobreak >NUL
goto :ollama_wait

:ollama_ready
echo Ollama API is ready.

:: -----------------------------------------
:: 3. SearXNG
:: -----------------------------------------

echo.
echo [3/5] Checking SearXNG on port 8888...

set /a COUNT=0

:searx_wait
set "HTTP_CODE="

for /f %%H in ('curl.exe -s -o NUL -w "%%{http_code}" --max-time 3 http://127.0.0.1:8888/') do (
    set "HTTP_CODE=%%H"
)

if defined HTTP_CODE (
    if "!HTTP_CODE:~0,1!"=="2" goto :searx_ready
    if "!HTTP_CODE:~0,1!"=="3" goto :searx_ready
)

set /a COUNT+=1
if !COUNT! GEQ 15 (
    echo SearXNG is not responding.
    echo Checking Docker containers:
    docker ps -a
    goto :error
)

timeout /t 2 /nobreak >NUL
goto :searx_wait

:searx_ready
echo SearXNG is responding.

:: -----------------------------------------
:: 4. TTS Server
:: -----------------------------------------

echo.
echo [4/5] Starting TTS server...

if exist "%TTS_DIR%\venv\Scripts\activate.bat" (
    set "TTS_ACTIVATE=%TTS_DIR%\venv\Scripts\activate.bat"
) else if exist "%TTS_DIR%\.venv\Scripts\activate.bat" (
    set "TTS_ACTIVATE=%TTS_DIR%\.venv\Scripts\activate.bat"
) else (
    echo ERROR: TTS virtual environment not found.
    goto :error
)

if not exist "%TTS_DIR%\server.py" (
    echo ERROR: tts\server.py not found.
    goto :error
)

start "HornetAI TTS" cmd /k "cd /d ""%TTS_DIR%"" && call ""%TTS_ACTIVATE%"" && python server.py"

echo TTS server launched.

:: -----------------------------------------
:: 5. HornetAI
:: -----------------------------------------

echo.
echo [5/5] Starting HornetAI...

cd /d "%ROOT%"

echo Project directory: %ROOT%
echo.

python -m app.main

echo.
echo HornetAI application has exited.
pause
exit /b 0

:error
echo.
echo ========================================
echo          STARTUP FAILED
echo ========================================
echo.
pause
exit /b 1