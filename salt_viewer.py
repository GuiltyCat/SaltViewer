import argparse
import csv
import io
import logging
import random
import shutil
import threading
import time
import tkinter as tk
import tkinter.filedialog as filedialog
import tkinter.messagebox as messagebox
import tkinter.ttk as ttk
from pathlib import Path

import natsort as ns
import pillow_avif
from PIL import Image, ImageTk

logger = logging.getLogger(__name__)
# logger.setLevel(logging.WARNING)

ch = logging.StreamHandler()
formatter = logging.Formatter(
    # "%(asctime)s:%(name)s:%(funcName)s:%(lineno)d:%(levelname)s:%(message)s"
    # "%(funcName)s:%(lineno)d:%(levelname)s:%(message)s"
    "%(asctime)s:%(lineno)d:%(funcName)s:%(message)s"
)
ch.setFormatter(formatter)
logger.addHandler(ch)


class ArchiveBase:

    prev_cache = 2
    next_cache = 10

    support_image_type = [
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
        ".svg",
        ".avif",
    ]
    support_archive_type = [".zip", ".rar", ".7z", ".pdf"]
    support_type = support_image_type + support_archive_type

    def __init__(self, multi_read=False):
        self.file_path = None
        self.data = None
        self.file_list = []
        self.i = 0

        self.multi_read = multi_read
        self.thread_run = False

        self.images = {}

        self.cache = {}

        self.is_directory = False

    def __del__(self):
        self.close()

    def filtering_file_list(self):
        self.file_list = [
            f
            for f in self.file_list
            if str(f)[-1] != "/" and Path(f).suffix.lower() in self.support_type
        ]

    def close(self):
        self.stop = True
        # if self.data is not None:
        #     self.data.close()
        self.file_path = None
        self.file_list = []

    def open(self, file_path, data=None):
        pass

    def suffix(self):
        return self.file_path.suffix.lower()

    def get_data(self, start, end):
        pass

    def in_range(self, i):
        return max(0, min(len(self), i))

    def getitem(self, i):
        pass

    def start_preload(self):
        t = threading.Thread(target=self.preload_thread)
        t.start()

    def preload_thread(self):
        self.stop = False
        while True:
            if self.stop:
                break

            start = self.in_range(self.i - self.prev_cache)
            end = self.in_range(self.i + self.next_cache)

            # logger.debug(f"start, end = {start}, {end}")

            yet = []

            self.cache = {i: self.cache.get(i) for i in range(start, end)}
            yet = [i for i in range(start, end) if self.cache.get(i) is None]

            if len(yet) == 0:
                # logger.debug("cache is full.")
                # logger.debug(f"file_path = {self.file_path}")
                # logger.debug(f"cached page is {self.cache.keys()}")
                time.sleep(1)
                continue

            if self.multi_read:
                logger.debug("getitems")
                logger.debug(f"yet = {yet}")
                # read more because self.i is update till calling getitems
                file_names, images = self.getitems(
                    yet[0], self.in_range(yet[0] + int(self.next_cache / 2))
                )
                logger.debug(f"yet[0], yet[-1] = {yet[0]}, {yet[-1]}")
                for j, file_name, image in zip(
                    list(range(yet[0], yet[-1] + 1)), file_names, images
                ):
                    logger.debug(f"cache: {j}, {file_name}")
                    self.cache[j] = (file_name, image)
            else:
                logger.debug("read single")
                for j in yet:
                    if self.cache[j] is not None:
                        continue
                    self.cache[j] = self.getitem(j)

            logger.debug(f"cache {len(yet)} files. : {self.cache.keys()}")

    def __getitem__(self, i):
        if len(self) == 0:
            return None, None

        i = self.in_range(i)

        if self.cache.get(i) is not None:
            logger.debug("cache hit")
            return self.cache[i]

        self.i = i
        logger.debug(f"cache failed:{i}")
        file_name, data = self.getitem(i)
        self.cache[i] = (file_name, data)

        return file_name, data

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

    def sort_file_list(self):
        self.file_list = ns.natsorted(
            self.file_list, key=lambda x: str(x), alg=ns.PATH | ns.IGNORECASE
        )


class DirectoryArchive(ArchiveBase):
    def __init__(self, file_path, data=None):
        super().__init__()
        self.is_directory = True
        self.random_list = []
        self.open(file_path, data)
        self.gen_random_list()
        self.cache = {}
        # self.start_preload()
        #

    def gen_random_list(self):
        # call after open calling
        self.random_list = [i for i in range(len(self))]
        random.shuffle(self.random_list)

    def search(self, file_path):
        self.i = self.file_list.index(Path(file_path))
        self.cache = {}
        return self.i

    def remove(self, file_path):
        i = self.search(file_path)
        logger.debug(f"remove {i}:{file_path}")
        self.cache = {}
        del self.file_list[i]
        if int(i) in self.random_list:
            logger.debug("i in self.random_list")
            i = int(i)
            self.random_list = [
                n if n < i else n - 1 for n in self.random_list if n != i
            ]
        else:
            logger.debug("i is not in self.random_list")

    def open(self, file_path, data=None):
        # you cannot path data, ignored
        self.file_path = Path(file_path)
        logger.debug("glob")
        self.file_list = list(Path(self.file_path.parent).glob("*"))
        logger.debug("sort")
        self.sort_file_list()
        logger.debug("filtering")
        self.filtering_file_list()
        # logger.debug(self.file_list)
        logger.debug("get index")
        try:
            self.i = self.file_list.index(Path(file_path))
            logger.debug(f"self.i = {self.i}")
        except ValueError:
            logger.debug("search failed. such file does not exist")

    def get_data(self, start, end):
        logger.debug("call")
        start = self.in_range(start)
        end = self.in_range(end)
        logger.debug("return")
        return start, end, self.file_list[start:end], [None] * (end - start)

    def getitem(self, i):
        # disable cache because trash not works well.
        # Other way is is_directory and set file_path as same
        self.cache = {}
        logger.debug(f"i = {i}")
        if 0 <= i < len(self):
            self.i = i
            self.file_path = self.file_list[i]
            return self.file_path, None
        else:
            return "", None

    def random_select(self):
        if len(self.random_list) == 0:
            self.gen_random_list()
            messagebox.showwarning("reset random_list", "reset random_list")
        i = self.random_list.pop()
        return self.getitem(i)


class ZipArchive(ArchiveBase):
    def __init__(self, file_path, data=None):
        if "zipfile" not in globals():
            global zipfile
            import zipfile
        super().__init__()
        self.open(file_path, data)
        self.start_preload()

    def open(self, file_path, data=None):
        logger.debug("called")
        self.file_path = file_path
        self.data = data
        self.file_list = []

        logger.debug("to byte")
        # fp = self.file_path if data is None else io.BytesIO(self.data)
        if self.data is not None:
            self.data.seek(0)
        fp = self.file_path if data is None else self.data

        logger.debug("zip open")
        with zipfile.ZipFile(fp) as f:
            self.file_list = f.namelist()
            # ns.natsorted(f.namelist())
        logger.debug("to list")
        self.sort_file_list()
        self.filtering_file_list()
        logger.debug(self.file_list)
        logger.debug("return")

    def getitem(self, i):
        logger.debug("__getitem__")
        file_name = ""
        file_byte = None

        logger.debug("to byte")
        # fp = self.file_path if self.data is None else io.BytesIO(self.data)
        fp = self.file_path if self.data is None else self.data

        logger.debug("open zip")
        if 0 <= i < len(self):
            with zipfile.ZipFile(fp) as f:
                file_name = Path(self.file_list[i])
                file_byte = f.read(self.file_list[i])

            logger.debug(f"i={i}")
            if i < len(self.file_list):
                logger.debug(self.file_list[i])
        logger.debug(file_name)
        logger.debug("return")
        return file_name, io.BytesIO(file_byte)


class RarArchive(ArchiveBase):
    def __init__(self, file_path, data=None):
        if "rarfile" not in "globals":
            global rarfile
            import rarfile
        super().__init__()
        self.open(file_path, data)
        self.start_preload()

    def open(self, file_path, data=None):
        logger.debug("called")
        self.file_path = file_path
        self.data = data
        self.file_list = []

        logger.debug("to byte")
        if self.data is not None:
            self.data.seek(0)
        fp = self.file_path if data is None else self.data

        logger.debug("open rar")
        with rarfile.RarFile(fp) as f:
            self.file_list = f.namelist()

        logger.debug("open rar")
        self.sort_file_list()
        self.filtering_file_list()
        logger.debug(self.file_list)

    def getitem(self, i):
        logger.debug("__getitem__")
        file_name = ""
        file_byte = None
        logger.debug("to byte")
        fp = self.file_path if self.data is None else self.data
        logger.debug("read file")
        if 0 <= i < len(self):
            with rarfile.RarFile(fp) as f:
                file_name = Path(self.file_list[i])
                file_byte = f.read(self.file_list[i])

        logger.debug(f"i={i}")
        logger.debug(self.file_list[i])
        logger.debug(file_name)
        logger.debug("return")
        return file_name, io.BytesIO(file_byte)


class SevenZipArchive(ArchiveBase):
    def __init__(self, file_path, data=None):
        if "py7zr" not in globals():
            global py7zr
            import py7zr
        super().__init__()
        self.open(file_path, data)
        self.multi_read = True
        self.start_preload()

    def open(self, file_path, data=None):
        logger.debug("called")
        self.file_path = file_path
        self.data = data
        self.file_list = []
        logger.debug("to bytes")
        if self.data is not None:
            self.data.seek(0)
        fp = self.file_path if self.data is None else self.data
        logger.debug("open 7z")
        with py7zr.SevenZipFile(fp, mode="r") as f:
            self.file_list = f.getnames()

        self.sort_file_list()
        self.filtering_file_list()
        logger.debug(self.file_list)
        logger.debug("return")

    def getitems(self, start, end):

        if self.data is not None:
            self.data.seek(0)
        fp = self.file_path if self.data is None else self.data

        file_names = []
        file_bytes = []
        with py7zr.SevenZipFile(fp) as f:
            file_names = [Path(name) for name in self.file_list[start:end]]
            logger.debug("read")
            data = f.read(self.file_list[start:end])
            logger.debug("name, data")
            for name, byte_data in data.items():
                logger.debug("extract data")
                file_bytes.append(byte_data)
        logger.debug("read end")

        return file_names, file_bytes

    def getitem(self, i):
        logger.debug("called")
        logger.debug(f"i = {i}")
        file_name = ""
        file_byte = None
        logger.debug("to byte")
        fp = self.file_path if self.data is None else io.BytesIO(self.data)
        logger.debug("open 7z")
        if 0 <= i < len(self):
            logger.debug("with open")
            file_name = Path(self.file_list[i])
            logger.debug(f"file_name＝ {file_name}")
            logger.debug("read")
            with py7zr.SevenZipFile(fp) as f:
                data = f.read([self.file_list[i]])
                logger.debug("name, data")
                for name, data in data.items():
                    logger.debug("extract data")
                    file_byte = data
            logger.debug("read end")

        logger.debug(f"file_bype = {file_byte}")
        logger.debug(f"i={i}")
        logger.debug(self.file_list[i])
        logger.debug(file_name)
        logger.debug("return")
        return file_name, file_byte


class PdfArchive(ArchiveBase):
    def __init__(self, file_path, data=None):
        if "pdf2image" not in globals():
            global pdf2image
            import pdf2image
        if "PyPDF3" not in globals():
            global PyPDF3
            import PyPDF3
        super().__init__()
        self.images = []

        self.multi_read = True

        self.open(file_path, data)
        self.start_preload()

    def open(self, file_path, data=None):

        self.file_path = file_path
        self.data = data

        page_num = 0
        if self.data is not None:
            data.seek(0)
            pdf = PyPDF3.PdfFileReader(self.data)
            page_num = pdf.getNumPages()
        else:
            with open(self.file_path, "rb") as f:
                pdf = PyPDF3.PdfFileReader(f)
                page_num = pdf.getNumPages()

        self.file_list = [Path(str(i + 1) + ".png") for i in range(page_num)]

    def getitems(self, start, end):
        end += 1
        logger.debug("called")
        logger.debug(f"start, end = {start}, {end}")

        file_names = self.file_list[start:end]
        logger.debug(f"file_names = {file_names}")

        if len(self.images) != 0:
            logger.debug("return cached images")
            return file_names, self.images[start:end]

        logger.debug(f"page = {start}:{end}")

        if self.data is None:
            logger.debug("read images from file_path")
            images = pdf2image.convert_from_path(
                self.file_path, first_page=start, last_page=end + 1
            )
        else:
            logger.debug("read images from data")
            self.data.seek(0)
            images = pdf2image.convert_from_bytes(
                self.data.read(), first_page=start, last_page=end + 1
            )

        logger.debug(f"return. {len(file_names)} == {len(images)}")
        return file_names, images

    def getitem(self, i):
        logger.debug("called")
        file_name = self.file_list[i]
        logger.debug(f"file_name = {file_name}")

        if len(self.images) != 0:
            return file_name, self.images[i]

        image = None

        logger.debug(f"page = {i}")

        if self.data is None:
            logger.debug("read from file_path")
            images = pdf2image.convert_from_path(
                self.file_path, first_page=i, last_page=i + 1
            )
        else:
            logger.debug("read from data")
            self.data.seek(0)
            images = pdf2image.convert_from_bytes(
                self.data.read(), first_page=i, last_page=i + 1
            )

        if len(images) != 0:
            image = images[0]
        else:
            logger.debug("images is not empty.")

        logger.debug("return")
        return file_name, image


class TarArchive(ArchiveBase):
    def __init__(self, file_path, data=None):
        if "tarfile" not in "globals":
            global tarfile
            import tarfile
        super().__init__()
        self.multi_read = True
        self.open(file_path, data)
        self.start_preload()

    def open(self, file_path, data=None):
        logger.debug("called")
        self.file_path = file_path
        self.data = data
        self.file_list = []

        logger.debug("to byte")
        if self.data is not None:
            self.data.seek(0)
        fp = self.file_path if data is None else self.data

        logger.debug("open tar")
        with tarfile.open(fp) as f:
            self.file_list = f.getnames()

        logger.debug("open tar")
        self.sort_file_list()
        self.filtering_file_list()
        logger.debug(self.file_list)

    def getitems(self, start, end):
        end += 1
        logger.debug("called")
        logger.debug(f"start, end = {start}, {end}")

        file_names = self.file_list[start:end]
        logger.debug(f"file_names = {file_names}")
        fp = self.file_path if self.data is None else self.data

        with tarfile.open(fp) as f:
            file_bytes = [io.BytesIO(f.extractfile(name).read()) for name in file_names]

        logger.debug(f"return. {len(file_names)}")
        return file_names, file_bytes

    def getitem(self, i):
        logger.debug("__getitem__")
        file_name = ""
        file_byte = None
        logger.debug("to byte")
        fp = self.file_path if self.data is None else self.data
        logger.debug("read file")
        if 0 <= i < len(self):
            with tarfile.open(fp) as f:
                file_name = Path(self.file_list[i])
                file_byte = f.extractfile(self.file_list[i]).read()

        logger.debug(f"i={i}")
        logger.debug(self.file_list[i])
        logger.debug(file_name)
        logger.debug("return")
        return file_name, io.BytesIO(file_byte)


class ArchiveTree:
    def __init__(self):
        self.root = []
        pass

    def reset(self):
        self.root = []

    def append(self, archive):
        if archive is None:
            logger.debug("archive is None.")
            return
        if archive.is_directory:
            archive.stop = True
            # self.root = [archive]
            return

        if len(self.root) > 1 and self.root[-1].file_path == archive.file_path:
            logger.debug("same archive. skipping")
            return
        # do not delete file_path and file_list
        # and stop preload because do not use so much.
        archive.stop = True
        self.root.append(archive)

    def top(self):
        if len(self.root) == 0:
            return None
        return self.root[0]

    def next_archive(self):
        num = len(self.root) - 1
        if num < 0:
            logger.debug("num < 0")
            return "", None, None

        for i in range(num, -1, -1):
            archive = self.root[i]
            file_path = archive.file_path
            next_file_path, data = archive.next()
            logger.debug(
                f"i,file_path,next_file_path = {i},{file_path},{next_file_path}"
            )
            if file_path == next_file_path:
                logger.debug("go to parent")
                del self.root[i]
                continue

            # archive.start_preload()
            logger.debug(f"next_file_path = {next_file_path}")
            return next_file_path, data, archive

        logger.debug("not found")
        return "", None, None

    def prev_archive(self):
        num = len(self.root) - 1
        if num < 0:
            return "", None, None

        for i in range(num, -1, -1):
            archive = self.root[i]
            file_path = archive.file_path
            next_file_path, data = archive.prev()
            logger.debug(
                f"i,file_path,next_file_path = {i},{file_path},{next_file_path}"
            )
            if file_path == next_file_path:
                logger.debug("go to parent")
                del self.root[i]
                continue
            return next_file_path, data, archive

        logger.debug("not found")
        return "", None, None


class ImageFrame(tk.Canvas):
    algorithm = {
        "Nearest": Image.Resampling.NEAREST,
        "Box": Image.Resampling.BOX,
        "Bilinear": Image.Resampling.BILINEAR,
        "Hamming": Image.Resampling.HAMMING,
        "Bicubic": Image.Resampling.BICUBIC,
        "Lanczos": Image.Resampling.LANCZOS,
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

        self.up_scale = Image.Resampling.NEAREST
        self.down_scale = Image.Resampling.NEAREST

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
            if image.info.get("duration") is not None:
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


class MoveFile:
    def __init__(self):
        self.ret = False
        pass

    def move_file(self, move_to_list, file_path):
        self.file_path = file_path
        self.move_to_list = move_to_list
        if len(self.move_to_list) == 0:
            messagebox.showwarning("No place is registered", "No place is registered")
            return

        self.child = tk.Toplevel()
        self.child.attributes("-type", "dialog")
        # self.child.focus_set()
        self.child.focus_force()
        self.child.grab_set()

        self.child.bind("<KeyPress>", self._move)
        ttk.Label(self.child, text=f"Move {file_path} to").pack(
            side="top", expand=True, fill="x"
        )

        for k, v in self.move_to_list.items():
            ttk.Label(self.child, text=f"{k}:{v}").pack(
                side="top", expand=True, fill="x"
            )

        ttk.Label(self.child, text="q, Esc, Ctrl+[, [: Quit").pack(
            side="top", expand=True, fill="x"
        )

        self.child.bind("<Escape>", lambda event: self.child.destroy())
        self.child.bind("[", lambda event: self.child.destroy())
        self.child.bind("q", lambda event: self.child.destroy())
        self.child.wait_window()
        return self.ret

    def _move(self, event):
        self.child.destroy()
        file_path = self.file_path
        key = event.keysym

        to = self.move_to_list.get(key)
        if to is None:
            messagebox.showwarning(
                "Such place is not in list.", f"Such place is not in list. {key}"
            )
            self.ret = False
            return

        to = Path(to)

        if not to.exists():
            messagebox.showwarning(
                "Such directory does not exist.", f"Such directory does not exist. {to}"
            )
            self.ret = False
            return

        if file_path.resolve() == Path(to / file_path.name).resolve():
            return

        to = to / file_path.name
        if to.exists() and not messagebox.askokcancel(
            "File exists.", "File exists. Overwrite?"
        ):
            logger.debug("Do not overwrite.")
            self.ret = False
            return

        logger.debug(f"Move {file_path} -> {to}")

        shutil.move(file_path, to)
        self.ret = True


class Config:
    default_config = """\
[Setting]

# None, Width, Height or Both
DefaultFitMode = Both
DefaultFullScreen = True

# If you make this value too much, it will occupy too much memory.
DefaultPrevCache = 4
DefaultNextCache = 10

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

# You can use repetition for NextPage and PrevPage.
# For example, 2h means goto next 2 page, type 100h go to next 100 page.
# If you want to reset number, type <Esc>, <Ctrl+[> or simply <[>
NextPage     = h
PrevPage     = l

NextArchive  = j
PrevArchive  = k

Head         = g
Tail         = G

FitNone      = N
FitWidth     = W
FitHeight    = H
FitBoth      = B

PageOrder    = o

TrashFile    = Delete
RenameFile  = e
MoveFile     = m

Quit         = q
FullScreen   = f
Reload       = r

RandomSelect = n

[MoveToList]

# When you press MoveFile key, then press key registered.
# File will be moved to registered place.

# a = /home/GuiltyCat/images/fantastic
# b = /home/GuiltyCat/images/bravo
# c = /home/GuiltyCat/images/wonderful
#
"""

    def __init__(self):
        self.keymap = {}
        self.setting = {}
        self.move_to_list = {}
        pass

    def open(self, file_path):
        file_path = Path(file_path)
        fp = file_path
        if file_path.exists():
            logger.debug("config file exists. reading")
            with open(fp, mode="r", newline="") as f:
                self._load(f)
        else:
            logger.debug("config file do not exists. read default.")
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
            if row[0] == "[MoveToList]":
                config = self.move_to_list
                continue

            if config is None:
                continue

            config[row[0].strip()] = row[1].strip()

    def load_from_args(self, key, value):
        self.settinng[key] = value

    def write_default_config(self, file_path):
        if file_path.exists():
            print(f"{file_path} already exists. Not overwerite.")
            return

        with open(file_path, "w") as f:
            f.write(self.default_config)


class SaltViewer(tk.Tk):
    def __init__(self, config_path, args):
        logger.debug("tk.Tk init")
        super().__init__()

        self.file_path = None

        self.archive = None

        # this directory is the parent of first file_path that passed
        # toself.open()
        self.root_dir = None

        logger.debug("set title")
        self.title("SaltViewer")

        # icon = self.open_svg(None, io.StringIO(Icon.svg))
        # icon = icon.resize((100, 100))
        # self.icon = ImageTk.PhotoImage(image=icon)
        # self.iconphoto(False, self.icon)

        logger.debug("binding functions")
        self.binding = {
            "DoublePage": self.toggle_page_mode,
            "TrashFile": self.trash,
            "RenameFile": self.rename,
            "NextPage": self.next_page,
            "PrevPage": self.prev_page,
            "NextArchive": self.next_archive,
            "PrevArchive": self.prev_archive,
            "PageOrder": self.toggle_order,
            "FitWidth": self.fit_width,
            "FitHeight": self.fit_height,
            "FitBoth": self.fit_both,
            "FitNone": self.fit_none,
            "MoveFile": self.move_file,
            "Quit": self.quit,
            "Reload": self.reload,
            "FullScreen": self.full_screen,
            "Head": self.head,
            "Tail": self.tail,
            "RandomSelect": self.random_select,
        }

        logger.debug("style")
        self.style = ttk.Style()

        self.construct_gui()

        self.double_page = False
        self.right2left = True

        logger.debug("read config")
        self.config = Config()
        logger.debug("config open")
        self.config.open(config_path)

        self.num = 0

        self.tree = ArchiveTree()

        self.load_config(args)

    def random_select(self, event):
        logger.debug("random_select called")
        self._load_root_dir_thread(self.file_path)
        self.tree.reset()
        if self.archive is not None:
            self.archive.close()
        self.archive = None
        self.open(*self.root_dir.random_select())

    def move_file(self, event):

        fullscreen = self.attributes("-fullscreen")
        self.attributes("-fullscreen", False)

        logger.debug("called")

        file_path = self.archive.file_path
        top = self.tree.top()
        if top is not None:
            file_path = Path(top.file_path)

        move_to_list = self.config.move_to_list
        logger.debug(f"{file_path}, {move_to_list}")

        if self.root_dir is None:
            logger.debug("Directory Archive")
            self.root_dir = DirectoryArchive(file_path)
            self.root_dir.stop = True

        if not MoveFile().move_file(move_to_list, file_path):
            logger.debug("move failed")
            self.attributes("-fullscreen", fullscreen)
            return

        if len(self.root_dir) == 1:
            self.archive.close()
            self.quit(None)
            return

        self.archive.close()
        self.archive = None
        self.tree.reset()

        self.root_dir.remove(file_path)
        self.root_dir.cache = {}
        next_file_path = self.root_dir.current()[0]

        self.attributes("-fullscreen", fullscreen)
        logger.debug(f"open {next_file_path}")
        self.open(next_file_path)

    def reload(self, event):
        self.archive.cache = {}
        self.current_page()

    def full_screen(self, event):
        self.attributes("-fullscreen", not self.attributes("-fullscreen"))

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

    def load_config(self, args):
        logger.debug("called")
        logger.debug("overwrite settings")
        for k, v in args.items():
            if v is None:
                continue
            self.config.setting[k] = v

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
            if name == "DefaultFitMode":
                self._change_image_fit_mode(key)
            elif name == "DoublePage":
                self.double_page = True if key == "true" else False
            elif name == "PageOrder":
                self.right2left = True if key == "right2left" else False
            elif name == "UpScale":
                self.image.select_up_scale_algorithm(key)
            elif name == "DownScale":
                self.image.select_down_scale_algorithm(key)
            elif name == "DefaultFullScreen":
                logger.debug("DefaultFullScreen")
                self.attributes("-fullscreen", key == "True")
            elif name == "DefaultPrevCache":
                ArchiveBase.prev_cache = int(key)
            elif name == "DefaultNextCache":
                ArchiveBase.next_cache = int(key)

        self.bind("<Escape>", self.reset_num)
        self.bind("[", self.reset_num)
        for i in range(10):
            self.bind(f"<KeyPress-{i}>", self.num_key)
        logger.debug("return")

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

        if self.root_dir is None:
            logger.debug("Directory Archive")
            self.root_dir = DirectoryArchive(self.archive.file_path)
            self.root_dir.stop = True

        if self.archive.is_directory:
            self.next_page(event)
            return

        next_file_path, data, archive = self.tree.next_archive()
        if next_file_path in ["", self.archive.file_path]:
            top = self.tree.top()
            if top is not None:
                self.root_dir.search(top.file_path)
            self.tree.reset()
            self.archive.close()
            self.archive = None
            file_path = self.root_dir.next()[0]
            self.open(file_path)
            return

        self.archive.close()
        self.archive = None
        logger.debug(f"next_file_path = {next_file_path}")
        self.open(next_file_path, data)

    def prev_archive(self, event):
        if self.root_dir is None:
            logger.debug("Directory Archive")
            self.root_dir = DirectoryArchive(self.archive.file_path)
            self.root_dir.stop = True

        if self.archive.is_directory:
            self.prev_page(event)
            return

        next_file_path, data, archive = self.tree.prev_archive()
        if next_file_path in ["", self.archive.file_path]:
            top = self.tree.top()
            if top is not None:
                self.root_dir.search(top.file_path)
            self.tree.reset()
            self.archive.close()
            self.archive = None
            file_path = self.root_dir.prev()[0]
            self.open(file_path)
            return

        self.archive.close()
        self.archive = None
        logger.debug(f"next_file_path = {next_file_path}")
        self.open(next_file_path, data)

    def construct_gui(self):
        logger.debug("called")
        self.main_frame = ttk.Frame(self)
        self.main_frame.pack(expand=True, fill="both", anchor="center")
        self.main_frame.grid_rowconfigure([0], weight=1)
        self.main_frame.grid_columnconfigure([0], weight=1)

        self.image = ImageFrame(self.main_frame)
        self.image.grid(row=0, column=0, sticky="wens")

        dummy_img = Image.new("RGB", (10, 10), color="black")
        self.image.mode = "Raw"
        logger.debug("----------------------------------")
        logger.debug("dummy image")
        logger.debug("----------------------------------")
        self.image.display(dummy_img)
        self.statusbar = tk.Label(self, text="SaltViewer", anchor="w")

        self.statusbar.pack(side=tk.BOTTOM, fill=tk.X)
        logger.debug("return")

    def rename(self, event):
        fullscreen = self.attributes("-fullscreen")
        self.attributes("-fullscreen", False)

        file_path = self.archive.file_path

        top = self.tree.top()
        if top is not None:
            file_path = Path(top.file_path)

        logger.debug(f"file_path = {file_path}")
        file_name = filedialog.asksaveasfilename(
            initialdir=file_path.parent,
            initialfile=file_path.name,
            defaultextension=file_path.suffix,
        )
        if file_name is None or file_name == "" or file_name == ():
            logger.debug("file_name is None")
            return
        logger.debug(file_name)

        if self.root_dir is None:
            self.root_dir = DirectoryArchive(file_path)
            self.root_dir.stop = True

        # logger.debug(f"root_dir file_list = {self.root_dir.file_list}")
        self.root_dir.remove(file_path)
        # logger.debug(f"root_dir file_list = {self.root_dir.file_list}")
        file_name = Path(file_name)
        if file_name.exists() and not messagebox.askokcancel(
            "Overwrite?", f"Overwrite File?"
        ):
            logger.debug("Cancel overwriting")
            return
        shutil.move(file_path, file_name)

        if len(self.root_dir) == 0:
            logger.debug("directory is empty")
            self.quit(None)
            return

        self.archive.close()
        self.archive = None

        self.root_dir.cache = {}
        next_file_path, data = self.root_dir.current()

        if next_file_path == "":
            next_file_path, data = self.root_dir.prev()

        self.tree.reset()
        logger.debug(f"next_file_path = {next_file_path}")
        self.open(next_file_path, data)
        self.attributes("-fullscreen", fullscreen)

    def trash(self, event):

        fullscreen = self.attributes("-fullscreen")
        self.attributes("-fullscreen", False)

        file_path = self.archive.file_path
        logger.debug(f"file_path = {file_path}")
        top = self.tree.top()
        if top is not None:
            file_path = Path(top.file_path)
        logger.debug(f"file_path = {file_path}")
        if messagebox.askokcancel("Trash file?", f"Trash file?\n{file_path}"):
            global send2trash
            from send2trash import send2trash

            if self.root_dir is None:
                self.root_dir = DirectoryArchive(file_path)
                self.root_dir.stop = True

            # logger.debug(f"root_dir file_list = {self.root_dir.file_list}")
            self.root_dir.remove(file_path)
            # logger.debug(f"root_dir file_list = {self.root_dir.file_list}")
            send2trash(str(file_path))

            if len(self.root_dir) == 0:
                logger.debug("directory is empty")
                self.quit(None)
                return

            self.archive.close()
            self.archive = None

            self.root_dir.cache = {}
            next_file_path, data = self.root_dir.current()

            if next_file_path == "":
                next_file_path, data = self.root_dir.prev()

            self.tree.reset()
            logger.debug(f"next_file_path = {next_file_path}")
            self.attributes("-fullscreen", fullscreen)

            self.open(next_file_path, data)
        else:
            self.attributes("-fullscreen", fullscreen)
            logger.debug("Cancelled")

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
        logger.debug("----------------------------------")
        logger.debug("current")
        logger.debug("----------------------------------")
        self.image.display(image, image2, self.right2left)

    def _open_next(self, c=1):
        logger.debug("called")
        file_path, data = self.archive.next(c)
        if file_path == "":
            logger.debug("file_path is empty")
            return None
        logger.debug(f"file_path={file_path}")
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
        logger.debug("-------------------------------------")
        logger.debug("next_page")
        logger.debug("-------------------------------------")
        self.image.display(image, image2, self.right2left)

    def _open_prev(self, c=1):
        file_path, data = self.archive.prev(c)
        if file_path == "":
            logger.debug("file_path is empty")
            return None
        logger.debug(f"file_path={file_path}")
        logger.debug(f"self.archive.file_path={self.archive.file_path}")
        return self.open_file(file_path, data)

    def prev_page(self, event):
        logger.debug("called")
        image = self._open_prev(self.num)
        self.num = 0
        image2 = None
        if self.double_page:
            image2 = self._open_prev()
        logger.debug("-------------------------------------")
        logger.debug("prev_page")
        logger.debug("-------------------------------------")
        self.image.display(image, image2, not self.right2left)

    def quit(self, event):
        if self.archive is not None:
            self.archive.close()
        self.destroy()

    def open(self, file_path, data=None):
        if self.archive is not None:
            self.archive.stop = True
        if self.root_dir is None:
            logger.debug("self.root_dir is None load directory")
            self._load_root_dir(file_path)
        self.file_path = file_path

        self.archive = self.open_archive(file_path, data)
        file_path, data = self.archive.current()
        logger.debug(f"file_path={file_path}")
        if file_path is None and data is None:
            logger.debug("file may be empty.")
            self.destroy()
        image = self.open_file(file_path, data)
        logger.debug("-------------------------------------")
        logger.debug("open")
        logger.debug(image)
        logger.debug("-------------------------------------")
        if image is None:
            logger.debug("image is None")
            return
        self.image.display(image)
        return image

    def _load_root_dir_thread(self, file_path):
        if self.root_dir is None:
            self.root_dir = DirectoryArchive(file_path)

    def _load_root_dir(self, file_path):
        logger.debug("start load_root dir")
        t = threading.Thread(target=self._load_root_dir_thread, args=(file_path,))
        t.start()

    def open_archive(self, file_path, data=None):
        logger.debug("called")
        print(file_path)
        suffix = Path(file_path).suffix.lower()

        if suffix == ".zip":
            logger.debug("zip")
            archive = ZipArchive(file_path, data)
        elif suffix == ".rar":
            logger.debug("rar")
            archive = RarArchive(file_path, data)
        elif suffix == ".7z":
            logger.debug("7z")
            archive = SevenZipArchive(file_path, data)
        elif suffix == ".pdf":
            logger.debug("pdf")
            archive = PdfArchive(file_path, data)
        elif suffix in [".tar", ".gz"]:
            logger.debug("pdf")
            archive = TarArchive(file_path, data)
        else:
            logger.debug("directory")
            archive = DirectoryArchive(file_path, data)

        # in the case of nested archive
        if self.archive is None:
            return archive

        # logger.debug(f"self.archive file_list = {self.archive.file_list}")
        # logger.debug(f"archive file_list = {archive.file_list}")
        # if not self.archive.is_directory and not archive.is_directory:
        #     logger.debug("self.tree.append")
        self.tree.append(self.archive)

        return archive

    def open_file(self, file_path, data=None):
        if file_path is None:
            logger.debug("file_path is None")
            return
        file_path = Path(file_path)
        logger.debug("called")

        logger.debug("set title")
        title = f"{file_path}:"
        if self.archive.file_path != file_path and self.archive.file_path.stem != str(
            file_path.parent
        ):
            title = f"{self.archive.file_path}/" + title
        page = f"({self.archive.i+1}/{len(self.archive)}):"

        logger.debug(page)
        logger.debug(title)

        self.title(page + title)
        self.statusbar.configure(text=f"{page} {self.archive.file_path}/{title}")
        self.image.title = title

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
            ".avif"
        ]:
            return self.open_image(file_path, data)
        # elif suffix in [".tiff"]:
        #    # can have multi images
        #    pass
        elif suffix in [".svg"]:
            return self.open_svg(file_path, data)
        elif suffix in [".zip", ".rar", ".7z", ".pdf"]:
            return self.open(file_path, data)
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
        import cairosvg

        if data is None:
            svg = cairosvg.svg2png(url=str(image_path))
        else:
            svg = cairosvg.svg2png(file_obj=data)
        svg = io.BytesIO(svg)
        return Image.open(svg)

    def mainloop(self):
        super().mainloop()
        if self.archive is not None:
            self.archive.close()


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

    parser = argparse.ArgumentParser(
        description="SaltViewer. Simple (archived) image viewer (https://github.com/GuiltyCat/SaltViewer)"
    )
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
    parser.add_argument(
        "--debug", help="run as debug mode. All log is printed.", action="store_true"
    )
    parser.add_argument(
        "--fullscreen", help="run as fullscreen mode", action="store_true", default=None
    )
    parser.add_argument(
        "--prev_cache",
        help="number of previous page cache. Default is 4",
        type=int,
        default=None,
    )
    parser.add_argument(
        "--next_cache",
        help="number of previous page cache. Default is 10",
        type=int,
        default=None,
    )
    parser.add_argument(
        "--fit_mode",
        help="fit_mode. Both, Raw, Width, Height.  Default is Both",
        default=None,
    )
    parser.add_argument(
        "--page_order",
        help="page order in double page mode. right2left or left2right. Default is right2left",
        default=None,
    )
    parser.add_argument(
        "--double",
        help="Double page mode. Default is %(default)s.",
        action="store_true",
        default=None,
    )
    parser.add_argument(
        "--upscale",
        help="Upscale algorithm. Nearest, Box, Bilinear, Hamming, Bicubic, Lanczos. Default is Lanczos",
        default=None,
    )
    parser.add_argument(
        "--downscale",
        help="Downscale algorithm. Nearest, Box, Bilinear, Hamming, Bicubic, Lanczos. Default is Lanczos",
        default=None,
    )

    args = parser.parse_args()

    args.path = Path(args.path)

    if args.icon:
        logger.debug("save icon")
        Icon().save_icon(args.path)
        return

    if args.default_config:
        logger.debug("write default config")
        Config().write_default_config(args.path)
        return

    if args.debug:
        # logger.debug("setLevel DEBUG")
        # logger.setLevel(logging.DEBUG)
        pass

    sv_args = {
        "DefaultFitMode": args.fit_mode,
        "DefaultFullScreen": args.fullscreen,
        "DefaultPrevCache": args.prev_cache,
        "DefaultNextCache": args.next_cache,
        "UpScale": args.upscale,
        "DownScale": args.downscale,
    }

    logger.debug("SaltViewer Init")
    sv = SaltViewer(args.config, sv_args)
    logger.debug("opee args.path")
    sv.open(Path(args.path))
    logger.debug("mainloop")
    sv.mainloop()


if __name__ == "__main__":
    main()
