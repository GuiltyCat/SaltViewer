import csv
import logging
import sys
import tkinter as tk
import tkinter.messagebox as messagebox
import tkinter.ttk as ttk
import zipfile
from io import BytesIO
from pathlib import Path

import py7zr
import rarfile
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
        return self[self.i]

    def delete(self):
        logger.debug(self.file_path)
        if self.file_path is not None:
            send2trash(str(self.file_path))


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
            self.file_path = self.file_list[i]
            self.i = i
            return self.file_list[i], None
        else:
            return "", None

    def delete(self):
        super().delete()
        self.next()
        file_path = self.file_list[self.i]
        self.open(file_path)


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
        return file_name, BytesIO(file_byte)


class RarArchive(ArchiveBase):
    def __init__(self, file_path):
        super().__init__()
        self.open(file_path)

    def open(self, file_path):
        self.file_path = file_path
        self.file_list = []
        with rarfile.RarFile(file_path) as f:
            self.file_list = natsorted(f.namelist())

        self.file_list = self.file_list[1:]
        logger.debug(self.file_list)

    def __getitem__(self, i):
        self.i = i
        file_name = ""
        file_byte = None
        if 0 <= i < len(self):
            with rarfile.RarFile(self.file_path) as f:
                file_name = Path(self.file_list[i])
                file_byte = f.read(self.file_list[i])

        logger.debug(f"self.i={self.i}")
        logger.debug(self.file_list[i])
        logger.debug(file_name)
        return file_name, BytesIO(file_byte)


class SevenZipArchive(ArchiveBase):
    def __init__(self, file_path):
        super().__init__()
        self.open(file_path)

    def open(self, file_path):
        self.file_path = file_path
        self.file_list = []
        with py7zr.SevenZipFile(file_path) as f:
            self.file_list = natsorted(f.getnames())

        self.file_list = self.file_list[1:]
        logger.debug(self.file_list)

    def __getitem__(self, i):
        self.i = i
        file_name = ""
        file_byte = None
        if 0 <= i < len(self):
            with py7zr.SevenZipFile(self.file_path) as f:
                file_name = Path(self.file_list[i])
                for name, data in f.read([self.file_list[i]]).items():
                    file_byte = data

        logger.debug(f"file_bype = {file_byte}")
        logger.debug(f"self.i={self.i}")
        logger.debug(self.file_list[i])
        logger.debug(file_name)
        return file_name, file_byte


class ImageFrame(tk.Canvas):
    def __init__(self, master):
        super().__init__(master, highlightthickness=0, bg="black")
        self.master = master
        self.item = None

        self.image = None
        self.image2 = None

        self.master.bind(
            "<Configure>", lambda *kw: self.display(self.image, self.image2)
        )
        self.mode = "FitInFrame"

    def resize_image(self, image, div=1):
        if image is None:
            return None
        if self.mode == "Raw":
            return image
        elif self.mode == "FitInFrame":
            logger.debug("FitInFrame")
            return self.fit_in_frame(image, div)
        else:
            logger.debug("Not supported")

    def merge_image(self, image, image2, right2left):
        if image is None or image2 is None:
            return image

        width = self.width()
        height = self.height()

        new_image = Image.new("RGB", (width, height))
        if right2left:
            image, image2 = image2, image

        # left
        left = int(width / 2 - image.width)
        upper = int((height - image.height) / 2)
        new_image.paste(image, (left, upper))
        # right
        left = int(width / 2)
        upper = int((height - image2.height) / 2)
        new_image.paste(image2, (left, upper))
        return new_image

    def display(self, image, image2=None, right2left=True):
        self.stop = True
        if hasattr(image, "is_animated") and image.is_animated:
            self.stop = False
            return self.display_animation(image, 0)
        self.image = image
        self.image2 = image2
        if image is not None:
            div = 1 if image2 is None else 2
            image = self.resize_image(image, div)
            image2 = self.resize_image(image2, div)

            new_image = self.merge_image(image, image2, right2left)
            self.tk_image = ImageTk.PhotoImage(image=new_image)
            if self.item is not None:
                self.delete(self.item)

            width = self.tk_image.width()
            height = self.tk_image.height()
            self.configure(width=width, height=height)
            sx, sy = self.center_shift(width, height)
        else:
            self.tk_image = None
            sx = 0
            sy = 0
        self.item = self.create_image(sx, sy, image=self.tk_image, anchor="nw")

    def display_animation(self, image, counter):
        if self.stop:
            return
        logger.debug(f"counter={counter}")
        counter %= image.n_frames
        image.seek(counter)

        new_image = self.resize_image(image)
        self.tk_image = ImageTk.PhotoImage(image=new_image)
        if self.item is not None:
            self.delete(self.item)
        width = self.tk_image.width()
        height = self.tk_image.height()
        self.configure(width=width, height=height)
        sx, sy = self.center_shift(width, height)
        self.item = self.create_image(sx, sy, image=self.tk_image, anchor="nw")
        self.after_idle(self.after, 0, self.display_animation, image, counter + 1)

    def center_shift(self, image_width, image_height):
        sx = (self.width() - image_width) / 2
        sy = (self.height() - image_height) / 2
        return sx, sy

    def width(self):
        return self.master.winfo_width()

    def height(self):
        return self.master.winfo_height()

    def fit_in_frame(self, image, div=1):
        width = self.width() / div
        height = self.height()
        logger.debug(f"{width}, {height}")
        times = min(width / image.width, height / image.height)

        size = (int(image.width * times), int(image.height * times))
        return image.resize(size)


class Config:
    def __init__(self):
        self.keymap = {}
        self.setting = {}
        pass

    def open(self, file_path):
        file_path = Path(file_path)
        if not file_path.exists():
            self.write_default(file_path)

        config = None
        with open(file_path, mode="r", newline="") as f:
            reader = csv.reader(f, delimiter="=")
            for row in reader:

                if len(row) == 0:
                    continue
                if row[0][0] == "#":
                    continue
                if row[0] == "[Setting]":
                    config = self.setting
                    continue
                if row[0] == "[Keymap]":
                    config = self.keymap
                    continue

                config[row[0].strip()] = row[1].strip()

    def write_default(self, file_path):
        config = """
# Fit can be Width, Height, Both
[Setting]

Fit = Width

# Resize algorithms
# | Filter   | Downscaling quality | Upscaling quality | Performance |
# | No       | -                   | -                 | ******      |
# | Nearest  | -                   | -                 | *****       |
# | Box      | *                   | -                 | ****        |
# | Bilinear | *                   | *                 | ***         |
# | Hamming  | **                  | -                 | ***         |
# | Bicubic  | ***                 | ***               | **          |
# | Lanczos  | ****                | ****              | *           |

DownScale   = Nearest
UpScale     = Nearest


[Keymap]

DoublePage  = d
DeleteFile  = Delete
NextPage    = h
PrevPage    = l
NextArchive = j
PrevArchive = k
PageOrder   = o
Quit        = q
Head        = g
Tail        = G
"""
        with open(file_path, "w") as f:
            f.write(config)


class ArchiveImageViewer(tk.Tk):
    def __init__(self, config_path="aiv.config"):
        super().__init__()
        self.binding = {
            "DoublePage": self.toggle_page_mode,
            "DeleteFile": self.delete,
            "NextPage": self.next_page,
            "PrevPage": self.prev_page,
            "NextArchive": self.next_archive,
            "PrevArchive": self.prev_archive,
            "PageOrder": self.toggle_order,
            "Quit": self.quit,
            "Head": self.head,
            "Tail": self.tail,
        }

        self.style = ttk.Style()

        self.config = Config()

        # temporary
        self.config.write_default(config_path)

        self.config.open(config_path)
        self.load_config()

        self.construct_gui()

        self.double_page = False
        self.right2left = True

    def load_config(self):
        print(self.config.keymap)
        print(self.config.setting)
        for name, key in self.config.keymap.items():
            func = self.binding[name]
            self.bind(f"<KeyPress-{key}>", func)

        # binding = {
        #    "l": self.prev_page,
        #    "h": self.next_page,
        #    "d": self.toggle_page_mode,
        #    "o": self.toggle_order,
        #    "q": self.quit,
        # }
        # for k, v in binding.items():

        # self.bind("<Delete>", self.delete)

    def head(self):
        pass

    def tail(self):
        pass

    def next_archive(self):
        pass

    def prev_archive(self):
        pass

    def construct_gui(self):
        self.main_frame = ttk.Frame(self)
        self.main_frame.pack(expand=True, fill="both", anchor="center")
        self.main_frame.grid_rowconfigure([0], weight=1)
        self.main_frame.grid_columnconfigure([0], weight=1)

        self.image = ImageFrame(self.main_frame)
        self.image.grid(row=0, column=0, sticky="wens")

        dummy_img = Image.new("RGB", (10, 10), color="black")
        self.image.mode = "Raw"
        self.image.display(dummy_img)

    def delete(self, event):
        if messagebox.askokcancel("Delete file?", "Delete file?"):
            print("Deleted.")
            self.current_page()
            self.archive.delete()
        else:
            print("Cancelled")

    def toggle_page_mode(self, event):
        self.double_page = not self.double_page
        logger.debug(f"DoublePage:{self.double_page}")
        self.current_page()

    def toggle_order(self, event):
        logger.debug("toggle order")
        self.right2left = not self.right2left

    def current_page(self):
        file_path, data = self.archive.current()
        if file_path == "":
            logger.debug("file_path is empty")
            return None
        image = self.open_file(file_path, data)
        image2 = None
        if self.double_page:
            image2 = self._open_next()
            # back to current
            self.archive.prev()
        self.image.display(image, image2, self.right2left)

    def _open_next(self):
        file_path, data = self.archive.next()
        if file_path == "":
            logger.debug("file_path is empty")
            return None
        return self.open_file(file_path, data)

    def next_page(self, event):
        logger.debug("called")

        # back to the second page then next
        if self.double_page:
            self.archive.next()
        image = self._open_next()
        image2 = None
        if self.double_page:
            image2 = self._open_next()
            # in order to set index as first page
            self.archive.prev()
        self.image.display(image, image2, self.right2left)

    def _open_prev(self):
        file_path, data = self.archive.prev()
        if file_path == "":
            logger.debug("file_path is empty")
            return None
        return self.open_file(file_path, data)

    def prev_page(self, event):
        logger.debug("called")
        image = self._open_prev()
        image2 = None
        if self.double_page:
            image2 = self._open_prev()
        self.image.display(image, image2, not self.right2left)

    def quit(self, event):
        self.destroy()

    def open(self, file_path):
        self.archive = self.open_archive(file_path)
        file_path, data = self.archive.current()
        image = self.open_file(file_path, data)
        self.image.display(image)

    def open_archive(self, file_path):
        suffix = Path(file_path).suffix.lower()
        if suffix == ".zip":
            return ZipArchive(file_path)
        elif suffix == ".rar":
            return RarArchive(file_path)
        elif suffix == ".7z":
            return SevenZipArchive(file_path)
        else:
            return DirectoryArchive(file_path)

    def open_file(self, file_path, data=None):
        file_path = Path(file_path)
        logger.debug(file_path)
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
            return self.open_image(file_path, data)
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
            return None

    def _open_by_path_or_data(self, path, data=None):
        if data is None:
            return Image.open(path)
        else:
            return Image.open(data)

    # can be animation
    def open_png_image(self, png_path, data=None):
        image = self._open_by_path_or_data(png_path, data)
        return image

    def open_image(self, image_path, data=None):
        image = self._open_by_path_or_data(image_path, data)
        if image is None:
            messagebox.showwarning("Image open failed.", "Image open failed.")
            return None

        # Force single page mode when animation
        if hasattr(image, "is_animated") and image.is_animated:
            self.double_page = False
        return image


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
