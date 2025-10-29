#!/bin/bash
# Create simple SVG-based PNG icons
for size in 16 48 128; do
  cat > icon${size}.svg << EOSVG
<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 128 128">
  <rect width="128" height="128" fill="#1f6feb" rx="24"/>
  <text x="64" y="90" font-family="Arial" font-size="80" font-weight="bold" fill="white" text-anchor="middle">J</text>
</svg>
EOSVG
done
