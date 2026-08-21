# rekordbox USB Playlist Exporter

[日本語版はこちら (Japanese README)](README.ja.md)

Switch between English and 日本語 anytime from the "Language" control in the top-left of the GUI
(a dictionary-based translation table lives in `i18n.py`).

Reads a USB exported from rekordbox for Pioneer CDJs (containing `PIONEER/rekordbox/export.pdb`) and
**copies** (never moves — your original USB is left untouched) tracks into a simple flat folder
structure for players that only support folder browsing (CDJ-400, third-party CDJs, etc.):

```
output/
  Playlists/
    Pops/
      01_track_a.mp3
      02_track_b.mp3
    okiniiri01/
      01_track_c.mp3
```

- Folder name = playlist name (characters invalid on Windows are replaced with `_`)
- File name = sequence number within the playlist + `_` + original file name (original file name is kept as-is)
- Even if playlists are nested in folders in rekordbox, the output is flattened to
  "one folder per playlist" (the folder hierarchy is not reproduced).
- Duplicate playlist names are automatically disambiguated as `name_1`, `name_2`, ...

### Additional options (the "File / folder naming options" panel in the GUI)

- **mp3 only**: excludes any file whose extension isn't `.mp3`. Sequence numbers are renumbered
  based only on the tracks actually copied.
- **File name source**:
  - "Original file name": use the original file name as-is (default)
  - "Tag (artist / title)": build the file name from the artist/title in the rekordbox database
- **Tag order** (only relevant when the file name source is "Tag"):
  - "Artist - Title" (default)
  - "Title - Artist"
- **Sequence number position**: prefix (`01_name.mp3`) or suffix (`name_01.mp3`)
- **Romanize (pykakasi)**: converts multi-byte characters (e.g. Japanese) in file/folder names to
  Hepburn-style romaji. Also applied to playlist folder names (some players struggle to display
  multi-byte characters in folder names too).

## Two modes

The GUI has two tabs:

- **Playlist mode**: copies rekordbox playlists into folders as described above.
- **BPM search mode**: given a target BPM and a tolerance (±), searches the *entire library*
  (independent of playlists) for tracks whose BPM falls in range, and copies the selected results
  into a folder with a name you choose (e.g. `Playlists/bpm_128/`). Results are listed closest-BPM-first.
  - Can also be filtered by genre (the dropdown is auto-populated from the genres actually used in
    the loaded library; "All" ignores genre).
  - Click the "Title", "Artist", or "BPM" column headers in the result list to sort ascending/descending.

The naming options (mp3-only, tag-based naming, romanization, etc.) apply to both modes.

## Source library (choose one of two formats)

The GUI's "Source library" selector lets you choose which database format on the USB to read.

| | export.pdb (stable) | One Library / exportLibrary.db (**beta**) |
|---|---|---|
| Applies to | The classic rekordbox device-export format | The newer Device Library Plus format (for newer hardware such as the OPUS-QUAD) |
| Library used | [`rekordbox-pdb`](https://github.com/fragmede/rekordbox-pdb) | `pyrekordbox`'s `devicelib_plus` (**unreleased dev build only**) |
| Install | Included in `requirements.txt` | Install `requirements-onelib.txt` separately |
| Verified | **Confirmed playing on real CDJ-400 hardware** | Not tested on real hardware yet; the read logic has been verified against schema-accurate synthetic data |

`pyrekordbox`'s stable release only supports the desktop `master.db`, not the `export.pdb`
(DeviceSQL format) used on CDJ USB exports — that's why the stable path here uses `rekordbox-pdb` instead.

**One Library (`exportLibrary.db`)** is a newer database format placed in the same folder as
`PIONEER/rekordbox/export.pdb` on the USB (only present if your hardware/rekordbox setup exports it).
`pyrekordbox` has a `devicelib_plus` module that reads it, but it's **not yet published to PyPI** —
only available on the GitHub development branch. Since it depends on unreleased code that could change
or break, it's marked "beta" here.

The `export.pdb` path has been confirmed to produce a working, playable USB on a real CDJ-400. One
Library (beta) hasn't been tested on real hardware yet, so it's recommended to use **dry run**
(logs what would be copied without actually copying anything) on a few playlists first before trusting it.

## Setup

```bash
cd rekordbox_flat_export
pip install -r requirements.txt

# Only if you want to use One Library (beta):
pip install -r requirements-onelib.txt
```

## Running

```bash
python app.py
```

## Usage

1. Choose `export.pdb (stable)` or `One Library (beta)` under "Source library"
2. Set "Source USB" to the root folder of a rekordbox-exported USB (the folder containing `PIONEER`)
3. Set "Output folder" to your destination (e.g. a separate USB for a CDJ-400)
4. Click "Load library" — this shows the playlist list and track counts (BPM search mode also loads
   the whole library at this point)
5. In "Playlist mode", uncheck any playlists you don't want; in "BPM search mode", enter a target BPM
   and tolerance, search, and set an output folder name
6. Adjust the "File / folder naming options" as needed
7. The first time, check "Dry run" and click "Start copy" to review the plan in the log
8. If it looks right, uncheck "Dry run" and click "Start copy" again

Tracks whose source file can't be found are skipped and logged with a reason; the rest continue normally.

## Limitations

- Only regular playlists (playlists containing tracks) are supported. Smart playlist conditions are
  not re-evaluated — a smart playlist reflects whatever was in it at export time.
  History playlists are not included.
- If `rekordbox-pdb` / `pyrekordbox`'s interpretation of the format doesn't match your actual file,
  loading may fail. In that case, adjust `load_playlists_pdb` / `load_playlists_onelib` in `core.py`
  to match the library's actual API.
- One Library (beta) depends on an unreleased `pyrekordbox` development build. If the API has changed
  since, re-run `pip install -r requirements-onelib.txt` to update.

## Building a standalone executable

```bash
pip install pyinstaller
pyinstaller --noconfirm --onefile --windowed --name RekordboxFlatExport \
  --collect-all pykakasi --collect-all rekordbox_pdb \
  --collect-all pyrekordbox --collect-all sqlcipher3 \
  app.py
```

This repo also has a GitHub Actions workflow (`.github/workflows/build.yml`) that builds both a
Windows `.exe` and a macOS `.app` (zipped) and attaches them to a GitHub Release whenever a `v*` tag
is pushed (or via manual `workflow_dispatch`). The macOS build is unsigned/not notarized, so it will
show a Gatekeeper warning on first launch (right-click → Open to bypass).
