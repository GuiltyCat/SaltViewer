from abc import abstractmethod
from pathlib import Path
import shutil
import logging
import random
import threading
import time
import tkinter.messagebox as messagebox
import io
import natsort as ns
import tempfile


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
formatter = logging.Formatter(
    "%(asctime)s:%(name)s:%(funcName)s:%(lineno)d:%(levelname)s:%(message)s"
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
        ".webp",
    ]
    support_archive_type = [".zip", ".rar", ".7z", ".pdf", ".gz", ".tar"]
    support_type = support_image_type + support_archive_type

    def __init__(self, multi_read=False):
        self.file_path = None
        self.data = None
        self.file_list: list[Path] = []
        self.i = 0

        self.multi_read = multi_read
        self.thread_run = False

        self.images: dict[str, bytes] = {}

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

    @abstractmethod
    def open(self, file_path, data=None):
        pass

    def suffix(self):
        if self.file_path is None:
            raise Exception("file_path is None")
        return self.file_path.suffix.lower()

    @abstractmethod
    def get_data(self, start, end):
        return int(), int(), [], []

    def in_range(self, i):
        return max(0, min(len(self), i))

    @abstractmethod
    def getitem(self, i) -> tuple[Path, io.BytesIO | None]:
        return Path(), io.BytesIO()

    @abstractmethod
    def getitems(self, start, end):
        return [], []

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
                logger.debug("cache is full.")
                logger.debug(f"file_path = {self.file_path}")
                logger.debug(f"cached page is {self.cache.keys()}")
                time.sleep(0.1)
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
            self.file_list, key=lambda x: str(x), alg=ns.ns.PATH | ns.ns.IGNORECASE
        )


class DirectoryArchive(ArchiveBase):
    def __init__(self, file_path, data=None):
        super().__init__()
        self.is_directory = True
        self.random_list = []
        self.open(file_path, data)
        self.gen_random_list()
        self.cache = {}

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
        _ = data
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
            return Path(), None

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
            # self.file_list = f.namelist()
            self.file_list = [Path(s) for s in f.namelist()]
        logger.debug("to list")
        self.sort_file_list()
        self.filtering_file_list()
        logger.debug(self.file_list)
        logger.debug("return")

    def getitem(self, i):
        logger.debug("__getitem__")
        file_name = Path()
        file_byte = None

        logger.debug("to byte")
        # fp = self.file_path if self.data is None else io.BytesIO(self.data)
        fp = self.file_path if self.data is None else self.data

        logger.debug("open zip")
        if 0 <= i < len(self):
            with zipfile.ZipFile(fp) as f:
                file_name = str(self.file_list[i])
                file_byte = f.read(file_name)

            logger.debug(f"i={i}")
            if i < len(self.file_list):
                logger.debug(self.file_list[i])
        else:
            raise ValueError("index out of range")
        logger.debug(file_name)
        logger.debug("return")
        if file_byte is None:
            raise ValueError("file_byte is None. file not found in zip.")
        return Path(file_name), io.BytesIO(file_byte)


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
            # self.file_list = f.namelist()
            self.file_list = [Path(s) for s in f.namelist()]

        logger.debug("open rar")
        self.sort_file_list()
        self.filtering_file_list()
        logger.debug(self.file_list)

    def getitem(self, i):
        logger.debug("__getitem__")
        file_name = Path()
        file_byte = None
        logger.debug("to byte")
        fp = self.file_path if self.data is None else self.data
        logger.debug("read file")
        if 0 <= i < len(self):
            with rarfile.RarFile(fp) as f:
                file_name = str(self.file_list[i])
                file_byte = f.read(file_name)

        if file_byte is None:
            raise ValueError("file_byte is None. file not found in rar.")
        logger.debug(f"i={i}")
        logger.debug(self.file_list[i])
        logger.debug(file_name)
        logger.debug("return")
        return Path(file_name), io.BytesIO(file_byte)


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
            logger.debug("getnames")
            logger.debug(self.file_list)

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
            file_list = [str(name) for name in self.file_list[start:end]]

            tmp_dir = tempfile.mkdtemp()
            f.extract(path=tmp_dir, targets=file_list)

            for name in file_list:
                file_path = Path(f"{tmp_dir}/{name}")
                with open(file_path, "rb") as f:
                    file_bytes.append(io.BytesIO(f.read()))
            shutil.rmtree(tmp_dir)

        logger.debug("read end")

        return file_names, file_bytes

    def getitem(self, i):
        logger.debug("called")
        logger.debug(f"i = {i}")
        file_name = Path()
        file_byte = None
        logger.debug("to byte")
        fp = self.file_path if self.data is None else io.BytesIO(self.data)
        logger.debug("open 7z")
        if 0 <= i < len(self):
            logger.debug("with open")
            file_name = Path(self.file_list[i])
            logger.debug(f"file_name＝ {file_name}")
            logger.debug("read")
            with py7zr.SevenZipFile(fp, mode="r") as f:
                temp_dir = tempfile.mkdtemp()
                f.extract(path=temp_dir, targets=[self.file_list[i]])

                file_name = Path(f"{temp_dir}/{self.file_list[i]}")
                with open(file_name, "rb") as f:
                    file_byte = io.BytesIO(f.read())

                shutil.rmtree(temp_dir)
            logger.debug("read end")

        if file_byte is None:
            raise ValueError("file_byte is None. file not found in 7z.")

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
        if data is not None:
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
        file_name: Path = self.file_list[i]
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

        if image is None:
            raise ValueError("image is None. file not found in pdf.")

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
        file_path = self.file_path if data is None else self.data

        logger.debug("open tar")
        logger.debug(f"file_path = {file_path}")
        logger.debug(f"type(file_path) = {type(file_path)}")
        with tarfile.open(file_path) as f:
            self.file_list = [Path(s) for s in f.getnames()]

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
            file_bytes = []
            for name in file_names:
                file = f.extractfile(str(name))
                if file is None:
                    raise ValueError("file is None. file not found in tar.")
                file_bytes.append(io.BytesIO(file.read()))

            # file_bytes = [io.BytesIO(f.extractfile(name).read()) for name in file_names]

        logger.debug(f"return. {len(file_names)}")
        return file_names, file_bytes

    def getitem(self, i):
        logger.debug("__getitem__")
        file_name = Path()
        file_byte = None
        logger.debug("to byte")
        fp = self.file_path if self.data is None else self.data

        logger.debug("read file")
        if 0 <= i < len(self):
            with tarfile.open(fp) as f:
                file_name = str(self.file_list[i])
                file = f.extractfile(file_name)
                if file is None:
                    raise ValueError("file is None. file not found in tar.")
                file_byte = file.read()

        if file_byte is None:
            raise ValueError("file_byte is None. file not found in tar.")

        logger.debug(f"i={i}")
        logger.debug(self.file_list[i])
        logger.debug(file_name)
        logger.debug("return")
        return Path(file_name), io.BytesIO(file_byte)


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
