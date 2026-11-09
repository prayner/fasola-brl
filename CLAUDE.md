# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview
This repo consists of a python module, fasola.py and some supporting
files for xsl transformations. Its purpose is to convert shape note
songbooks to the bespoke braille music notation defined in fasola.py.
Two books are supported:

- **sacred-harp**: the 2025 edition of the Sacred Harp, from the plain
  text lyrics in 2025-edition and the MusicXML in 2025-music
  (brailleAll / brailleList / braillesong_general).
- **shenandoah**: the Shenandoah Harmony, from the MusicXML in
  shenandoah-harmony/WholeBook/MusicXML, which carries the words too
  (brailleShenandoah / braillesong_shenandoah).

For each song the output is the title and each part's music, then the
words of every verse, then each verse line by line (a line of words, then
the music it is sung to).

## Commands

```bash
# Enable environment
conda activate 3.11
cd /home/peter/nonwork/fasola

# braille the bass part of the whole book into test-bass
python fasola.py --book sacred-harp --parts bass --outdir test-bass
python fasola.py --book shenandoah --parts bass --outdir shenandoah-bass

# or choose the book with an environment variable (default sacred-harp)
FASOLA_BOOK=shenandoah python fasola.py --parts bass --outdir shenandoah-bass

# only some songs: Sacred Harp numbers, or Shenandoah music file names
python fasola.py --book sacred-harp --songs 347.1 --outdir test-bass
python fasola.py --book shenandoah --songs CH144_WalkWithGod --outdir test-bass
```

From python, after `exec(open('fasola.py').read())` or importing it:

```python
brailleBook(['bass'], 'test-bass', book='shenandoah')  # book=None uses FASOLA_BOOK
```

Each run prints (or brailleBook returns) the songs that failed; `--debug`
(debug=True) stops at the first failure instead.
