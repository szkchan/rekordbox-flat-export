"""
rekordbox が Pioneer CDJ 用に書き出した USB のライブラリを、
フォルダ読み込みしか対応していない機種 (CDJ-400 や他社 CDJ 等) 向けに、

  <出力先>/Playlists/<プレイリスト名 or BPM検索名>/<連番>_<元のファイル名>

という構成でコピーする GUI アプリ。プレイリストモードと、BPM近傍で
ライブラリ全体を横断検索するBPM検索モードの2つのタブがある。

使い方:
    python app.py
"""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import core
from i18n import LANG_LABELS, LANGS, t


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.lang = "en"
        self._i18n_widgets: list[tuple[tk.Widget, str, dict]] = []

        self.geometry("860x700")
        self.minsize(720, 560)

        self.tracks: dict[int, core.TrackInfo] = {}
        self.playlists: list[core.PlaylistInfo] = []
        self.selected: dict[int, bool] = {}

        self.bpm_results: list[core.TrackInfo] = []
        self.bpm_selected: dict[int, bool] = {}
        self._genre_list: list[str] = []
        self._bpm_sort_col: str | None = None
        self._bpm_sort_asc: bool = True

        self.event_queue: "queue.Queue" = queue.Queue()
        self.worker: threading.Thread | None = None

        self._build_widgets()
        self._apply_language()
        self.after(100, self._poll_queue)

    # ---------- i18n ----------

    def _reg(self, widget: tk.Widget, key: str, **params) -> tk.Widget:
        """ウィジェットを言語切り替え対象として登録し、現在の言語で文言を設定する。"""
        self._i18n_widgets.append((widget, key, params))
        widget.configure(text=t(self.lang, key, **params))
        return widget

    def _apply_language(self):
        for widget, key, params in self._i18n_widgets:
            widget.configure(text=t(self.lang, key, **params))
        self.title(t(self.lang, "window_title"))
        self.tree.heading("sel", text=t(self.lang, "col_sel"))
        self.tree.heading("name", text=t(self.lang, "col_name"))
        self.tree.heading("count", text=t(self.lang, "col_count"))
        self.bpm_tree.heading("sel", text=t(self.lang, "col_sel"))
        self._refresh_bpm_headings()
        self._refresh_genre_combo()
        self.notebook.tab(self.playlist_tab, text=t(self.lang, "tab_playlist_mode"))
        self.notebook.tab(self.bpm_tab, text=t(self.lang, "tab_bpm_mode"))

    def _on_language_change(self):
        self.lang = self.lang_var.get()
        self._apply_language()

    def _update_tag_order_state(self):
        flag = "!disabled" if self.name_source_var.get() == "tag" else "disabled"
        for widget in (self.tag_order_label, self.tag_order_rb1, self.tag_order_rb2):
            widget.state([flag])

    def t(self, key: str, **params) -> str:
        return t(self.lang, key, **params)

    # ---------- BPM tree: sortable columns ----------

    def _refresh_bpm_headings(self):
        labels = {"title": "col_title", "artist": "col_artist", "bpm": "col_bpm"}
        for col, key in labels.items():
            text = self.t(key)
            if self._bpm_sort_col == col:
                text += " ▲" if self._bpm_sort_asc else " ▼"
            self.bpm_tree.heading(col, text=text)

    def _sort_bpm_tree(self, col: str):
        if self._bpm_sort_col == col:
            self._bpm_sort_asc = not self._bpm_sort_asc
        else:
            self._bpm_sort_col = col
            self._bpm_sort_asc = True
        self._apply_bpm_sort()

    def _apply_bpm_sort(self):
        col = self._bpm_sort_col
        if col is None:
            return

        def key_func(pair):
            value = pair[0]
            if col == "bpm":
                try:
                    return float(value)
                except ValueError:
                    return float("-inf")
            return value.lower()

        items = [(self.bpm_tree.set(iid, col), iid) for iid in self.bpm_tree.get_children("")]
        items.sort(key=key_func, reverse=not self._bpm_sort_asc)
        for index, (_, iid) in enumerate(items):
            self.bpm_tree.move(iid, "", index)
        self._refresh_bpm_headings()

    # ---------- genre filter ----------

    def _refresh_genre_combo(self):
        all_label = self.t("genre_all")
        current = self.genre_var.get()
        self.genre_combo["values"] = [all_label] + self._genre_list
        if current not in self._genre_list:
            self.genre_var.set(all_label)

    # ---------- UI construction ----------

    def _build_widgets(self):
        pad = {"padx": 8, "pady": 4}

        lang_bar = ttk.Frame(self)
        lang_bar.pack(fill="x", padx=8, pady=(6, 0))
        self._reg(ttk.Label(lang_bar), "label_language").pack(side="left")
        self.lang_var = tk.StringVar(value=self.lang)
        for code in LANGS:
            ttk.Radiobutton(
                lang_bar,
                text=LANG_LABELS[code],
                variable=self.lang_var,
                value=code,
                command=self._on_language_change,
            ).pack(side="left", padx=(4, 0))

        top = ttk.Frame(self)
        top.pack(fill="x", **pad)

        self._reg(ttk.Label(top), "label_usb").grid(row=0, column=0, sticky="w")
        self.usb_var = tk.StringVar()
        ttk.Entry(top, textvariable=self.usb_var).grid(row=0, column=1, sticky="ew", padx=4)
        self._reg(ttk.Button(top, command=self._browse_usb), "browse").grid(row=0, column=2)

        self._reg(ttk.Label(top), "label_out").grid(row=1, column=0, sticky="w")
        self.out_var = tk.StringVar()
        ttk.Entry(top, textvariable=self.out_var).grid(row=1, column=1, sticky="ew", padx=4)
        self._reg(ttk.Button(top, command=self._browse_out), "browse").grid(row=1, column=2)

        self._reg(ttk.Label(top), "label_source").grid(row=2, column=0, sticky="w")
        self.library_source_var = tk.StringVar(value="pdb")
        source_frame = ttk.Frame(top)
        source_frame.grid(row=2, column=1, sticky="w", padx=4)
        self._reg(
            ttk.Radiobutton(source_frame, variable=self.library_source_var, value="pdb"),
            "source_pdb",
        ).pack(side="left")
        self._reg(
            ttk.Radiobutton(source_frame, variable=self.library_source_var, value="onelib"),
            "source_onelib",
        ).pack(side="left", padx=(12, 0))

        top.columnconfigure(1, weight=1)

        btns = ttk.Frame(self)
        btns.pack(fill="x", **pad)
        self._reg(ttk.Button(btns, command=self._load), "btn_load").pack(side="left")

        # ---- Notebook: プレイリストモード / BPM検索モード ----
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, **pad)

        self.playlist_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.playlist_tab, text="Playlist mode")
        self._build_playlist_tab(self.playlist_tab)

        self.bpm_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.bpm_tab, text="BPM search mode")
        self._build_bpm_tab(self.bpm_tab)

        naming = ttk.LabelFrame(self)
        self._reg(naming, "group_naming")
        naming.pack(fill="x", **pad)

        self.mp3_only_var = tk.BooleanVar(value=False)
        self._reg(
            ttk.Checkbutton(naming, variable=self.mp3_only_var), "chk_mp3_only"
        ).grid(row=0, column=0, columnspan=4, sticky="w", padx=6, pady=(4, 2))

        self._reg(ttk.Label(naming), "label_name_source").grid(row=1, column=0, sticky="w", padx=6)
        self.name_source_var = tk.StringVar(value="original")
        rb_name_original = ttk.Radiobutton(
            naming, variable=self.name_source_var, value="original", command=self._update_tag_order_state
        )
        self._reg(rb_name_original, "name_source_original").grid(row=1, column=1, sticky="w")
        rb_name_tag = ttk.Radiobutton(
            naming, variable=self.name_source_var, value="tag", command=self._update_tag_order_state
        )
        self._reg(rb_name_tag, "name_source_tag").grid(row=1, column=2, sticky="w")

        self.tag_order_label = ttk.Label(naming)
        self._reg(self.tag_order_label, "label_tag_order").grid(row=2, column=0, sticky="w", padx=6)
        self.tag_order_var = tk.StringVar(value="artist_title")
        self.tag_order_rb1 = ttk.Radiobutton(naming, variable=self.tag_order_var, value="artist_title")
        self._reg(self.tag_order_rb1, "tag_order_artist_title").grid(row=2, column=1, sticky="w")
        self.tag_order_rb2 = ttk.Radiobutton(naming, variable=self.tag_order_var, value="title_artist")
        self._reg(self.tag_order_rb2, "tag_order_title_artist").grid(row=2, column=2, sticky="w")
        self._update_tag_order_state()

        self._reg(ttk.Label(naming), "label_seq_position").grid(row=3, column=0, sticky="w", padx=6)
        self.seq_position_var = tk.StringVar(value="prefix")
        self._reg(
            ttk.Radiobutton(naming, variable=self.seq_position_var, value="prefix"), "seq_prefix"
        ).grid(row=3, column=1, sticky="w")
        self._reg(
            ttk.Radiobutton(naming, variable=self.seq_position_var, value="suffix"), "seq_suffix"
        ).grid(row=3, column=2, sticky="w")

        ttk.Style(self).configure("Wrap.TCheckbutton", wraplength=800, justify="left")
        self.romanize_var = tk.BooleanVar(value=False)
        romanize_chk = ttk.Checkbutton(naming, variable=self.romanize_var, style="Wrap.TCheckbutton")
        self._reg(romanize_chk, "chk_romanize").grid(
            row=4, column=0, columnspan=4, sticky="w", padx=6, pady=(2, 4)
        )

        opts = ttk.Frame(self)
        opts.pack(fill="x", **pad)
        self.dry_run_var = tk.BooleanVar(value=False)
        self._reg(ttk.Checkbutton(opts, variable=self.dry_run_var), "chk_dry_run").pack(side="left")
        self.copy_btn = self._reg(ttk.Button(opts, command=self._start_copy), "btn_copy")
        self.copy_btn.pack(side="right")

        self.progress = ttk.Progressbar(self, mode="determinate")
        self.progress.pack(fill="x", **pad)

        log_frame = ttk.Frame(self)
        log_frame.pack(fill="both", expand=True, **pad)
        self.log = tk.Text(log_frame, height=8, state="disabled")
        self.log.pack(side="left", fill="both", expand=True)
        log_scroll = ttk.Scrollbar(log_frame, orient="vertical", command=self.log.yview)
        self.log.configure(yscrollcommand=log_scroll.set)
        log_scroll.pack(side="right", fill="y")

    def _build_playlist_tab(self, parent):
        btns = ttk.Frame(parent)
        btns.pack(fill="x", padx=4, pady=4)
        self._reg(
            ttk.Button(btns, command=lambda: self._set_all(True)), "btn_select_all"
        ).pack(side="left")
        self._reg(ttk.Button(btns, command=lambda: self._set_all(False)), "btn_deselect_all").pack(
            side="left", padx=4
        )

        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill="both", expand=True, padx=4, pady=4)

        self.tree = ttk.Treeview(
            tree_frame, columns=("sel", "name", "count"), show="headings", selectmode="none"
        )
        self.tree.column("sel", width=60, anchor="center")
        self.tree.column("name", width=400, anchor="w")
        self.tree.column("count", width=80, anchor="center")
        self.tree.pack(side="left", fill="both", expand=True)
        self.tree.bind("<Button-1>", self._on_tree_click)

        scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")

    def _build_bpm_tab(self, parent):
        search_bar = ttk.Frame(parent)
        search_bar.pack(fill="x", padx=4, pady=4)

        self._reg(ttk.Label(search_bar), "label_bpm_target").grid(row=0, column=0, sticky="w")
        self.bpm_target_var = tk.StringVar(value="128")
        ttk.Entry(search_bar, textvariable=self.bpm_target_var, width=10).grid(
            row=0, column=1, sticky="w", padx=(4, 16)
        )

        self._reg(ttk.Label(search_bar), "label_bpm_tolerance").grid(row=0, column=2, sticky="w")
        self.bpm_tolerance_var = tk.StringVar(value="1")
        ttk.Entry(search_bar, textvariable=self.bpm_tolerance_var, width=10).grid(
            row=0, column=3, sticky="w", padx=4
        )

        self._reg(ttk.Label(search_bar), "label_genre").grid(row=0, column=4, sticky="w", padx=(16, 0))
        self.genre_var = tk.StringVar(value="")
        self.genre_combo = ttk.Combobox(
            search_bar, textvariable=self.genre_var, state="readonly", width=18
        )
        self.genre_combo.grid(row=0, column=5, sticky="w", padx=4)

        self._reg(ttk.Button(search_bar, command=self._bpm_search), "btn_bpm_search").grid(
            row=0, column=6, sticky="w", padx=(16, 0)
        )

        folder_bar = ttk.Frame(parent)
        folder_bar.pack(fill="x", padx=4, pady=(0, 4))
        self._reg(ttk.Label(folder_bar), "label_bpm_folder").pack(side="left")
        self.bpm_folder_var = tk.StringVar()
        ttk.Entry(folder_bar, textvariable=self.bpm_folder_var).pack(
            side="left", fill="x", expand=True, padx=4
        )

        btns = ttk.Frame(parent)
        btns.pack(fill="x", padx=4, pady=4)
        self._reg(
            ttk.Button(btns, command=lambda: self._set_all_bpm(True)), "btn_select_all"
        ).pack(side="left")
        self._reg(ttk.Button(btns, command=lambda: self._set_all_bpm(False)), "btn_deselect_all").pack(
            side="left", padx=4
        )

        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill="both", expand=True, padx=4, pady=4)

        self.bpm_tree = ttk.Treeview(
            tree_frame, columns=("sel", "title", "artist", "bpm"), show="headings", selectmode="none"
        )
        self.bpm_tree.column("sel", width=60, anchor="center")
        self.bpm_tree.column("title", width=280, anchor="w")
        self.bpm_tree.column("artist", width=180, anchor="w")
        self.bpm_tree.column("bpm", width=80, anchor="center")
        for col in ("title", "artist", "bpm"):
            self.bpm_tree.heading(col, command=lambda c=col: self._sort_bpm_tree(c))
        self.bpm_tree.pack(side="left", fill="both", expand=True)
        self.bpm_tree.bind("<Button-1>", self._on_bpm_tree_click)

        scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.bpm_tree.yview)
        self.bpm_tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")

    # ---------- helpers ----------

    def _browse_usb(self):
        path = filedialog.askdirectory(title=self.t("browse_title_usb"))
        if path:
            self.usb_var.set(path)

    def _browse_out(self):
        path = filedialog.askdirectory(title=self.t("browse_title_out"))
        if path:
            self.out_var.set(path)

    def _log(self, text: str):
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _clear_log(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    def _reason_text(self, item: core.CopyItem) -> str:
        if not item.reason_code:
            return ""
        return self.t(item.reason_code, **item.reason_params)

    def _error_text(self, e: Exception) -> str:
        code = getattr(e, "code", None)
        if code:
            return self.t(code, **getattr(e, "params", {}))
        return str(e)

    def _is_bpm_tab_active(self) -> bool:
        return self.notebook.select() == str(self.bpm_tab)

    # ---------- loading library ----------

    def _load(self):
        usb_root = self.usb_var.get().strip()
        if not usb_root:
            messagebox.showwarning(self.t("title_warn"), self.t("msg_usb_missing"))
            return
        usb_path = Path(usb_root)
        if not usb_path.exists():
            messagebox.showerror(self.t("title_error"), self.t("msg_folder_missing", path=usb_root))
            return

        source = self.library_source_var.get()
        source_label = self.t("source_pdb" if source == "pdb" else "source_onelib")
        self._clear_log()
        self._log(self.t("log_loading", source=source_label, path=str(usb_path)))
        self.tree.delete(*self.tree.get_children())
        self.bpm_tree.delete(*self.bpm_tree.get_children())
        self.bpm_results = []
        self.bpm_selected = {}

        def work():
            try:
                tracks, playlists = core.load_playlists(usb_path, source=source)
                self.event_queue.put(("loaded", tracks, playlists))
            except (
                core.PdbLibraryMissingError,
                core.PdbNotFoundError,
                core.OneLibraryMissingError,
                core.OneLibraryNotFoundError,
            ) as e:
                self.event_queue.put(("error", self._error_text(e)))
            except Exception as e:  # noqa: BLE001
                self.event_queue.put(("error", self.t("log_load_failed", error=e)))

        threading.Thread(target=work, daemon=True).start()

    def _on_loaded(self, tracks, playlists):
        self.tracks = tracks
        self.playlists = playlists
        self.selected = {pl.id: True for pl in playlists}
        for pl in playlists:
            self.tree.insert(
                "", "end", iid=str(pl.id), values=("✓", pl.name, len(pl.track_ids))
            )
        self._log(self.t("log_loaded", n=len(playlists), m=len(tracks)))
        if not playlists:
            self._log(self.t("log_no_playlists"))

        self._genre_list = core.list_genres(tracks)
        self._refresh_genre_combo()

    def _on_tree_click(self, event):
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return
        col = self.tree.identify_column(event.x)
        row = self.tree.identify_row(event.y)
        if not row or col != "#1":
            return
        pl_id = int(row)
        self.selected[pl_id] = not self.selected.get(pl_id, True)
        mark = "✓" if self.selected[pl_id] else " "
        vals = list(self.tree.item(row, "values"))
        vals[0] = mark
        self.tree.item(row, values=vals)

    def _set_all(self, value: bool):
        for pl in self.playlists:
            self.selected[pl.id] = value
            mark = "✓" if value else " "
            vals = list(self.tree.item(str(pl.id), "values"))
            if vals:
                vals[0] = mark
                self.tree.item(str(pl.id), values=vals)

    # ---------- BPM search mode ----------

    def _bpm_search(self):
        if not self.tracks:
            messagebox.showwarning(self.t("title_not_loaded"), self.t("msg_not_loaded"))
            return
        try:
            target = float(self.bpm_target_var.get())
            tolerance = float(self.bpm_tolerance_var.get())
        except ValueError:
            messagebox.showwarning(self.t("title_warn"), self.t("msg_bpm_invalid"))
            return

        genre_sel = self.genre_var.get()
        genre = genre_sel if genre_sel and genre_sel != self.t("genre_all") else None

        results = core.search_tracks_by_bpm(self.tracks, target, tolerance, genre=genre)
        self.bpm_results = results
        self.bpm_selected = {track.id: True for track in results}

        self.bpm_tree.delete(*self.bpm_tree.get_children())
        for track in results:
            bpm_str = f"{track.bpm:.2f}" if track.bpm is not None else "-"
            self.bpm_tree.insert(
                "", "end", iid=str(track.id), values=("✓", track.title, track.artist, bpm_str)
            )
        self._apply_bpm_sort()

        if not self.bpm_folder_var.get().strip():
            target_str = f"{target:g}"
            suffix = f"_{genre}" if genre else ""
            self.bpm_folder_var.set(f"bpm_{target_str}{suffix}")

        self._log(self.t("log_bpm_found", n=len(results), target=target, tol=tolerance))

    def _on_bpm_tree_click(self, event):
        region = self.bpm_tree.identify("region", event.x, event.y)
        if region != "cell":
            return
        col = self.bpm_tree.identify_column(event.x)
        row = self.bpm_tree.identify_row(event.y)
        if not row or col != "#1":
            return
        tid = int(row)
        self.bpm_selected[tid] = not self.bpm_selected.get(tid, True)
        mark = "✓" if self.bpm_selected[tid] else " "
        vals = list(self.bpm_tree.item(row, "values"))
        vals[0] = mark
        self.bpm_tree.item(row, values=vals)

    def _set_all_bpm(self, value: bool):
        for track in self.bpm_results:
            self.bpm_selected[track.id] = value
            mark = "✓" if value else " "
            vals = list(self.bpm_tree.item(str(track.id), "values"))
            if vals:
                vals[0] = mark
                self.bpm_tree.item(str(track.id), values=vals)

    # ---------- copying ----------

    def _start_copy(self):
        if not self.tracks:
            messagebox.showwarning(self.t("title_not_loaded"), self.t("msg_not_loaded"))
            return
        out_root = self.out_var.get().strip()
        if not out_root:
            messagebox.showwarning(self.t("title_warn"), self.t("msg_out_missing"))
            return

        if self._is_bpm_tab_active():
            chosen_ids = [t.id for t in self.bpm_results if self.bpm_selected.get(t.id, True)]
            if not chosen_ids:
                messagebox.showwarning(self.t("title_no_selection"), self.t("msg_no_selection"))
                return
            folder_name = self.bpm_folder_var.get().strip()
            if not folder_name:
                messagebox.showwarning(self.t("title_warn"), self.t("msg_bpm_folder_missing"))
                return
            chosen_playlists = [core.make_search_playlist(folder_name, chosen_ids)]
        else:
            chosen_playlists = [pl for pl in self.playlists if self.selected.get(pl.id, True)]
            if not chosen_playlists:
                messagebox.showwarning(self.t("title_no_selection"), self.t("msg_no_selection"))
                return

        usb_path = Path(self.usb_var.get().strip())
        out_path = Path(out_root)
        dry_run = self.dry_run_var.get()

        try:
            plan = core.build_copy_plan(
                usb_path,
                out_path,
                self.tracks,
                chosen_playlists,
                mp3_only=self.mp3_only_var.get(),
                name_source=self.name_source_var.get(),
                seq_position=self.seq_position_var.get(),
                tag_order=self.tag_order_var.get(),
                romanize=self.romanize_var.get(),
            )
        except core.RomajiLibraryMissingError as e:
            messagebox.showerror(self.t("title_error"), self._error_text(e))
            return
        total = len(plan)
        ok_count = sum(1 for p in plan if p.ok)
        missing = total - ok_count

        msg = self.t("confirm_summary", n=len(chosen_playlists), total=total)
        if missing:
            msg += self.t("confirm_missing", m=missing)
        msg += "\n\n" + (self.t("confirm_dry_run_note") if dry_run else self.t("confirm_dest", path=out_path))
        msg += self.t("confirm_continue")
        if not messagebox.askyesno(self.t("title_confirm"), msg):
            return

        self.copy_btn.configure(state="disabled")
        self.progress.configure(maximum=max(total, 1), value=0)
        self._clear_log()
        self._log(self.t("log_copy_start", prefix=self.t("dry_run_tag") if dry_run else "", n=total))

        def progress_cb(item: core.CopyItem, i: int, n: int):
            self.event_queue.put(("progress", item, i, n))

        def work():
            results = core.execute_copy_plan(plan, dry_run=dry_run, progress_cb=progress_cb)
            self.event_queue.put(("done", results))

        threading.Thread(target=work, daemon=True).start()

    # ---------- queue polling (thread -> UI) ----------

    def _poll_queue(self):
        try:
            while True:
                event = self.event_queue.get_nowait()
                kind = event[0]
                if kind == "loaded":
                    self._on_loaded(event[1], event[2])
                elif kind == "error":
                    messagebox.showerror(self.t("title_error"), event[1])
                    self._log(self.t("log_error_prefix", error=event[1]))
                elif kind == "progress":
                    item, i, n = event[1], event[2], event[3]
                    self.progress.configure(value=i)
                    if item.ok:
                        self._log(
                            self.t("log_progress_ok", i=i, n=n, playlist=item.playlist_name, name=item.dst.name)
                        )
                    else:
                        self._log(
                            self.t(
                                "log_progress_skip",
                                i=i,
                                n=n,
                                playlist=item.playlist_name,
                                reason=self._reason_text(item),
                            )
                        )
                elif kind == "done":
                    results = event[1]
                    ok = sum(1 for r in results if r.ok)
                    ng = len(results) - ok
                    self._log(self.t("log_done", ok=ok, ng=ng))
                    self.copy_btn.configure(state="normal")
                    messagebox.showinfo(self.t("title_done"), self.t("done_msg", ok=ok, ng=ng))
        except queue.Empty:
            pass
        self.after(100, self._poll_queue)


if __name__ == "__main__":
    app = App()
    app.mainloop()
