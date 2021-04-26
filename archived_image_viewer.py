import logging
import shutil
import sys
import tkinter as tk
import tkinter.messagebox as messagebox
import tkinter.ttk as ttk
import zipfile
from io import BytesIO
from pathlib import Path

from natsort import natsorted
from PIL import Image, ImageTk
from send2trash import send2trash

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    "%(asctime)s:%(name)s:%(funcName)s:%(lineno)d:%(levelname)s:%(message)s"
)
ch.setFormatter(formatter)
logger.addHandler(ch)


class AnimationGIF:
    def __init__(self):
        pass

    def open(self, path):
        pass


class ArchiveBase:
    def __init__(self):
        self.file_path = None
        self.file_list = []
        self.i = 0

    def open(self, file_path):
        pass

    def close(self):
        self.file_path = None
        self.file_list = []

    def suffix(self):
        return self.file_path.suffix.lower()

    def __getitem__(self, i):
        pass

    def __len__(self):
        return len(self.file_list)

    def next(self):
        self.i = min(self.i + 1, len(self) - 1)
        return self[self.i]

    def prev(self):
        self.i = max(self.i - 1, 0)
        return self[self.i]

    def current(self):
        return self.i

    def delete(self):
        pass


class ZipArchive(ArchiveBase):
    def __init__(self, file_path):
        super().__init__()
        self.open(file_path)

    def open(self, file_path):
        self.file_path = file_path
        self.file_list = []
        with zipfile.ZipFile(file_path) as f:
            self.file_list = natsorted(f.namelist())

        self.file_list = self.file_list[1:]
        logger.debug(self.file_list)

    def __getitem__(self, i):
        self.i = i
        file_name = ""
        file_byte = None
        if 0 <= i < len(self):
            with zipfile.ZipFile(self.file_path) as f:
                file_name = Path(self.file_list[i])
                file_byte = f.read(self.file_list[i])

        logger.debug(f"self.i={self.i}")
        logger.debug(self.file_list[i])
        logger.debug(file_name)
        return file_name, file_byte

    def delete(self):
        if self.file_path is not None:
            send2trash(self.file_path)


class DirectoryArchive(ArchiveBase):
    def __init__(self, file_path):
        super().__init__()
        self.open(file_path)

    def open(self, file_path):
        self.file_path = Path(file_path)
        self.file_list = natsorted(
            list(Path(self.file_path.parent).glob("*")), key=lambda x: str(x)
        )
        logger.debug(self.file_list)
        self.i = self.file_list.index(Path(file_path))
        logger.debug(f"self.i = {self.i}")

    def __getitem__(self, i):
        logger.debug(f"self.i = {self.i}")
        if 0 <= i < len(self):
            return self.file_list[i], None
        else:
            return "", None

    def delete(self):
        send2trash(self.file_list[self.i])


class ImageFrame(tk.Canvas):
    def __init__(self, master):
        super().__init__(master, highlightthickness=0)
        self.master = master
        self.item = None

        self.master.bind("<Configure>", lambda *kw: self.display(self.orig_image))
        self.mode = "FitInFrame"

    def resize_image(self, **kw):
        image = self.orig_image
        if self.mode == "Raw":
            return image
        elif self.mode == "FitInFrame":
            logger.debug("FitInFrame")
            return self.fit_in_frame(image)
        else:
            logger.debug("Not supported")

    def display(self, image):
        if image is not None:
            self.orig_image = image
            image = self.resize_image()

            self.image = ImageTk.PhotoImage(image=image)
            if self.item is not None:
                self.delete(self.item)
            self.configure(width=self.image.width(), height=self.image.height())
            sx, sy = self.center_shift(self.image.width(), self.image.height())
        else:
            self.image = None
            sx=0
            sy=0
        self.item = self.create_image(sx, sy, image=self.image, anchor="nw")

    def center_shift(self, image_width, image_height):
        return (self.width() - image_width) / 2, (self.height() - image_height) / 2

    def width(self):
        return self.master.winfo_width()

    def height(self):
        return self.master.winfo_height()

    def fit_in_frame(self, image):
        width = self.width()
        height = self.height()
        logger.debug(f"{width}, {height}")
        times = min(width / image.width, height / image.height)
        return image.resize((int(image.width * times), int(image.height * times)))


class ArchiveImageViewer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.style = ttk.Style()

        self.construct_gui()
        self.keybinding()

    def construct_gui(self):
        main_frame = ttk.Frame(self)
        main_frame.pack(expand=True, fill="both", anchor="center")
        main_frame.grid_rowconfigure([0], weight=1)
        main_frame.grid_columnconfigure([0], weight=1)

        self.image = ImageFrame(main_frame)
        self.image.grid(row=0, column=0, sticky="wens")

        dummy_img = Image.new("RGB", (10, 10), color="black")
        self.image.mode = "Raw"
        self.image.display(dummy_img)

    def keybinding(self):
        binding = {
            "l": self.prev_page,
            "h": self.next_page,
            "q": self.quit,
        }
        for k, v in binding.items():
            self.bind(f"<KeyPress-{k}>", v)

        self.bind(f"<Delete>", self.delete)

    def delete(self, event):
        if messagebox.askokcancel("Delete file?", "Delete file?"):
            print("Deleted.")
        else:
            print("Cancelled")

    def next_page(self, event):
        file_path, data = self.archive.next()
        if file_path == "":
            logger.debug("file_path is empty")
            return
        self.open_file(file_path, data)

    def prev_page(self, event):
        file_path, data = self.archive.prev()
        if file_path == "":
            logger.debug("file_path is empty")
            return
        logger.debug(file_path)
        self.open_file(file_path, data)

    def quit(self, event):
        self.destroy()

    def open(self, file_path):
        self.archive = self.open_archive(file_path)
        file_path, data = self.archive[self.archive.current()]
        self.open_file(file_path, data)

    def open_archive(self, file_path):
        suffix = Path(file_path).suffix.lower()
        if suffix == ".zip":
            return ZipArchive(file_path)
        else:
            return DirectoryArchive(file_path)

    def open_file(self, file_path, data=None):
        file_path = Path(file_path)
        suffix = file_path.suffix.lower()
        logger.debug(suffix)
        if suffix in [
            ".bmp",
            ".dib",
            ".eps",
            ".gif",
            ".icns",
            ".ico",
            ".im",
            ".jpg",
            ".jpeg",
            ".msp",
            ".pcx",
            ".ppm",
            ".sgi",
            ".spider",
            ".tga",
            ".xbm",
        ]:
            self.open_image(file_path, data)
        elif suffix in [".gif"]:
            pass
        elif suffix in [".png"]:
            pass
        elif suffix in [".tiff"]:
            # can have multi images
            pass
        elif suffix in [".webv"]:
            # can be sequence
            pass
        else:
            logger.debug(f"Not supported.:{suffix}")
            self.image.display(None)

    # can be animation
    def open_gif_image(self, gif_path):
        image = Image.open(gif_path)
        return image

    # can be animation
    def open_png_image(self, png_path):
        image = Image.open(png_path)
        return image

    def open_image(self, image_path, data=None):
        if data is None:
            image = Image.open(image_path)
        else:
            image = Image.open(BytesIO(data))
        if image is None:
            messagebox.showwarning("Image open failed.", "Image open failed.")
            return
        self.image.display(image)


def main():
    args = sys.argv
    if len(args) <= 1:
        print("file path is required.")
        return
    aiv = ArchiveImageViewer()
    aiv.open(Path(args[1]))
    aiv.image.mode = "FitInFrame"
    aiv.mainloop()


if __name__ == "__main__":
    main()
