# YourApp v1 ⚡

## Versions
- **YourApp-UI** → Clickable app with GUI (Tkinter)
- **YourApp-CLI** → Lightweight command-line version

## Build Instructions
1. Install requirements:
   ```bash
   pip install -r requirements.txt
   ```
2. Run build script:
   - Windows: `build.bat`
   - macOS/Linux: `bash build.sh`

## Pricing
- Pricing is stored in **encrypted format** (`pricing.json`).  
- Update via:  
  ```bash
  python encrypt_pricing.py
  ```

## Next Steps
- Test locally
- Package installers
- Deploy to stores (Play Store, App Store, etc.)
