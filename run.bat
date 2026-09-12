@echo off
if not defined GEMINI_API_KEY (
    if exist "%~dp0.env" (
        for /f "usebackq tokens=1,* delims==" %%A in ("%~dp0.env") do (
            if "%%A"=="GEMINI_API_KEY" set "GEMINI_API_KEY=%%B"
        )
    )
)
if exist "%~dp0.venv\Scripts\activate.bat" (
    call "%~dp0.venv\Scripts\activate.bat"
)
python "%~dp0main.py" %*