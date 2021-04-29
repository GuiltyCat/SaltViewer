import argparse
import csv
import io
import logging
import time
import tkinter as tk
import tkinter.messagebox as messagebox
import tkinter.ttk as ttk
import zipfile
from pathlib import Path

import cairosvg
import pdf2image
import py7zr
import rarfile
from natsort import natsorted
from PIL import Image, ImageTk
from send2trash import send2trash

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

ch = logging.StreamHandler()
formatter = logging.Formatter(
    # "%(asctime)s:%(name)s:%(funcName)s:%(lineno)d:%(levelname)s:%(message)s"
    # "%(funcName)s:%(lineno)d:%(levelname)s:%(message)s"
    "%(asctime)s:%(funcName)s:%(lineno)d:%(message)s"
)
ch.setFormatter(formatter)
logger.addHandler(ch)


class ArchiveBase:
    def __init__(self):
        self.file_path = None
        self.data = None
        self.file_list = []
        self.i = 0

    def open(self, file_path, data=None):
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

    def head(self):
        self.i = 0
        return self[self.i]

    def tail(self):
        self.i = len(self) - 1
        return self[self.i]

    def next(self, c=1):
        c = max(1, c)
        self.i = min(self.i + c, len(self) - 1)
        return self[self.i]

    def prev(self, c=1):
        c = max(1, c)
        self.i = max(self.i - c, 0)
        return self[self.i]

    def current(self):
        return self[self.i]

    def trash(self):
        logger.debug(self.file_path)
        if self.file_path is not None:
            send2trash(str(self.file_path))


class DirectoryArchive(ArchiveBase):
    def __init__(self, file_path, data=None):
        super().__init__()
        self.open(file_path, data)

    def open(self, file_path, data=None):
        # you cannot path data, ignored
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


class ZipArchive(ArchiveBase):
    def __init__(self, file_path, data=None):
        super().__init__()
        self.open(file_path, data)

    def open(self, file_path, data=None):
        logger.debug("called")
        self.file_path = file_path
        self.data = data
        self.file_list = []

        logger.debug("to byte")
        fp = self.file_path if data is None else io.BytesIO(self.data)

        logger.debug("zip open")
        with zipfile.ZipFile(fp) as f:
            self.file_list = natsorted(f.namelist())

        logger.debug("to list")
        self.file_list = [f for f in self.file_list if f[-1] != "/"]
        logger.debug(self.file_list)
        logger.debug("return")

    def __getitem__(self, i):
        logger.debug("__getitem__")
        self.i = i
        file_name = ""
        file_byte = None

        logger.debug("to byte")
        fp = self.file_path if self.data is None else io.BytesIO(self.data)

        logger.debug("open zip")
        if 0 <= i < len(self):
            with zipfile.ZipFile(fp) as f:
                file_name = Path(self.file_list[i])
                file_byte = f.read(self.file_list[i])

        logger.debug(f"self.i={self.i}")
        logger.debug(self.file_list[i])
        logger.debug(file_name)
        logger.debug("return")
        return file_name, io.BytesIO(file_byte)


class RarArchive(ArchiveBase):
    def __init__(self, file_path, data=None):
        super().__init__()
        self.open(file_path, data)

    def open(self, file_path, data=None):
        logger.debug("called")
        self.file_path = file_path
        self.data = data
        self.file_list = []

        logger.debug("to byte")
        fp = self.file_path if data is None else io.BytesIO(self.data)

        logger.debug("open rar")
        with rarfile.RarFile(fp) as f:
            self.file_list = natsorted(f.namelist())

        logger.debug("open rar")
        self.file_list = [f for f in self.file_list if f[-1] != "/"]
        logger.debug(self.file_list)

    def __getitem__(self, i):
        logger.debug("__getitem__")
        self.i = i
        file_name = ""
        file_byte = None
        logger.debug("to byte")
        fp = self.file_path if self.data is None else io.BytesIO(self.data)
        logger.debug("read file")
        if 0 <= i < len(self):
            with rarfile.RarFile(fp) as f:
                file_name = Path(self.file_list[i])
                file_byte = f.read(self.file_list[i])

        logger.debug(f"self.i={self.i}")
        logger.debug(self.file_list[i])
        logger.debug(file_name)
        logger.debug("return")
        return file_name, io.BytesIO(file_byte)


class SevenZipArchive(ArchiveBase):
    def __init__(self, file_path, data=None):
        super().__init__()
        self.open(file_path, data)

    def open(self, file_path, data=None):
        logger.debug("called")
        self.file_path = file_path
        self.data = None
        self.file_list = []
        logger.debug("to bytes")
        fp = self.file_path if self.data is None else io.BytesIO(self.data)
        logger.debug("open 7z")
        with py7zr.SevenZipFile(fp, mode="r") as f:
            self.file_list = natsorted(f.getnames())

        self.file_list = [f for f in self.file_list if f[-1] != "/"]
        logger.debug(self.file_list)
        logger.debug("return")

    def __getitem__(self, i):
        logger.debug("__getitem__")
        self.i = i
        file_name = ""
        file_byte = None
        logger.debug("to byte")
        fp = self.file_path if self.data is None else io.BytesIO(self.data)
        logger.debug("open 7z")
        if 0 <= i < len(self):
            logger.debug("with open")
            with py7zr.SevenZipFile(fp) as f:
                file_name = Path(self.file_list[i])
                logger.debug("read")
                data = f.read([self.file_list[i]])
                logger.debug("name, data")
                for name, data in data.items():
                    logger.debug("extract data")
                    file_byte = data
            logger.debug("read end")

        logger.debug(f"file_bype = {file_byte}")
        logger.debug(f"self.i={self.i}")
        logger.debug(self.file_list[i])
        logger.debug(file_name)
        logger.debug("return")
        return file_name, file_byte


class PdfArchive(ArchiveBase):
    def __init__(self, file_path, data=None):
        super().__init__()
        self.images = []
        self.open(file_path, data)

    def open(self, file_path, data=None):

        self.file_path = file_path
        if data is None:
            self.images = pdf2image.convert_from_path(file_path)
        else:
            self.images = pdf2image.convert_from_bytes(data.read())

        self.file_list = [Path(str(i) + ".png") for i in range(len(self.images))]

    def __getitem__(self, i):
        logger.debug("getitem")
        self.i = i
        file_name = self.file_list[self.i]
        image = self.images[self.i]
        print(type(image))
        logger.debug("io.BytesIO")
        # image_bytes = io.BytesIO()
        logger.debug("image.save")
        # image.save(image_bytes, format="PNG")
        logger.debug("return")
        return file_name, image


class ImageFrame(tk.Canvas):
    algorithm = {
        "Nearest": Image.NEAREST,
        "Box": Image.BOX,
        "Bilinear": Image.BILINEAR,
        "Hamming": Image.HAMMING,
        "Bicubic": Image.BICUBIC,
        "Lanczos": Image.LANCZOS,
    }

    def __init__(self, master):
        super().__init__(master, highlightthickness=0, bg="black")
        self.master = master
        self.item = None

        self.image = None
        self.image2 = None
        self.tk_image = None

        self.master.bind(
            "<Configure>", lambda *kw: self.display(self.image, self.image2)
        )

        self.duration = 0

        # self.stop = True
        self.after_id = None

        self.fit_width = True
        self.fit_height = True
        self.title = ""

        self.up_scale = Image.NEAREST
        self.down_scale = Image.NEAREST

    def select_up_scale_algorithm(self, up):
        algo = self.algorithm.get(up)
        if algo is not None:
            self.up_scale = algo
        else:
            logger.warning("UpScale = {up} is not supported.")

    def select_down_scale_algorithm(self, down):
        algo = self.algorithm.get(down)
        if algo is not None:
            self.down_scale = algo
        else:
            logger.warning("DownScale = {down} is not supported.")

    def resize_image(self, image, div=1):
        if image is None:
            return None
        if not self.fit_width and not self.fit_height:
            return image
        elif self.fit_width and self.fit_height:
            return self.fit_in_frame(image, div)
        elif self.fit_width and not self.fit_height:
            return self.fit_in_frame_width(image, div)
        elif not self.fit_width and self.fit_height:
            return self.fit_in_frame_height(image, div)
        else:
            logger.debug("Not supported.")

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
        if self.after_id is not None:
            self.after_cancel(self.after_id)
        self.after_id
        self.image = image
        self.image2 = image2
        if getattr(image, "is_animated", False):
            self.stop = False
            self.start = time.perf_counter()
            duration = image.info["duration"]
            logger.debug(f"duration = {duration}")
            return self.display_animation(image, 0)

        if image is not None:
            div = 1 if image2 is None else 2
            image = self.resize_image(image, div)
            image2 = self.resize_image(image2, div)

            new_image = self.merge_image(image, image2, right2left)
            del self.tk_image
            self.tk_image = ImageTk.PhotoImage(image=new_image)
            del new_image
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
        start = time.perf_counter()
        self.fps = 1.0 / (start - self.start)
        self.start = start
        logger.debug("start")
        if self.stop:
            self.stop = False
            return

        logger.debug(f"counter={counter}")
        counter %= image.n_frames
        image.seek(counter)

        logger.debug("resize")
        new_image = self.resize_image(image)
        logger.debug("to tk photoimage")
        del self.tk_image
        self.tk_image = ImageTk.PhotoImage(image=new_image)
        del new_image
        logger.debug("delete item")
        if self.item is not None:
            self.delete(self.item)
        logger.debug("get width and height")
        width = self.tk_image.width()
        height = self.tk_image.height()

        logger.debug("change config")
        self.configure(width=width, height=height)
        sx, sy = self.center_shift(width, height)
        logger.debug("create_image")
        self.item = self.create_image(sx, sy, image=self.tk_image, anchor="nw")

        # automatically adjust duration
        duration = image.info["duration"]
        self.master.master.title(
            f"{self.title}:{counter}/{image.n_frames}:"
            + f"fps={self.fps:.2f}/{1/(duration/1000):.2f}"
        )
        logger.debug("time count")
        end = time.perf_counter()
        self.duration = int(duration - (end - start) * 1000)
        logger.debug(f"self.duration = {self.duration} or 0")
        # if self.duration == 0, image will not be updated.
        self.duration = max(1, self.duration)

        logger.debug("call after")
        self.after_id = self.after(
            self.duration, self.display_animation, image, counter + 1
        )
        logger.debug("end")

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
        if times == 1:
            return image
        size = (int(image.width * times), int(image.height * times))

        algo = self.up_scale if times > 1 else self.down_scale
        return self.resize(image, size, algo)

    def resize(self, image, size, algorithm):
        if size[0] == 0 or size[1] == 0:
            size = (1, 1)
        return image.resize(size, algorithm)

    def fit_in_frame_width(self, image, div):
        width = self.width() / div
        height = self.height()
        logger.debug(f"{width}, {height}")
        times = width / image.width
        if times == 1:
            return image
        size = (int(image.width * times), int(image.height * times))
        algo = self.up_scale if times > 1 else self.down_scale
        return self.resize(image, size, algo)

    def fit_in_frame_height(self, image, div):
        width = self.width() / div
        height = self.height()
        logger.debug(f"{width}, {height}")
        times = height / image.height
        if times == 1:
            return image
        size = (int(image.width * times), int(image.height * times))
        algo = self.up_scale if times > 1 else self.down_scale
        return self.resize(image, size, algo)


class Config:
    default_config = """\
[Setting]

# None, Width, Height or Both
FitMode = Both

# true or false.
DoublePage = False

# right2left or left2right
PageOrder  = right2left

# Resize algorithms
# | Filter   | Downscaling quality | Upscaling quality | Performance |
# | Nearest  | -                   | -                 | *****       |
# | Box      | *                   | -                 | ****        |
# | Bilinear | *                   | *                 | ***         |
# | Hamming  | **                  | -                 | ***         |
# | Bicubic  | ***                 | ***               | **          |
# | Lanczos  | ****                | ****              | *           |

UpScale     = Lanczos
DownScale   = Lanczos

[Keymap]

DoublePage  = d
TrashFile   = Delete

# You can use repetition for NextPage and PrevPage.
# For example, 2h means goto next 2 page, type 100h go to next 100 page.
# If you want to reset number, type <Esc>, <Ctrl+[> or simply <[>
NextPage    = h
PrevPage    = l

NextArchive = j
PrevArchive = k

FitNone     = N
FitWidth    = W
FitHeight   = H
FitBoth     = B

PageOrder   = o

Quit        = q
Head        = g
Tail        = G
"""

    def __init__(self):
        self.keymap = {}
        self.setting = {}
        pass

    def open(self, file_path):
        file_path = Path(file_path)
        fp = file_path
        if file_path.exists():
            with open(fp, mode="r", newline="") as f:
                self._load(f)
        else:
            with io.StringIO(self.default_config) as f:
                self._load(f)

    def _load(self, f):

        config = None
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

            if config is None:
                continue

            config[row[0].strip()] = row[1].strip()

    def write_default_config(self, file_path):
        if file_path.exists():
            print(f"{file_path} already exists. Not overwerite.")
            return

        with open(file_path, "w") as f:
            f.write(self.default_config)


class SaltViewer(tk.Tk):
    def __init__(self, config_path):
        super().__init__()

        self.title("SaltViewer")
        icon = self.open_svg(None, io.StringIO(Icon.svg))
        icon = icon.resize((100, 100))
        self.icon = ImageTk.PhotoImage(image=icon)
        self.iconphoto(False, self.icon)

        self.binding = {
            "DoublePage": self.toggle_page_mode,
            "TrashFile": self.trash,
            "NextPage": self.next_page,
            "PrevPage": self.prev_page,
            "NextArchive": self.next_archive,
            "PrevArchive": self.prev_archive,
            "PageOrder": self.toggle_order,
            "FitWidth": self.fit_width,
            "FitHeight": self.fit_height,
            "FitBoth": self.fit_both,
            "FitNone": self.fit_none,
            "Quit": self.quit,
            "Head": self.head,
            "Tail": self.tail,
        }

        self.style = ttk.Style()
        self.construct_gui()

        self.double_page = False
        self.right2left = True

        self.config = Config()
        self.config.open(config_path)

        self.num = 0

        self.load_config()

    def fit_width(self, event):
        self._change_image_fit_mode("Width")
        self.current_page()

    def fit_height(self, event):
        self._change_image_fit_mode("Height")
        self.current_page()

    def fit_both(self, event):
        self._change_image_fit_mode("Both")
        self.current_page()

    def fit_none(self, event):
        self._change_image_fit_mode("None")
        self.current_page()

    def load_config(self):
        for name, key in self.config.keymap.items():
            func = self.binding.get(name)
            if name is None:
                print(f"Such operation is not supported: {name}")
            elif len(key) == 1:
                self.bind(f"<KeyPress-{key}>", func)
            elif key == "Delete":
                self.bind("<Delete>", func)
            else:
                print(f"Not supported.: {name} = {key}")

        for name, key in self.config.setting.items():
            if name == "FitMode":
                self._change_image_fit_mode(key)
            elif name == "DoublePage":
                self.double_page = True if key == "true" else False
            elif name == "PageOrder":
                self.right2left = True if key == "right2left" else False
            elif name == "UpScale":
                self.image.select_up_scale_algorithm(key)
            elif name == "DownScale":
                self.image.select_down_scale_algorithm(key)

        self.bind("<Escape>", self.reset_num)
        self.bind("[", self.reset_num)
        for i in range(10):
            self.bind(f"<KeyPress-{i}>", self.num_key)

    def num_key(self, event):
        self.num *= 10
        self.num += int(event.char)
        logger.debug(f"num = {self.num}")

    def reset_num(self, event):
        self.num = 0
        logger.debug(f"num = {self.num}")

    def _change_image_fit_mode(self, key):
        if key == "Both":
            self.image.fit_width = True
            self.image.fit_height = True
        elif key == "Width":
            self.image.fit_width = True
            self.image.fit_height = False
        elif key == "Height":
            self.image.fit_width = False
            self.image.fit_height = True
        elif key == "None":
            self.image.fit_width = False
            self.image.fit_height = False

    def head(self, event):
        self.archive.head()
        self.current_page()

    def tail(self, event):
        self.archive.tail()
        self.current_page()

    def next_archive(self, event):
        file_path = self.archive.file_path
        archive = DirectoryArchive(file_path)
        self.open(archive.next()[0])

    def prev_archive(self, event):
        file_path = self.archive.file_path
        archive = DirectoryArchive(file_path)
        self.open(archive.prev()[0])

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

    def trash(self, event):
        if messagebox.askokcancel("Trash file?", "Trash file?"):
            file_path = self.archive.file_path
            print(f"Trash {file_path}")
            archive = DirectoryArchive(file_path)
            if len(archive) == 1:
                print("Archive is empty")
                self.archive.trash()
                self.quit(None)
                return
            next_file_path = archive.next()[0]
            if next_file_path == file_path:
                next_file_path = archive.prev()[0]
            self.archive.trash()
            self.open(next_file_path)
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

    def _open_next(self, c=1):
        logger.debug("called")
        file_path, data = self.archive.next(c)
        if file_path == "":
            logger.debug("file_path is empty")
            return None
        return self.open_file(file_path, data)

    def next_page(self, event):
        logger.debug("called")

        # back to the second page then next
        if self.double_page:
            logger.debug("double_page")
            self.archive.next()
        image = self._open_next(self.num)
        self.num = 0
        image2 = None
        if self.double_page:
            image2 = self._open_next()
            # in order to set index as first page
            self.archive.prev()
        self.image.display(image, image2, self.right2left)

    def _open_prev(self, c=1):
        file_path, data = self.archive.prev(c)
        if file_path == "":
            logger.debug("file_path is empty")
            return None
        return self.open_file(file_path, data)

    def prev_page(self, event):
        logger.debug("called")
        image = self._open_prev(self.num)
        self.num = 0
        image2 = None
        if self.double_page:
            image2 = self._open_prev()
        self.image.display(image, image2, not self.right2left)

    def quit(self, event):
        self.destroy()

    def open(self, file_path, data=None):
        self.archive = self.open_archive(file_path, data)
        file_path, data = self.archive.current()
        image = self.open_file(file_path, data)
        self.image.display(image)

    def open_archive(self, file_path, data=None):
        logger.debug("called")
        suffix = Path(file_path).suffix.lower()
        if suffix == ".zip":
            logger.debug("zip")
            return ZipArchive(file_path, data)
        elif suffix == ".rar":
            logger.debug("rar")
            return RarArchive(file_path, data)
        elif suffix == ".7z":
            logger.debug("7z")
            return SevenZipArchive(file_path, data)
        elif suffix == ".pdf":
            logger.debug("pdf")
            return PdfArchive(file_path, data)
        else:
            logger.debug("directory")
            return DirectoryArchive(file_path, data)

    def open_file(self, file_path, data=None):
        logger.debug("called")

        logger.debug("set title")
        title = f"{file_path}:({self.archive.i+1}/{len(self.archive)})"
        if self.archive.file_path.stem != str(file_path.parent):
            title = f"{self.archive.file_path}/" + title

        self.title(title)
        self.image.title = title

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
            ".png",
            ".ppm",
            ".sgi",
            ".spider",
            ".tga",
            ".tiff",
            ".webv",
            ".xbm",
        ]:
            return self.open_image(file_path, data)
        elif suffix in [".tiff"]:
            # can have multi images
            pass
        elif suffix in [".svg"]:
            return self.open_svg(file_path, data)
        elif suffix in [".zip", ".rar", ".7z", ".pdf"]:
            self.open(file_path, data)
        else:
            logger.debug(f"Not supported.:{suffix}")
            return None

    def _open_by_path_or_data(self, path, data=None):

        if data is None:
            return Image.open(path)

        if isinstance(data, io.BytesIO):
            return Image.open(data)

        # if PIL.Image
        return data

    def open_image(self, image_path, data=None):
        logger.debug("called")
        image = self._open_by_path_or_data(image_path, data)
        if image is None:
            messagebox.showwarning("Image open failed.", "Image open failed.")
            return None

        # Force single page mode when animation
        if getattr(image, "is_animated", False):
            self.double_page = False

        logger.debug("return")
        return image

    def open_svg(self, image_path, data=None):
        if data is None:
            svg = cairosvg.svg2png(url=str(image_path))
        else:
            svg = cairosvg.svg2png(file_obj=data)
        svg = io.BytesIO(svg)
        return Image.open(svg)


class Icon:
    svg = """\
<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   xmlns:osb="http://www.openswatchbook.org/uri/2009/osb"
   xmlns:dc="http://purl.org/dc/elements/1.1/"
   xmlns:cc="http://creativecommons.org/ns#"
   xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
   xmlns:svg="http://www.w3.org/2000/svg"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:xlink="http://www.w3.org/1999/xlink"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   width="1024"
   height="1024"
   viewBox="0 0 270.93333 270.93333"
   version="1.1"
   id="svg8"
   inkscape:version="1.0.2 (e86c870879, 2021-01-15, custom)"
   sodipodi:docname="icon.svg"
   inkscape:export-filename="/home/miyamoto/bitmap.png"
   inkscape:export-xdpi="96"
   inkscape:export-ydpi="96">
  <defs
     id="defs2">
    <linearGradient
       inkscape:collect="always"
       id="linearGradient1708">
      <stop
         style="stop-color:#ffffff;stop-opacity:1;"
         offset="0"
         id="stop1704" />
      <stop
         style="stop-color:#ffffff;stop-opacity:0;"
         offset="1"
         id="stop1706" />
    </linearGradient>
    <linearGradient
       id="linearGradient1683"
       osb:paint="solid">
      <stop
         style="stop-color:#000000;stop-opacity:1;"
         offset="0"
         id="stop1681" />
    </linearGradient>
    <marker
       style="overflow:visible"
       id="SquareL"
       refX="0.0"
       refY="0.0"
       orient="auto"
       inkscape:stockid="SquareL"
       inkscape:isstock="true">
      <path
         transform="scale(0.8)"
         style="fill-rule:evenodd;stroke:#000000;stroke-width:1.0pt"
         d="M -5.0,-5.0 L -5.0,5.0 L 5.0,5.0 L 5.0,-5.0 L -5.0,-5.0 z "
         id="path1377" />
    </marker>
    <linearGradient
       id="linearGradient1087"
       osb:paint="solid">
      <stop
         style="stop-color:#000000;stop-opacity:1;"
         offset="0"
         id="stop1085" />
    </linearGradient>
    <inkscape:perspective
       sodipodi:type="inkscape:persp3d"
       inkscape:vp_x="-53.579323 : -6.5615746e-15 : 0"
       inkscape:vp_y="-1.0338376e-13 : 562.79499 : 0"
       inkscape:vp_z="264.08259 : 106.73382 : 0"
       inkscape:persp3d-origin="94.9365 : 54.502409 : 1"
       id="perspective1055" />
    <linearGradient
       id="linearGradient957"
       osb:paint="solid">
      <stop
         style="stop-color:#ffffff;stop-opacity:1;"
         offset="0"
         id="stop955" />
    </linearGradient>
    <inkscape:perspective
       sodipodi:type="inkscape:persp3d"
       inkscape:vp_x="-32.52275 : -3.9828882e-15 : 0"
       inkscape:vp_y="-6.2754137e-14 : 341.6176 : 0"
       inkscape:vp_z="160.29863 : 64.787629 : 0"
       inkscape:persp3d-origin="49.630612 : 152.78217 : 1"
       id="perspective1055-3" />
    <inkscape:perspective
       sodipodi:type="inkscape:persp3d"
       inkscape:vp_x="-8.6049776 : -1.0538058e-15 : 0"
       inkscape:vp_y="-1.6603699e-14 : 90.386323 : 0"
       inkscape:vp_z="42.412346 : 17.141727 : 0"
       inkscape:persp3d-origin="79.669861 : 184.05643 : 1"
       id="perspective1055-3-0" />
    <linearGradient
       inkscape:collect="always"
       xlink:href="#linearGradient1708"
       id="linearGradient1710"
       x1="100.0077"
       y1="42.333334"
       x2="141.96263"
       y2="41.603447"
       gradientUnits="userSpaceOnUse"
       gradientTransform="matrix(0.90625002,0,0,0.90625002,20.835943,7.2760412)" />
  </defs>
  <sodipodi:namedview
     id="base"
     pagecolor="#ffffff"
     bordercolor="#666666"
     borderopacity="1.0"
     inkscape:pageopacity="0.0"
     inkscape:pageshadow="2"
     inkscape:zoom="63.356768"
     inkscape:cx="905.82998"
     inkscape:cy="209.77284"
     inkscape:document-units="mm"
     inkscape:current-layer="layer1"
     inkscape:document-rotation="0"
     showgrid="true"
     units="px"
     width="1024px"
     inkscape:window-width="1784"
     inkscape:window-height="1387"
     inkscape:window-x="768"
     inkscape:window-y="49"
     inkscape:window-maximized="0">
    <inkscape:grid
       type="xygrid"
       id="grid1004" />
  </sodipodi:namedview>
  <metadata
     id="metadata5">
    <rdf:RDF>
      <cc:Work
         rdf:about="">
        <dc:format>image/svg+xml</dc:format>
        <dc:type
           rdf:resource="http://purl.org/dc/dcmitype/StillImage" />
        <dc:title />
      </cc:Work>
    </rdf:RDF>
  </metadata>
  <g
     inkscape:label="レイヤー 1"
     inkscape:groupmode="layer"
     id="layer1">
    <rect
       style="fill:#000000;fill-opacity:1;fill-rule:evenodd;stroke-width:7.937;stroke-linecap:square;stroke-miterlimit:4.8;stroke-dasharray:none"
       id="rect971-3"
       width="5.0270834"
       height="1.8520833"
       x="238.91875"
       y="57.414585" />
    <circle
       style="fill:#000000;fill-opacity:1;stroke-width:0.336799;image-rendering:auto"
       id="path943"
       cx="135.5"
       cy="135.5"
       r="135.5" />
    <g
       id="g1651"
       transform="translate(-10.583334,-5.8208324)">
      <a
         id="a981"
         style="stroke-width:7.9375;stroke-miterlimit:4;stroke-dasharray:none"
         transform="translate(4.2333334,-5.2867415)">
        <rect
           style="fill:none;fill-opacity:1;fill-rule:evenodd;stroke:#fffffe;stroke-width:7.9375;stroke-miterlimit:4;stroke-dasharray:none;stroke-opacity:1"
           id="rect118"
           width="121.25342"
           height="121.25342"
           x="43.580471"
           y="109.85602" />
      </a>
      <rect
         style="fill:none;fill-opacity:1;fill-rule:evenodd;stroke:#fffffe;stroke-width:7.937;stroke-miterlimit:4;stroke-dasharray:none;stroke-opacity:1"
         id="rect118-3"
         width="81.530472"
         height="81.530472"
         x="67.675278"
         y="124.43076" />
      <rect
         style="fill:none;fill-opacity:1;fill-rule:evenodd;stroke:#fffffe;stroke-width:7.93749;stroke-miterlimit:4;stroke-dasharray:none;stroke-opacity:1"
         id="rect118-3-6"
         width="35.346275"
         height="35.346275"
         x="90.76738"
         y="147.52287" />
    </g>
    <g
       id="g1645"
       transform="matrix(0.95813112,0,-0.59461959,0.28653765,56.19471,64.999159)"
       style="fill:none;fill-opacity:1;stroke:#fffffe;stroke-width:14.6121;stroke-miterlimit:4.8;stroke-dasharray:none;stroke-opacity:1">
      <a
         id="a981-1"
         style="fill:none;fill-opacity:1;stroke:#fffffe;stroke-width:14.6121;stroke-miterlimit:4.8;stroke-dasharray:none;stroke-opacity:1"
         transform="translate(4.2913838,-134.48001)">
        <rect
           style="fill:none;fill-opacity:1;fill-rule:evenodd;stroke:#fffffe;stroke-width:14.6121;stroke-miterlimit:4.8;stroke-dasharray:none;stroke-opacity:1"
           id="rect118-8"
           width="121.25342"
           height="121.25342"
           x="43.580471"
           y="109.85602" />
      </a>
      <rect
         style="fill:none;fill-opacity:1;fill-rule:evenodd;stroke:#fffffe;stroke-width:14.6121;stroke-miterlimit:4.8;stroke-dasharray:none;stroke-opacity:1"
         id="rect118-3-7"
         width="81.530472"
         height="81.530472"
         x="67.73333"
         y="-4.7624998"
         ry="0" />
      <rect
         style="fill:none;fill-opacity:1;fill-rule:evenodd;stroke:#fffffe;stroke-width:14.6121;stroke-linecap:square;stroke-miterlimit:4.8;stroke-dasharray:none;stroke-opacity:1"
         id="rect118-3-6-9"
         width="35.346275"
         height="35.346275"
         x="90.825432"
         y="18.329603"
         rx="0"
         ry="0" />
    </g>
    <g
       id="g1657"
       transform="matrix(0.61024286,-0.30392859,0,0.98675564,57.544339,48.452764)"
       style="stroke-width:1.28011">
      <a
         id="a981-1-2"
         style="stroke-width:10.1609;stroke-miterlimit:4;stroke-dasharray:none"
         transform="translate(133.40803,-5.3633407)">
        <rect
           style="fill:none;fill-opacity:1;fill-rule:evenodd;stroke:#fffffe;stroke-width:10.1609;stroke-miterlimit:4;stroke-dasharray:none;stroke-opacity:1"
           id="rect118-8-0"
           width="121.25342"
           height="121.25342"
           x="43.580471"
           y="109.85602" />
      </a>
      <rect
         style="fill:none;fill-opacity:1;fill-rule:evenodd;stroke:#fffffe;stroke-width:10.1609;stroke-miterlimit:4;stroke-dasharray:none;stroke-opacity:1"
         id="rect118-3-7-2"
         width="81.530472"
         height="81.530472"
         x="196.85002"
         y="124.35419" />
      <rect
         style="fill:none;fill-opacity:1;fill-rule:evenodd;stroke:#fffffe;stroke-width:10.1609;stroke-miterlimit:4;stroke-dasharray:none;stroke-opacity:1"
         id="rect118-3-6-9-3"
         width="35.346275"
         height="35.346275"
         x="219.94212"
         y="147.44611" />
    </g>
    <rect
       style="fill:none;fill-opacity:1;fill-rule:evenodd;stroke-width:10;stroke-linecap:square;stroke-miterlimit:4.8;stroke-dasharray:none"
       id="rect969"
       width="238.125"
       height="74.083336"
       x="-42.333332"
       y="26.458332" />
    <rect
       style="fill:#000000;fill-opacity:1;fill-rule:evenodd;stroke-width:7.05184;stroke-linecap:square;stroke-miterlimit:4.8;stroke-dasharray:none"
       id="rect971"
       width="3.968334"
       height="1.8520833"
       x="238.91875"
       y="54" />
    <rect
       style="fill:#000000;fill-opacity:1;fill-rule:evenodd;stroke-width:8.20116;stroke-linecap:square;stroke-miterlimit:4.8;stroke-dasharray:none"
       id="rect993"
       width="1.9774171"
       height="2.3812499"
       x="242.645"
       y="55.827084" />
  </g>
</svg>
"""

    def __init__(self):
        pass

    def save_icon(self, file_path):
        if file_path.exists():
            print(f"{file_path} already exists. Not overwerite.")
            return

        with open(file_path, "w") as f:
            f.write(self.svg)


def main():

    default_config_path = str(Path.home() / ".svrc")

    parser = argparse.ArgumentParser(description="SaltViewer")
    parser.add_argument(
        "path", help="image file or archive file", type=str, default=None
    )
    parser.add_argument(
        "--config",
        help=f"configuration file path. default is {default_config_path}",
        type=str,
        default=default_config_path,
    )
    parser.add_argument("--icon", help="write icon to path", action="store_true")
    parser.add_argument(
        "--default_config",
        help="write default configuration to path. salt-viewer --default_config >~/.svrc",
        action="store_true",
    )
    parser.add_argument("--debug", help="debug mode", action="store_true")

    args = parser.parse_args()

    args.path = Path(args.path)

    if args.icon:
        Icon().save_icon(args.path)
        return

    if args.default_config:
        Config.write_default_config(args.path)

    if args.debug:
        logger.setLevel(logging.DEBUG)

    sv = SaltViewer(args.config)
    sv.open(Path(args.path))
    sv.mainloop()


if __name__ == "__main__":
    main()
