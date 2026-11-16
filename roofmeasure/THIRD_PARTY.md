# Third-party components in RoofMeasure 0.1.7.6

| Component | Version | Where | License |
|---|---|---|---|
| MapLibre GL JS | 4.7.1 | www/vendor/maplibre-gl.js, .css (www/vendor/LICENSE.txt) | BSD-3-Clause |
| laz-perf | 0.0.7 | www/vendor/laz-perf/ | Apache-2.0 |
| three.js (core + OrbitControls, bundled into one IIFE with esbuild, minified) | r187 (0.187.0) | www/vendor/three/three-rm.min.js (www/vendor/three/LICENSE, README.md) | MIT |
| Pyodide (CPython + stdlib, WebAssembly) | 0.27.7 | www/vendor/pyodide/ | MPL-2.0 (CPython: PSF License) |
| Google Maps logo SVGs | Google attribution pack | www/icons/google-maps-logo-*.svg | Google brand assets (see www/icons/GOOGLE_LOGO_NOTICE.md) |
| Android SDK build tools / platform android.jar (build time only) | 34 | not shipped in source | Android SDK License |
| Playwright-core (tests only, not shipped) | 1.59.1 | tests/*.cjs | Apache-2.0 |

Data sources (terms of service, not code licenses): MassGIS (Commonwealth of Massachusetts), USGS 3DEP lidar (public domain),
USDA NAIP (public domain), OpenStreetMap (ODbL), Overture Maps (ODbL/CDLA), FEMA USA Structures (public domain).
Google / Microsoft (Azure, Bing) / Esri imagery is display-only reference: never traced, measured, stored or analysed (their terms).
