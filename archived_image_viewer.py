import csv
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
        return self[self.i]

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
        super().__init__(master, highlightthickness=0, bg="black")
        self.master = master
        self.item = None

        self.orig_image = None
        self.orig_image2 = None

        self.master.bind(
            "<Configure>", lambda *kw: self.display(self.orig_image, self.orig_image2)
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

        self.image = Image.new("RGB", (width, height))
        if right2left:
            image, image2 = image2, image

        # left
        left = int(width / 2 - image.width)
        upper = int((height - image.height) / 2)
        self.image.paste(image, (left, upper))
        # right
        left = int(width / 2)
        upper = int((height - image2.height) / 2)
        self.image.paste(image2, (left, upper))
        return self.image

    def display(self, image, image2=None, right2left=True):
        self.orig_image = image
        self.orig_image2 = image2
        if image is not None:
            div = 1 if image2 is None else 2
            image = self.resize_image(image, div)
            image2 = self.resize_image(image2, div)

            self.image = self.merge_image(image, image2, right2left)
            self.image = ImageTk.PhotoImage(image=self.image)
            if self.item is not None:
                self.delete(self.item)
            self.configure(width=self.image.width(), height=self.image.height())
            sx, sy = self.center_shift(self.image.width(), self.image.height())
        else:
            self.image = None
            sx = 0
            sy = 0
        self.item = self.create_image(sx, sy, image=self.image, anchor="nw")

    def center_shift(self, image_width, image_height):
        return (self.width() - image_width) / 2, (self.height() - image_height) / 2

    def width(self):
        return self.master.winfo_width()

    def height(self):
        return self.master.winfo_height()

    def fit_in_frame(self, image, div=1):
        width = self.width() / div
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

        self.double_page = False
        self.right2left = True

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

    def keybinding(self):
        binding = {
            "l": self.prev_page,
            "h": self.next_page,
            "d": self.toggle_page_mode,
            "o": self.toggle_order,
            "q": self.quit,
        }
        for k, v in binding.items():
            self.bind(f"<KeyPress-{k}>", v)

        self.bind("<Delete>", self.delete)

    def delete(self, event):
        if messagebox.askokcancel("Delete file?", "Delete file?"):
            print("Deleted.")
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
            return None
            # self.image.display(None)

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
            return None
        return image
        # self.image.display(image)


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
