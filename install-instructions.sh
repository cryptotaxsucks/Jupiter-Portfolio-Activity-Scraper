#!/bin/bash

clear
cat << 'EOF'
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║         Jupiter Portfolio Full CSV Export Extension (v5)             ║
║                    Chrome Extension - Ready to Install               ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝

📦 INSTALLATION INSTRUCTIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This is a Chrome browser extension. To install:

1️⃣  Open Chrome and navigate to:
   chrome://extensions/

2️⃣  Enable "Developer mode" (toggle in top-right corner)

3️⃣  Click "Load unpacked" button

4️⃣  Select this folder:
   /home/runner/workspace

5️⃣  The extension is now installed!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📖 USAGE GUIDE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

First Time Setup:

1. Navigate to: https://jup.ag/portfolio/[your-wallet-address]
2. Click "Load more" button ONCE on the transactions page
   (This captures authentication headers)
3. Click the extension icon in Chrome toolbar
4. Click "Export Full CSV"
5. You can close the popup - export runs in background
6. Notification appears when complete

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📁 FILES INCLUDED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✓ manifest.json       - Extension configuration (MV3)
✓ background.js       - Service worker (export logic)
✓ content.js          - Content script (bridge injector)
✓ bridge.js           - Page-world script (header capture)
✓ popup.html/js/css   - Extension popup UI
✓ offscreen.html/js   - Offscreen document (downloads)
✓ icons/              - Extension icons
✓ README.md           - Full documentation

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔍 DIAGNOSTICS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

After clicking "Load more" on Jupiter:
- Open extension popup
- Click "Diagnostics" button
- Verify: hasBridge: true, headersReady: true

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✨ FEATURES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

• Export ALL transactions (10,000+) without manual clicking
• Runs in background (close popup anytime)
• Progress notifications
• Automatic header capture
• MV3 compliant (no deprecated APIs)
• CSV format matches Jupiter's official export

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

For detailed documentation, see README.md

Press Ctrl+C to exit this message.

EOF

# Keep running to satisfy workflow requirement
while true; do
  sleep 3600
done
