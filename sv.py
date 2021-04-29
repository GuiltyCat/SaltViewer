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

    def trash(self):
        super().trash()
        self.next()
        file_path = self.file_list[self.i]
        self.open(file_path)


class ZipArchive(ArchiveBase):
    def __init__(self, file_path, data=None):
        super().__init__()
        self.open(file_path, data)

    def open(self, file_path, data=None):
        self.file_path = file_path
        self.data = data
        self.file_list = []

        fp = self.file_path if data is None else io.BytesIO(self.data)

        with zipfile.ZipFile(fp) as f:
            self.file_list = natsorted(f.namelist())

        self.file_list = [f for f in self.file_list if f[-1] != "/"]
        logger.debug(self.file_list)

    def __getitem__(self, i):
        self.i = i
        file_name = ""
        file_byte = None

        fp = self.file_path if self.data is None else io.BytesIO(self.data)

        if 0 <= i < len(self):
            with zipfile.ZipFile(fp) as f:
                file_name = Path(self.file_list[i])
                file_byte = f.read(self.file_list[i])

        logger.debug(f"self.i={self.i}")
        logger.debug(self.file_list[i])
        logger.debug(file_name)
        return file_name, io.BytesIO(file_byte)


class RarArchive(ArchiveBase):
    def __init__(self, file_path, data=None):
        super().__init__()
        self.open(file_path, data)

    def open(self, file_path, data=None):
        self.file_path = file_path
        self.data = data
        self.file_list = []

        fp = self.file_path if data is None else io.BytesIO(self.data)

        with rarfile.RarFile(fp) as f:
            self.file_list = natsorted(f.namelist())

        self.file_list = [f for f in self.file_list if f[-1] != "/"]
        logger.debug(self.file_list)

    def __getitem__(self, i):
        self.i = i
        file_name = ""
        file_byte = None
        fp = self.file_path if self.data is None else io.BytesIO(self.data)
        if 0 <= i < len(self):
            with rarfile.RarFile(fp) as f:
                file_name = Path(self.file_list[i])
                file_byte = f.read(self.file_list[i])

        logger.debug(f"self.i={self.i}")
        logger.debug(self.file_list[i])
        logger.debug(file_name)
        return file_name, io.BytesIO(file_byte)


class SevenZipArchive(ArchiveBase):
    def __init__(self, file_path, data=None):
        super().__init__()
        self.open(file_path, data)

    def open(self, file_path, data=None):
        self.file_path = file_path
        self.data = None
        self.file_list = []
        fp = self.file_path if self.data is None else io.BytesIO(self.data)
        with py7zr.SevenZipFile(fp) as f:
            self.file_list = natsorted(f.getnames())

        self.file_list = [f for f in self.file_list if f[-1] != "/"]
        logger.debug(self.file_list)

    def __getitem__(self, i):
        self.i = i
        file_name = ""
        file_byte = None
        fp = self.file_path if self.data is None else io.BytesIO(self.data)
        if 0 <= i < len(self):
            with py7zr.SevenZipFile(fp) as f:
                file_name = Path(self.file_list[i])
                for name, data in f.read([self.file_list[i]]).items():
                    file_byte = data

        logger.debug(f"file_bype = {file_byte}")
        logger.debug(f"self.i={self.i}")
        logger.debug(self.file_list[i])
        logger.debug(file_name)
        return file_name, file_byte


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


class SaltViewer(tk.Tk):
    def __init__(self, config_path):
        super().__init__()

        self.title("SaltViewer")

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
        if messagebox.askokcancel("Delete file?", "Delete file?"):
            print("Deleted.")
            self.current_page()
            self.archive.trash()
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
        file_path, data = self.archive.next(c)
        if file_path == "":
            logger.debug("file_path is empty")
            return None
        return self.open_file(file_path, data)

    def next_page(self, event):
        logger.debug("called")

        # back to the second page then next
        if self.double_page:
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
        suffix = Path(file_path).suffix.lower()
        if suffix == ".zip":
            return ZipArchive(file_path, data)
        elif suffix == ".rar":
            return RarArchive(file_path, data)
        elif suffix == ".7z":
            return SevenZipArchive(file_path, data)
        else:
            return DirectoryArchive(file_path, data)

    def open_file(self, file_path, data=None):

        title = f"{file_path}:({self.archive.i+1}/{len(self.archive)})"
        if self.archive.file_path != file_path:
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
        elif suffix in [".zip", ".rar", ".7z"]:
            self.open(file_path, data)
        else:
            logger.debug(f"Not supported.:{suffix}")
            return None

    def _open_by_path_or_data(self, path, data=None):
        if data is None:
            return Image.open(path)
        else:
            return Image.open(data)

    def open_image(self, image_path, data=None):
        image = self._open_by_path_or_data(image_path, data)
        if image is None:
            messagebox.showwarning("Image open failed.", "Image open failed.")
            return None

        # Force single page mode when animation
        if getattr(image, "is_animated", False):
            self.double_page = False
        return image


def main():

    parser = argparse.ArgumentParser(description="SaltViewer")
    parser.add_argument(
        "path", help="image file or archive file", type=str, default=None
    )
    parser.add_argument(
        "--config", help="configuration file path", type=str, default=".svrc"
    )
    parser.add_argument("--debug", help="debug mode", action="store_true")

    args = parser.parse_args()

    if args.debug:
        logger.setLevel(logging.DEBUG)

    sv = SaltViewer(args.config)
    sv.open(Path(args.path))
    sv.mainloop()


if __name__ == "__main__":
    main()
