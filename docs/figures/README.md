# Figures

Every figure in [`docs/images`](../images) is drawn by one script from documented sources, so each line can be checked and rebuilt.

```bash
cd docs/figures
pip install numpy scipy pillow       # and rsvg-convert (librsvg), or: pip install cairosvg
python make_figures.py               # all figures
python make_figures.py placement     # just one
```

`extract_reference_data.py` wrote the files in `data/` once (it needs `mne ezdxf pandas openpyxl scipy` and downloads the Raspberry Pi drawing and PiEEG's example recording). You only run it again to change a source.

| Figure | File | Built from |
|---|---|---|
| Hero | `hero.png` | Bust of Athena: AI generated illustration (Gamma), recolored and cleaned by the script. Trace: a 6 s excerpt of PiEEG's example recording `output3.xlsx`, channel 8, 1 to 40 Hz |
| FIG. 01 System | `system.png` | the head from FIG. 04, the boards from the sources below, free cables drawn as hanging catenaries |
| FIG. 02 What's in the box | `kit.png` | Raspberry Pi drawing, PiEEG-8 measurements, sticker diameter and cable length from the product pages |
| FIG. 03 Mounting | `assembly.png` | Raspberry Pi 3 Model B mechanical drawing (RPI-3B-V1_2, DXF), PiEEG-8 measurements |
| FIG. 04 Electrode placement | `placement.png` | MNE-Python standard 10-20 montage (colin27 head) |
| FIG. 05 Wiring | `wiring.png` | PiEEG docs (header order), register values written by PiEEG Server 0.49.0, ADS1299 datasheet |
| FIG. 06 Pi header | `header.png` | PiEEG docs (Electrodes & Pinout), PiEEG Server 0.49.0 (`profiles.py`, `hardware.py`), ADS1299 datasheet |

## Measured or approximate

- **Raspberry Pi 3 Model B**: outline, parts, mounting holes and the 40 pin header come from Raspberry Pi's official DXF drawing.
- **PiEEG-8**: there is no published mechanical drawing. Outline, holes, electrode header, ADS1299, LED and jumpers are measured on the top view photo in PiEEG's docs (`pieeg8_led.png`, board printed PiEEG V2.1), about 1 mm accurate. The 40 pin socket shares the Pi's coordinates.
- **Electrode positions**: MNE-Python's `standard_1020` montage. The top view in FIG. 04 uses the azimuthal equidistant projection of MNE's topographic maps, scaled left to right so T7 and T8 sit on the circle like Fpz and Oz.
- **Head**: skull and electrode positions follow the montage. Face, ear and hair are drawn to adult proportions and are approximate.
- **Stickers**: Somnomedics SEN010C, 26 mm, drawn at true size. The snap stud's size is approximate.
- **Clips and connectors**: alligator clip (about 28 mm) and Dupont housing (about 14 mm) are approximate.
- **Side views in FIG. 03**: heights are schematic.

## Style

The figures follow the PiEEG Home Lab design system, Lab theme: ground `#0b0d33`, gold for hardware, one fixed color per lead (E1 `#4b4bff`, E2 `#8f96ff` dashed, REF `#22d3ff`, BIAS `#c792ff`), Inter Display, Inter and DejaVu Sans Mono, SVG 1000 px wide, PNG exported at 2x.
