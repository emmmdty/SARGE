# CCKS 2026 paper source

Final paper PDF: `../SARGE_CCKS2026.pdf`

The `source/` directory is the camera-ready LaTeX package: main text,
bibliography, class files, and the two figures used by the paper. It is kept
byte-identical to the submitted source package.

## Build

From this directory:

```bash
cd source
pdflatex main_en_final
bibtex main_en_final
pdflatex main_en_final
pdflatex main_en_final
```

The resulting `main_en_final.pdf` should match `../SARGE_CCKS2026.pdf`.
