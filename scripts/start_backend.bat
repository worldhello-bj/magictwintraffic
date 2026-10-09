@echo off
cd /d "%~dp0\.."
echo Full backend uses Linux workers. Starting through Docker Desktop.
docker compose up --build
