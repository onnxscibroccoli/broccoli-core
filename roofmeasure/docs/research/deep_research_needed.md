# RoofMeasure 0.1.7.3: deep research needed (next work, all NOT_PROVEN today)

1. **Ground truth**
   - We need measured reports to calibrate against: contractor tape and drone, EagleView/GAF reports that homeowners own and share, and permit
     drawings and assessor sketches.
   - Without them every number stays NOT_PROVEN.
   - Needed: a consent and data-sharing workflow, and an error budget per line type.
2. **Roof reconstruction from lidar**
   - Move from region growing plus adjacency to a topologically consistent model, using one of:
     - PolyFit (Nan & Wonka; GPL code, so use it as a method reference)
     - City3D (Huang et al. 2022)
     - Roofn3D / RoofN3D benchmark
     - 3dfier / geoflow (TU Delft; GPL/LGPL)
     - Kinetic shape reconstruction (CGAL; GPL/commercial)
     - BSP-Net-style learned primitives
   - Also: roof-graph matching against the straight skeleton, and mixed-pitch weighted skeletons.
3. **Dormers and curved structures**
   - Shed, gable and eyebrow dormers; barrel and curved roofs (non-planar, so they need quadric or spline fitting).
   - Small-plane detection at about 7 pts/m² and its point-density limits.
   - Fusing in the newer and denser MA lidar where it exists.
4. **Skylight / chimney / vent detection on FREE imagery plus lidar** (never on Google/Bing/Esri)
   - Imagery sources:
     - MassGIS 2025 orthos: 15 cm. The MassGIS tile server sends CORS for the app origin, so in-app pixel reads are possible.
     - NAIP: 60 cm.
     - Mapillary: CC BY-SA. KartaView: CC BY-SA. Check per-image licences.
     - User photos.
   - Lightweight candidate models:
     - YOLOv8n/YOLO11n: AGPL-3.0; Ultralytics licence, commercial licence needed for closed use.
     - RT-DETR (Apache-2.0, PaddleDetection / HF transformers).
     - YOLOX-nano (Apache-2.0).
     - MobileNet-SSD / EfficientDet-Lite (Apache-2.0, TFLite, runs on-device).
     - SAM / SAM 2 (Apache-2.0) for segmentation; MobileSAM / EfficientSAM (Apache-2.0) are light enough for phones.
     - Grounding DINO (Apache-2.0) for zero-shot "skylight" prompts.
   - Run them with ONNX Runtime Web (MIT) or TF.js (Apache-2.0) in the WebView.
   - We need a labelled MA roof-object dataset (skylights, chimneys, vents, solar), or fine-tuning on public sets such as the RID roof
     information dataset (TUM) or SpaceNet (CC BY-SA).
5. **Lidar vintage vs current building**
   - Detect additions and changes between the 2021 lidar, the MassGIS roofprints and the 2025 orthos.
   - Lean and registration correction of the orthos (2–6 m offsets seen).
   - Footprint/lidar offset estimation (ICP of footprint edges vs lidar step edges).
6. **Trees and occlusion**
   - Filter vegetation over roofs (class 1/5 contamination), use return number and number-of-returns, use leaf-off vintages, and decide when to
     refuse a fit.
7. **Flashing semantics**
   - Rules for when a height jump means sidewall/step flashing, headwall, counter-flashing or a plain eave/rake.
   - Validate with contractors; a cricket at a chimney is one case.
   - Also: gutters and drip edge on raised-section eaves.
8. **National coverage**
   - Outside MA: 3DEP EPT/COPC coverage and quality levels (QL1/QL2), and footprint sources (FEMA USA Structures, Overture, OSM, Microsoft
     footprints ODbL).
   - Per-state ortho sources with permissive terms.
9. **Quote fairness**
   - Map takeoffs to material quantities and regional unit costs (open price data?), so homeowners can check a quote.
   - This needs a sound method and careful wording (no accuracy claims).
10. **On-device emulator/device testing**
   - The box emulator never boots. CI uses GitHub's KVM runners (reactivecircus/android-emulator-runner). Real-device PDF save and share on
     Ian's phone remains NOT_PROVEN until he tests.
11. **Ortho pixel analysis (now allowed on free MassGIS 2025 15 cm and NAIP; Google/Bing/Esri stay display-only)**
    - Edge snap exists (gradient search per edge); next: Canny-style sub-pixel edges, per-vertex corner snap, lean/offset correction of the
      2025 orthos (2-6 m relief displacement) before snapping, confidence per edge.
    - Skylight/dormer candidates from bright/dark rectangular patches, fused with the lidar voids/dips; ortho-to-lidar registration first.
12. **Single-ridge vs per-wing eave/rake on complex roofs**
    - The private complex test house matches the reference with the single dominant ridge (255.5/149.4 LF); per-wing gave 283.4/115.9.
      Need more complex houses with ground truth to decide when per-wing is right (L/T/cross-gables) and to auto-pick it from lidar ridges.
13. **Promoting candidates**: measure how often users promote lidar hip/valley/wall-flashing candidates; use that to tune confidence thresholds.
