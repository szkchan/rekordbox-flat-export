"""簡易な辞書ベースの多言語対応。app.py から t(lang, key, **params) の形で使う。"""

from __future__ import annotations

LANGS = ["en", "ja"]

LANG_LABELS = {"ja": "日本語", "en": "English"}

STRINGS: dict[str, dict[str, str]] = {
    "ja": {
        # ウィンドウ / 静的ラベル
        "window_title": "rekordbox USB プレイリスト展開ツール",
        "label_language": "言語:",
        "label_usb": "コピー元 USB (rekordbox 書き出し先):",
        "label_out": "出力先フォルダ:",
        "label_source": "変換元ライブラリ:",
        "source_pdb": "export.pdb (安定)",
        "source_onelib": "One Library / exportLibrary.db (ベータ)",
        "browse": "参照...",
        "btn_load": "プレイリスト読み込み",
        "btn_select_all": "全選択",
        "btn_deselect_all": "全解除",
        "col_sel": "コピー",
        "col_name": "プレイリスト名 (出力フォルダ名)",
        "col_count": "曲数",
        "group_naming": "ファイル名・フォルダ名のオプション",
        "chk_mp3_only": "mp3のみコピーする（それ以外は除外）",
        "label_name_source": "ファイル名の元:",
        "name_source_original": "元のファイル名",
        "name_source_tag": "タグ（アーティスト名・曲名）",
        "label_tag_order": "タグの順序:",
        "tag_order_artist_title": "アーティスト名 - 曲名",
        "tag_order_title_artist": "曲名 - アーティスト名",
        "label_seq_position": "連番の位置:",
        "seq_prefix": "先頭 (01_名前.mp3)",
        "seq_suffix": "末尾 (名前_01.mp3)",
        "chk_romanize": (
            "マルチバイト文字をローマ字化する"
            "（文字化け対策：一部のCDJ/他社プレイヤーで日本語等が表示できない場合に。pykakasi使用、フォルダ名にも適用）"
        ),
        "chk_dry_run": "ドライラン（実際にはコピーせずログのみ表示）",
        "btn_copy": "コピー実行",
        # ダイアログタイトル
        "title_warn": "未入力",
        "title_error": "エラー",
        "title_confirm": "確認",
        "title_done": "完了",
        "title_not_loaded": "未読み込み",
        "title_no_selection": "未選択",
        # ダイアログ本文
        "browse_title_usb": "rekordbox 書き出し済み USB のルートフォルダを選択",
        "browse_title_out": "出力先フォルダを選択",
        "msg_usb_missing": "コピー元 USB のフォルダを指定してください。",
        "msg_folder_missing": "フォルダが存在しません: {path}",
        "msg_out_missing": "出力先フォルダを指定してください。",
        "msg_not_loaded": "先にプレイリストを読み込んでください。",
        "msg_no_selection": "コピーするプレイリストを1つ以上選択してください。",
        "confirm_summary": "{n} プレイリスト、{total} 曲が対象です。",
        "confirm_missing": "\nうち {m} 曲は対象外（ファイルが見つからない／mp3以外）としてスキップされます。",
        "confirm_dry_run_note": "ドライラン（コピーは行いません）",
        "confirm_dest": "コピー先: {path}",
        "confirm_continue": "\n続行しますか？",
        "done_msg": "コピーが完了しました。\n成功: {ok} 件\n失敗・スキップ: {ng} 件",
        # ログ
        "log_loading": "読み込み中 ({source}): {path}",
        "log_loaded": "{n} 件のプレイリスト、{m} 件のトラックを読み込みました。",
        "log_no_playlists": "トラックを含むプレイリストが見つかりませんでした。",
        "log_load_failed": "読み込みに失敗しました: {error}",
        "log_error_prefix": "エラー: {error}",
        "log_copy_start": "{prefix}コピーを開始します... ({n} 曲)",
        "dry_run_tag": "[ドライラン] ",
        "log_progress_ok": "[{i}/{n}] OK: {playlist}/{name}",
        "log_progress_skip": "[{i}/{n}] スキップ ({playlist}): {reason}",
        "log_done": "完了: 成功 {ok} 件 / 失敗・スキップ {ng} 件",
        # core.py のエラーコード / スキップ理由コード
        "err_pdb_not_found": (
            "{usb_root} 配下に PIONEER/rekordbox/export.pdb が見つかりませんでした。"
            "rekordbox で「デバイスにエクスポート」した USB のルートフォルダを選択してください。"
        ),
        "err_pdb_lib_missing": (
            "rekordbox-pdb ライブラリが見つかりません。以下でインストールしてください:\n{cmd}"
        ),
        "err_onelib_not_found": (
            "{usb_root} 配下に PIONEER/rekordbox/exportLibrary.db が見つかりませんでした。"
            "One Library (Device Library Plus) 形式で書き出された USB か確認してください。"
        ),
        "err_onelib_lib_missing": (
            "One Library 対応の pyrekordbox が見つかりません（未リリースの開発版が必要です）。"
            "以下でインストールしてください:\n{cmd}"
        ),
        "err_romaji_lib_missing": "pykakasi ライブラリが見つかりません。以下でインストールしてください:\n{cmd}",
        "reason_track_not_in_db": "track id={id} が DB 内に見つかりません",
        "reason_file_not_found": "ファイルが見つかりません: {file_path} ({title})",
        "reason_excluded_non_mp3": "mp3以外のため除外: {filename}",
        "reason_copy_failed": "コピーに失敗しました: {error}",
    },
    "en": {
        "window_title": "rekordbox USB Playlist Exporter",
        "label_language": "Language:",
        "label_usb": "Source USB (rekordbox export):",
        "label_out": "Output folder:",
        "label_source": "Source library:",
        "source_pdb": "export.pdb (stable)",
        "source_onelib": "One Library / exportLibrary.db (beta)",
        "browse": "Browse...",
        "btn_load": "Load playlists",
        "btn_select_all": "Select all",
        "btn_deselect_all": "Deselect all",
        "col_sel": "Copy",
        "col_name": "Playlist name (output folder)",
        "col_count": "Tracks",
        "group_naming": "File / folder naming options",
        "chk_mp3_only": "Copy mp3 files only (exclude others)",
        "label_name_source": "File name source:",
        "name_source_original": "Original file name",
        "name_source_tag": "Tag (artist / title)",
        "label_tag_order": "Tag order:",
        "tag_order_artist_title": "Artist - Title",
        "tag_order_title_artist": "Title - Artist",
        "label_seq_position": "Sequence number position:",
        "seq_prefix": "Prefix (01_name.mp3)",
        "seq_suffix": "Suffix (name_01.mp3)",
        "chk_romanize": (
            "Romanize multi-byte characters "
            "(prevents mojibake/garbled text on CDJs or players that can't display Japanese etc.; "
            "uses pykakasi, also applied to folder names)"
        ),
        "chk_dry_run": "Dry run (log only, no actual copying)",
        "btn_copy": "Start copy",
        "title_warn": "Missing input",
        "title_error": "Error",
        "title_confirm": "Confirm",
        "title_done": "Done",
        "title_not_loaded": "Not loaded",
        "title_no_selection": "Nothing selected",
        "browse_title_usb": "Select the root folder of a rekordbox-exported USB",
        "browse_title_out": "Select the output folder",
        "msg_usb_missing": "Please specify the source USB folder.",
        "msg_folder_missing": "Folder does not exist: {path}",
        "msg_out_missing": "Please specify an output folder.",
        "msg_not_loaded": "Please load playlists first.",
        "msg_no_selection": "Please select at least one playlist to copy.",
        "confirm_summary": "{n} playlist(s), {total} track(s) targeted.",
        "confirm_missing": "\n{m} track(s) will be skipped (file not found / not mp3).",
        "confirm_dry_run_note": "Dry run (nothing will actually be copied)",
        "confirm_dest": "Destination: {path}",
        "confirm_continue": "\nContinue?",
        "done_msg": "Copy finished.\nSucceeded: {ok}\nFailed/skipped: {ng}",
        "log_loading": "Loading ({source}): {path}",
        "log_loaded": "Loaded {n} playlist(s), {m} track(s).",
        "log_no_playlists": "No playlists containing tracks were found.",
        "log_load_failed": "Failed to load: {error}",
        "log_error_prefix": "Error: {error}",
        "log_copy_start": "{prefix}Starting copy... ({n} tracks)",
        "dry_run_tag": "[Dry run] ",
        "log_progress_ok": "[{i}/{n}] OK: {playlist}/{name}",
        "log_progress_skip": "[{i}/{n}] Skipped ({playlist}): {reason}",
        "log_done": "Done: {ok} succeeded / {ng} failed or skipped",
        "err_pdb_not_found": (
            "PIONEER/rekordbox/export.pdb was not found under {usb_root}. "
            "Please select the root folder of a USB exported from rekordbox (\"Export to device\")."
        ),
        "err_pdb_lib_missing": "The rekordbox-pdb library was not found. Please install it:\n{cmd}",
        "err_onelib_not_found": (
            "PIONEER/rekordbox/exportLibrary.db was not found under {usb_root}. "
            "Please check that the USB was exported in One Library (Device Library Plus) format."
        ),
        "err_onelib_lib_missing": (
            "pyrekordbox with One Library support was not found "
            "(an unreleased development build is required). Please install it:\n{cmd}"
        ),
        "err_romaji_lib_missing": "The pykakasi library was not found. Please install it:\n{cmd}",
        "reason_track_not_in_db": "track id={id} was not found in the database",
        "reason_file_not_found": "File not found: {file_path} ({title})",
        "reason_excluded_non_mp3": "Excluded (not mp3): {filename}",
        "reason_copy_failed": "Copy failed: {error}",
    },
}


def t(lang: str, key: str, **params) -> str:
    table = STRINGS.get(lang, STRINGS["ja"])
    template = table.get(key) or STRINGS["ja"].get(key, key)
    return template.format(**params) if params else template
