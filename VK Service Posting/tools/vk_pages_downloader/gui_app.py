#!/usr/bin/env python3
"""VK Clips Downloader — GUI для загрузки клипов по vk_pages.txt."""

from __future__ import annotations

import os
import sys
import threading
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from download_vk_clips import DownloadConfig, DownloadProgress, run_download

APP_TITLE = "VK Clips Downloader"
APP_VERSION = "1.0.0"


def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


class VkClipsDownloaderApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()

        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")

        self.title(f"{APP_TITLE} {APP_VERSION}")
        self.geometry("720x720")
        self.minsize(680, 680)

        self._cancel = threading.Event()
        self._worker: threading.Thread | None = None

        self._build_ui()

    def _build_ui(self) -> None:
        pad = {"padx": 16, "pady": (8, 4)}

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(16, 8))
        ctk.CTkLabel(
            header,
            text=APP_TITLE,
            font=ctk.CTkFont(size=22, weight="bold"),
        ).pack(anchor="w")
        ctk.CTkLabel(
            header,
            text="Скачивание клипов VK с вашего ПК по файлу vk_pages.txt из архива «Ссылки»",
            font=ctk.CTkFont(size=13),
            text_color=("#555555", "#aaaaaa"),
            wraplength=680,
            justify="left",
        ).pack(anchor="w", pady=(4, 0))
        ctk.CTkLabel(
            header,
            text="① Обзор… → выберите vk_pages.txt   ② внизу окна — «Начать загрузку»",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("#1f6aa5", "#63b3ed"),
        ).pack(anchor="w", pady=(8, 0))

        form = ctk.CTkFrame(self)
        form.pack(fill="x", padx=16, pady=8)

        self.input_var = ctk.StringVar()
        self._row_file(
            form,
            "Список ссылок",
            self.input_var,
            self._browse_input,
            0,
            hint="vk_pages.txt или папка с архивом",
        )

        self.output_var = ctk.StringVar()
        self._row_file(
            form,
            "Папка для видео",
            self.output_var,
            self._browse_output,
            1,
            hint="пусто = подпапка clips рядом со списком",
        )

        opts = ctk.CTkFrame(form, fg_color="transparent")
        opts.grid(row=2, column=0, columnspan=3, sticky="ew", padx=12, pady=8)

        ctk.CTkLabel(opts, text="Потоков загрузки").grid(row=0, column=0, sticky="w")
        self.workers_slider = ctk.CTkSlider(opts, from_=1, to=8, number_of_steps=7, width=200)
        self.workers_slider.set(3)
        self.workers_slider.grid(row=0, column=1, padx=12)
        self.workers_label = ctk.CTkLabel(opts, text="3")
        self.workers_label.grid(row=0, column=2)
        self.workers_slider.configure(command=lambda v: self.workers_label.configure(text=str(int(v))))

        ctk.CTkLabel(opts, text="Прокси (необяз.)").grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.proxy_entry = ctk.CTkEntry(
            opts,
            placeholder_text="http://user:pass@host:port",
            width=360,
        )
        self.proxy_entry.grid(row=1, column=1, columnspan=2, sticky="ew", padx=12, pady=(8, 0))

        self.cookies_var = ctk.StringVar()
        self._row_file(
            form,
            "Cookies VK",
            self.cookies_var,
            self._browse_cookies,
            3,
            hint="необязательно, Netscape cookies.txt",
        )

        form.grid_columnconfigure(1, weight=1)

        prog_frame = ctk.CTkFrame(self)
        prog_frame.pack(fill="x", padx=16, pady=8)
        self.status_label = ctk.CTkLabel(prog_frame, text="Готов к загрузке", anchor="w")
        self.status_label.pack(fill="x", padx=12, pady=(12, 4))
        self.progress = ctk.CTkProgressBar(prog_frame)
        self.progress.pack(fill="x", padx=12, pady=4)
        self.progress.set(0)
        self.stats_label = ctk.CTkLabel(
            prog_frame,
            text="0 / 0  ·  успешно 0  ·  ошибок 0",
            text_color=("#666666", "#999999"),
        )
        self.stats_label.pack(fill="x", padx=12, pady=(0, 12))

        # Кнопки внизу окна — всегда видны (не под журналом)
        actions = ctk.CTkFrame(self)
        actions.pack(side="bottom", fill="x", padx=16, pady=(8, 16))

        self.start_btn = ctk.CTkButton(
            actions,
            text="▶  Начать загрузку",
            height=48,
            font=ctk.CTkFont(size=16, weight="bold"),
            command=self._start,
        )
        self.start_btn.pack(side="left", expand=True, fill="x", padx=(0, 8))

        self.stop_btn = ctk.CTkButton(
            actions,
            text="Стоп",
            height=48,
            width=100,
            fg_color=("#c0392b", "#922b21"),
            hover_color=("#e74c3c", "#c0392b"),
            command=self._stop,
            state="disabled",
        )
        self.stop_btn.pack(side="left", padx=(0, 8))

        self.folder_btn = ctk.CTkButton(
            actions,
            text="Папка",
            height=48,
            width=100,
            command=self._open_folder,
            state="disabled",
        )
        self.folder_btn.pack(side="left")

        log_frame = ctk.CTkFrame(self)
        log_frame.pack(fill="both", expand=True, padx=16, pady=(0, 8))
        ctk.CTkLabel(log_frame, text="Журнал", anchor="w").pack(
            fill="x",
            padx=12,
            pady=(8, 4),
        )
        self.log_box = ctk.CTkTextbox(
            log_frame,
            height=140,
            font=ctk.CTkFont(family="Consolas", size=12),
        )
        self.log_box.pack(fill="x", padx=12, pady=(0, 10))
        self.log_box.configure(state="disabled")

        self._last_output: Path | None = None

    def _row_file(
        self,
        parent: ctk.CTkFrame,
        label: str,
        variable: ctk.StringVar,
        command,
        row: int,
        hint: str = "",
    ) -> None:
        ctk.CTkLabel(parent, text=label, anchor="w").grid(
            row=row,
            column=0,
            sticky="nw",
            padx=12,
            pady=10,
        )
        col = ctk.CTkFrame(parent, fg_color="transparent")
        col.grid(row=row, column=1, sticky="ew", padx=4, pady=8)
        entry = ctk.CTkEntry(col, textvariable=variable)
        entry.pack(fill="x")
        if hint:
            ctk.CTkLabel(
                col,
                text=hint,
                font=ctk.CTkFont(size=11),
                text_color=("#888888", "#777777"),
            ).pack(anchor="w", pady=(2, 0))
        ctk.CTkButton(
            parent,
            text="Обзор…",
            width=90,
            command=command,
        ).grid(row=row, column=2, padx=12, pady=10)

    def _browse_input(self) -> None:
        path = filedialog.askopenfilename(
            title="Файл со ссылками",
            filetypes=[
                ("Списки ссылок", "*.txt"),
                ("Все файлы", "*.*"),
            ],
        )
        if not path:
            path = filedialog.askdirectory(title="Папка с архивом «Ссылки»")
        if path:
            self.input_var.set(path)
            if not self.output_var.get().strip():
                p = Path(path)
                base = p.parent if p.is_file() else p
                self.output_var.set(str(base / "clips"))

    def _browse_output(self) -> None:
        path = filedialog.askdirectory(title="Папка для сохранения видео")
        if path:
            self.output_var.set(path)

    def _browse_cookies(self) -> None:
        path = filedialog.askopenfilename(
            title="cookies.txt",
            filetypes=[("Cookies", "*.txt"), ("Все", "*.*")],
        )
        if path:
            self.cookies_var.set(path)

    def _log(self, line: str) -> None:
        self.log_box.configure(state="normal")
        self.log_box.insert("end", line + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _on_progress(self, p: DownloadProgress) -> None:
        def ui() -> None:
            if p.total:
                self.progress.set(p.done / p.total)
            self.stats_label.configure(
                text=f"{p.done} / {p.total}  ·  успешно {p.ok}  ·  ошибок {p.fail}",
            )
            if p.message:
                self.status_label.configure(text=p.message[:120])
                if p.done > 0 or p.finished:
                    self._log(p.message)

        self.after(0, ui)

    def _start(self) -> None:
        inp = self.input_var.get().strip()
        if not inp:
            messagebox.showwarning(APP_TITLE, "Укажите файл vk_pages.txt или папку с архивом.")
            return
        if not Path(inp).exists():
            messagebox.showerror(APP_TITLE, f"Путь не найден:\n{inp}")
            return

        out = self.output_var.get().strip()
        proxy = self.proxy_entry.get().strip() or None
        cookies = self.cookies_var.get().strip() or None

        config = DownloadConfig(
            input_path=Path(inp),
            output_dir=Path(out) if out else None,
            workers=int(self.workers_slider.get()),
            proxy=proxy,
            cookies_file=cookies,
        )

        self._cancel.clear()
        self.progress.set(0)
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")
        self._log("Запуск…")

        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.folder_btn.configure(state="disabled")
        self._last_output = None

        def work() -> None:
            try:
                result = run_download(config, on_progress=self._on_progress, cancel_event=self._cancel)
                self._last_output = result.output_dir

                def done() -> None:
                    self.start_btn.configure(state="normal")
                    self.stop_btn.configure(state="disabled")
                    self.folder_btn.configure(state="normal" if self._last_output else "disabled")
                    if result.ok:
                        messagebox.showinfo(
                            APP_TITLE,
                            f"Скачано файлов: {result.ok}\nОшибок: {result.fail}\n\n{result.output_dir}",
                        )
                    elif self._cancel.is_set():
                        messagebox.showinfo(APP_TITLE, "Загрузка остановлена.")
                    else:
                        messagebox.showwarning(
                            APP_TITLE,
                            f"Не удалось скачать клипы.\nОшибок: {result.fail}\n\n"
                            f"См. {result.errors_path}",
                        )

                self.after(0, done)
            except Exception as e:
                def err() -> None:
                    self.start_btn.configure(state="normal")
                    self.stop_btn.configure(state="disabled")
                    messagebox.showerror(APP_TITLE, str(e))

                self.after(0, err)

        self._worker = threading.Thread(target=work, daemon=True)
        self._worker.start()

    def _stop(self) -> None:
        self._cancel.set()
        self.status_label.configure(text="Останавливаем…")
        self._log("Запрошена остановка…")

    def _open_folder(self) -> None:
        if self._last_output and self._last_output.is_dir():
            os.startfile(self._last_output)
        elif self.output_var.get().strip():
            p = Path(self.output_var.get().strip())
            if p.is_dir():
                os.startfile(p)


def main() -> None:
    app = VkClipsDownloaderApp()
    app.mainloop()


if __name__ == "__main__":
    main()
