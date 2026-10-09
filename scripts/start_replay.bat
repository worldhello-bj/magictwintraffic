@echo off
cd /d "%~dp0\.."
if not exist web\dist\index.html (
  echo Build viewer first: cd web ^&^& npm ci ^&^& npm run build
  exit /b 1
)
python -m http.server 8080 --bind 127.0.0.1 --directory web\dist
