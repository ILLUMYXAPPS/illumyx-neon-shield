@echo off
echo Building YourApp for Windows...
pyinstaller --onefile --noconsole --icon=assets/icon.ico app_ui.py --name YourApp-UI
pyinstaller --onefile --noconsole --icon=assets/icon.ico app_cli.py --name YourApp-CLI
echo Build complete! Check the dist/ folder.
pause
