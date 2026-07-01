@echo off
cd /d "C:\Users\marko\Desktop\Reymen Proje\ReYMeN-Ajan"
setlocal
set /p TOKEN=<"C:\Users\marko\tmp_token.txt"
set TELEGRAM_BOT_TOKEN=%TOKEN%
set HERMES_PROFILE=default
set HERMES_GATEWAY=http
"C:\Users\marko\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe" reymen\ag\telegram_bot.py
