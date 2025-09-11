#!/bin/bash
echo "Building YourApp for macOS/Linux..."
pyinstaller --onefile --noconsole --icon=assets/icon.ico app_ui.py --name YourApp-UI
pyinstaller --onefile --noconsole --icon=assets/icon.ico app_cli.py --name YourApp-CLI
echo "Build complete! Check the dist/ folder."
