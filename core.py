"""
rekordbox が Pioneer CDJ 用に書き出した USB (PIONEER/rekordbox/export.pdb) から
プレイリスト情報を読み込み、フォルダ読み込みしか対応していない機種向けに
  <output_root>/playlists/<プレイリスト名>/<連番>_<元のファイル名>
という構成でファイルをコピーするためのコアロジック。

DB の読み込みには rekordbox-pdb (https://github.com/fragmede/rekordbox-pdb) を使用する。
pyrekordbox はデスクトップの master.db 用で、CDJ 向け export.pdb (DeviceSQL 形式) は
読めないため、こちらを利用している。
"""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Literal, Optional
from urllib.parse import unquote

INVALID_CHARS = re.compile(r'[\\/:*?"<>|]')

NameSource = Literal["original", "tag"]
SeqPosition = Literal["prefix", "suffix"]
TagOrder = Literal["artist_title", "title_artist"]


def sanitize_name(name: str) -> str:
    name = (name or "").strip()
    name = INVALID_CHARS.sub("_", name)
    name = name.rstrip(". ")
    return name or "untitled"


class RomajiLibraryMissingError(Exception):
    def __init__(self):
        self.code = "err_romaji_lib_missing"
        self.params = {"cmd": "pip install pykakasi"}
        super().__init__(self.code)


_kakasi_instance = None


def _get_kakasi():
    global _kakasi_instance
    if _kakasi_instance is None:
        try:
            import pykakasi
        except ImportError as e:
            raise RomajiLibraryMissingError() from e
        _kakasi_instance = pykakasi.kakasi()
    return _kakasi_instance


def romanize_text(text: str) -> str:
    """日本語などマルチバイト文字を含む文字列をローマ字に変換する。"""
    if not text:
        return text
    kks = _get_kakasi()
    return "".join(item["hepburn"] for item in kks.convert(text))


@dataclass
class TrackInfo:
    id: int
    title: str
    artist: str
    file_path: str  # export.pdb に記録された、USBルートからの相対パス
    bpm: Optional[float] = None


@dataclass
class PlaylistInfo:
    id: int
    name: str  # 出力フォルダ名として使う、サニタイズ・重複解決済みの名前
    original_name: str
    track_ids: list[int] = field(default_factory=list)


@dataclass
class CopyItem:
    playlist_name: str
    src: Optional[Path]
    dst: Optional[Path]
    ok: bool
    reason_code: str = ""
    reason_params: dict = field(default_factory=dict)


LibrarySource = Literal["pdb", "onelib"]


class PdbNotFoundError(Exception):
    def __init__(self, usb_root: Path):
        self.code = "err_pdb_not_found"
        self.params = {"usb_root": str(usb_root)}
        super().__init__(self.code)


class PdbLibraryMissingError(Exception):
    def __init__(self):
        self.code = "err_pdb_lib_missing"
        self.params = {"cmd": "pip install git+https://github.com/fragmede/rekordbox-pdb.git"}
        super().__init__(self.code)


class OneLibraryNotFoundError(Exception):
    def __init__(self, usb_root: Path):
        self.code = "err_onelib_not_found"
        self.params = {"usb_root": str(usb_root)}
        super().__init__(self.code)


class OneLibraryMissingError(Exception):
    def __init__(self):
        self.code = "err_onelib_lib_missing"
        self.params = {"cmd": "pip install git+https://github.com/dylanljones/pyrekordbox.git"}
        super().__init__(self.code)


def find_export_pdb(usb_root: Path) -> Path:
    candidate = usb_root / "PIONEER" / "rekordbox" / "export.pdb"
    if candidate.exists():
        return candidate
    # 大文字小文字違いや配置違いのケースを一応探索する
    for p in usb_root.rglob("export.pdb"):
        return p
    raise PdbNotFoundError(usb_root)


def find_export_library(usb_root: Path) -> Path:
    candidate = usb_root / "PIONEER" / "rekordbox" / "exportLibrary.db"
    if candidate.exists():
        return candidate
    for p in usb_root.rglob("exportLibrary.db"):
        return p
    raise OneLibraryNotFoundError(usb_root)


def search_tracks_by_bpm(
    tracks: dict[int, TrackInfo], target_bpm: float, tolerance: float
) -> list[TrackInfo]:
    """指定 BPM ± 許容範囲に一致するトラックを、目標 BPM に近い順で返す。"""
    lo, hi = target_bpm - tolerance, target_bpm + tolerance
    matches = [t for t in tracks.values() if t.bpm is not None and lo <= t.bpm <= hi]
    matches.sort(key=lambda t: (abs(t.bpm - target_bpm), t.title.lower()))
    return matches


def make_search_playlist(name: str, track_ids: list[int]) -> PlaylistInfo:
    """BPM 検索結果などを、既存の build_copy_plan にそのまま渡せる PlaylistInfo にまとめる。"""
    return PlaylistInfo(id=-1, name=sanitize_name(name), original_name=name, track_ids=track_ids)


def _finalize_playlists(
    raw_playlists: list[tuple[int, str, list[int]]]
) -> list[PlaylistInfo]:
    """(id, name, track_ids) のリストから、空プレイリスト除去・重複名解決済みの PlaylistInfo リストを作る。"""
    used_names: dict[str, int] = {}
    playlists: list[PlaylistInfo] = []
    for pid, raw_name, track_ids in raw_playlists:
        if not track_ids:
            continue  # 空プレイリストはスキップ
        base_name = sanitize_name(raw_name)
        name = base_name
        if base_name in used_names:
            used_names[base_name] += 1
            name = f"{base_name}_{used_names[base_name]}"
        else:
            used_names[base_name] = 0
        playlists.append(PlaylistInfo(id=pid, name=name, original_name=raw_name, track_ids=track_ids))
    playlists.sort(key=lambda p: p.name.lower())
    return playlists


def load_playlists_pdb(usb_root: Path) -> tuple[dict[int, TrackInfo], list[PlaylistInfo]]:
    try:
        from rekordbox_pdb import Database
    except ImportError as e:
        raise PdbLibraryMissingError() from e

    pdb_path = find_export_pdb(usb_root)
    db = Database.from_file(str(pdb_path))

    artist_map = {a.id: (a.name or "") for a in db.artists}

    tracks: dict[int, TrackInfo] = {}
    for t in db.tracks:
        tempo = getattr(t, "tempo", None)  # BPM * 100
        tracks[t.id] = TrackInfo(
            id=t.id,
            title=getattr(t, "title", "") or "",
            artist=artist_map.get(getattr(t, "artist_id", None), ""),
            file_path=t.file_path,
            bpm=(tempo / 100) if tempo else None,
        )

    # is_folder == False のノードのみが実際にトラックを持つ「プレイリスト」
    leaf_nodes = [n for n in db.playlist_tree if not n.is_folder]

    entries_by_playlist: dict[int, list[tuple[int, int]]] = {}
    for e in db.playlist_entries:
        entries_by_playlist.setdefault(e.playlist_id, []).append((e.entry_index, e.track_id))

    raw_playlists = []
    for node in leaf_nodes:
        entries = sorted(entries_by_playlist.get(node.id, []), key=lambda x: x[0])
        track_ids = [tid for _, tid in entries]
        raw_playlists.append((node.id, node.name, track_ids))

    return tracks, _finalize_playlists(raw_playlists)


def load_playlists_onelib(usb_root: Path) -> tuple[dict[int, TrackInfo], list[PlaylistInfo]]:
    """One Library (Device Library Plus, exportLibrary.db) からの読み込み。

    未リリースの pyrekordbox 開発版 (devicelib_plus モジュール) が必要:
        pip install git+https://github.com/dylanljones/pyrekordbox.git
    正式リリースされていない機能に依存しているため挙動が変わる可能性がある。
    """
    try:
        from pyrekordbox.devicelib_plus import DeviceLibraryPlus
    except ImportError as e:
        raise OneLibraryMissingError() from e

    lib_path = find_export_library(usb_root)
    db = DeviceLibraryPlus(str(lib_path))
    try:
        tracks: dict[int, TrackInfo] = {}
        for c in db.get_content():
            artist_name = c.artist.name if c.artist is not None else ""
            bpmx100 = getattr(c, "bpmx100", None)
            tracks[c.content_id] = TrackInfo(
                id=c.content_id,
                title=c.title or "",
                artist=artist_name or "",
                file_path=c.path,
                bpm=(bpmx100 / 100) if bpmx100 else None,
            )

        # attribute == 0 が通常のプレイリスト、1 がフォルダ
        leaf_playlists = [p for p in db.get_playlist() if p.attribute == 0]

        raw_playlists = []
        for p in leaf_playlists:
            songs = sorted(p.songs, key=lambda s: s.sequenceNo)
            track_ids = [s.content_id for s in songs]
            raw_playlists.append((p.playlist_id, p.name, track_ids))

        return tracks, _finalize_playlists(raw_playlists)
    finally:
        db.close()


def load_playlists(
    usb_root: Path, source: LibrarySource = "pdb"
) -> tuple[dict[int, TrackInfo], list[PlaylistInfo]]:
    if source == "onelib":
        return load_playlists_onelib(usb_root)
    return load_playlists_pdb(usb_root)


def resolve_source_path(usb_root: Path, file_path: str) -> Optional[Path]:
    raw = (file_path or "").replace("\\", "/").lstrip("/")
    candidates = [usb_root / raw, usb_root / unquote(raw)]
    for c in candidates:
        if c.exists():
            return c
    # 直接パスが見つからない場合、ファイル名で USB 内を探索するフォールバック
    filename = Path(raw).name
    if filename:
        for p in usb_root.rglob(filename):
            return p
    return None


def _dedup_name(base: str, used_names: dict[str, int]) -> str:
    if base not in used_names:
        used_names[base] = 0
        return base
    used_names[base] += 1
    return f"{base}_{used_names[base]}"


def _track_base_name(
    track: TrackInfo, src: Path, name_source: NameSource, tag_order: TagOrder = "artist_title"
) -> str:
    if name_source == "tag":
        artist = (track.artist or "").strip() or "Unknown Artist"
        title = (track.title or "").strip() or src.stem
        if tag_order == "title_artist":
            return f"{title} - {artist}"
        return f"{artist} - {title}"
    return src.stem


def build_copy_plan(
    usb_root: Path,
    output_root: Path,
    tracks: dict[int, TrackInfo],
    playlists: list[PlaylistInfo],
    *,
    mp3_only: bool = False,
    name_source: NameSource = "original",
    seq_position: SeqPosition = "prefix",
    tag_order: TagOrder = "artist_title",
    romanize: bool = False,
) -> list[CopyItem]:
    plan: list[CopyItem] = []
    used_folder_names: dict[str, int] = {}

    for pl in playlists:
        folder_source = pl.original_name if romanize else pl.name
        folder_base = sanitize_name(romanize_text(folder_source) if romanize else folder_source)
        folder_name = _dedup_name(folder_base, used_folder_names)
        folder = output_root / "Playlists" / folder_name

        # 1st pass: 各トラックを解決し、実際にコピー対象になるものを確定する
        entries: list[tuple[bool, Optional[TrackInfo], Optional[Path], str, dict]] = []
        for tid in pl.track_ids:
            track = tracks.get(tid)
            if track is None:
                entries.append((False, None, None, "reason_track_not_in_db", {"id": tid}))
                continue
            src = resolve_source_path(usb_root, track.file_path)
            if src is None:
                entries.append(
                    (
                        False,
                        track,
                        None,
                        "reason_file_not_found",
                        {"file_path": track.file_path, "title": track.title},
                    )
                )
                continue
            if mp3_only and src.suffix.lower() != ".mp3":
                entries.append((False, track, src, "reason_excluded_non_mp3", {"filename": src.name}))
                continue
            entries.append((True, track, src, "", {}))

        included_count = sum(1 for ok, *_ in entries if ok)
        width = max(2, len(str(included_count)))

        # 2nd pass: 実際に含まれるものにのみ連番を振り、ファイル名を組み立てる
        seq_counter = 0
        for ok, track, src, reason_code, reason_params in entries:
            if not ok:
                plan.append(CopyItem(folder_name, src, None, False, reason_code, reason_params))
                continue
            seq_counter += 1
            seq = str(seq_counter).zfill(width)
            base = _track_base_name(track, src, name_source, tag_order)
            if romanize:
                base = romanize_text(base)
            base = sanitize_name(base)
            ext = src.suffix
            filename = f"{seq}_{base}{ext}" if seq_position == "prefix" else f"{base}_{seq}{ext}"
            dst = folder / filename
            plan.append(CopyItem(folder_name, src, dst, True))

    return plan


ProgressCallback = Callable[[CopyItem, int, int], None]


def execute_copy_plan(
    plan: list[CopyItem],
    dry_run: bool = False,
    progress_cb: Optional[ProgressCallback] = None,
) -> list[CopyItem]:
    results: list[CopyItem] = []
    total = len(plan)
    for i, item in enumerate(plan, start=1):
        if not item.ok:
            results.append(item)
            if progress_cb:
                progress_cb(item, i, total)
            continue
        try:
            if not dry_run:
                item.dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item.src, item.dst)
            results.append(item)
        except OSError as e:
            results.append(
                CopyItem(
                    item.playlist_name,
                    item.src,
                    item.dst,
                    False,
                    "reason_copy_failed",
                    {"error": str(e)},
                )
            )
        if progress_cb:
            progress_cb(results[-1], i, total)
    return results
