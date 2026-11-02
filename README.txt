BeaconDex Platinum v0.1.0
========================

This package does not contain a Nintendo DS ROM.

Required source ROM
-------------------
Pokemon Platinum (USA), revision 1
Game code: CPUE
Size: 134217728 bytes
SHA-256: fbce4c4def0c7797f8dd238a3d7a5e48b4a7e3abd86890ac65f6321cef781bdb

Easy method
-----------
Open BeaconDex-Platinum-v0.1.0-US-Rev1.bps in Floating IPS or another BPS
patcher, select the clean source ROM above, and save the result as a new .nds
file. Do not overwrite your clean ROM. Start with a fresh save.

Bundled command-line method
---------------------------
python3 bps_patch.py apply CLEAN_PLATINUM.nds \
  BeaconDex-Platinum-v0.1.0-US-Rev1.bps BeaconDex-Platinum.nds

Expected patched ROM SHA-256
---------------------------
9c54fe91735278fcc0efee2b26804bcc64d1060367ff310279494bae13b55f96
