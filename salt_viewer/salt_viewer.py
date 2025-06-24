import argparse
import csv
import io
import logging
import shutil
import threading
import time
import tkinter as tk
import tkinter.filedialog as filedialog
import tkinter.messagebox as messagebox
import tkinter.ttk as ttk
from pathlib import Path
from archive import (
    ArchiveBase,
    DirectoryArchive,
    RarArchive,
    SevenZipArchive,
    ZipArchive,
    PdfArchive,
    TarArchive,
)
import pillow_avif
from PIL import Image, ImageTk

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

ch = logging.StreamHandler()
formatter = logging.Formatter(
    "%(asctime)s:%(name)s:%(funcName)s:%(lineno)d:%(levelname)s:%(message)s"
)
ch.setFormatter(formatter)
logger.addHandler(ch)


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
        if self.master.master is None:
            raise RuntimeError("master.master is None")
        self.master.master.title(
            f"{self.title}:{counter}/{image.n_frames}:"
            + f"fps={self.fps:.2f}/{1 / (duration / 1000):.2f}"
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
        self.setting[key] = value

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
            if self.archive is not None:
                self.archive.close()
            self.quit(None)
            return

        if self.archive is not None:
            self.archive.close()
        self.archive = None
        self.tree.reset()

        self.root_dir.remove(file_path)
        self.root_dir.cache = {}

        if self.root_dir is None:
            logger.debug("root_dir.current() is None")
            self.quit(None)
            return
        current = self.root_dir.current()
        if current is None:
            logger.debug("root_dir.current() is None")
            self.quit(None)
            return
        if len(current) == 0:
            logger.debug("root_dir.current() is empty")
            self.quit(None)
            return
        next_file_path = current[0]

        self.attributes("-fullscreen", fullscreen)
        logger.debug(f"open {next_file_path}")
        self.open(next_file_path)

    def reload(self, event):
        _ = event
        if self.archive is None:
            return
        self.archive.cache = {}
        self.current_page()

    def full_screen(self, event):
        _ = event
        self.attributes("-fullscreen", not self.attributes("-fullscreen"))

    def fit_width(self, event):
        _ = event
        self._change_image_fit_mode("Width")
        self.current_page()

    def fit_height(self, event):
        _ = event
        self._change_image_fit_mode("Height")
        self.current_page()

    def fit_both(self, event):
        _ = event
        self._change_image_fit_mode("Both")
        self.current_page()

    def fit_none(self, event):
        _ = event
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
            match name:
                case "DefaultFullScreen":
                    self.attributes("-fullscreen", key == "True")
                case "DefaultPrevCache":
                    ArchiveBase.prev_cache = int(key)
                case "DefaultNextCache":
                    ArchiveBase.next_cache = int(key)
                case "DefaultFitMode":
                    self._change_image_fit_mode(key)
                case "DoublePage":
                    self.double_page = True if key == "true" else False
                case "PageOrder":
                    self.right2left = True if key == "right2left" else False
                case "UpScale":
                    self.image.select_up_scale_algorithm(key)
                case "DownScale":
                    self.image.select_down_scale_algorithm(key)
                case _:
                    print(f"Not supported.: {name} = {key}")

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
        match key:
            case "Both":
                self.image.fit_width = True
                self.image.fit_height = True
            case "Width":
                self.image.fit_width = True
                self.image.fit_height = False
            case "Height":
                self.image.fit_width = False
                self.image.fit_height = True
            case "None":
                self.image.fit_width = False
                self.image.fit_height = False

    def head(self, event):
        _ = event
        if self.archive is None:
            return
        self.archive.head()
        self.current_page()

    def tail(self, event):
        _ = event
        if self.archive is None:
            return
        self.archive.tail()
        self.current_page()

    def next_archive(self, event):
        if self.archive is None:
            logger.info("Archive is None")
            return
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
            next_file = self.root_dir.next()
            if next_file is None or len(next_file) == 0:
                logger.debug("directory is empty")
                self.quit(None)
                return
            file_path = next_file[0]
            self.open(file_path)
            return

        self.archive.close()
        self.archive = None
        logger.debug(f"next_file_path = {next_file_path}")
        self.open(next_file_path, data)

    def prev_archive(self, event):
        if self.archive is None:
            logger.info("Archive is None")
            return
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
            prev_file = self.root_dir.prev()
            if prev_file is None or len(prev_file) == 0:
                logger.debug("directory is empty")
                self.quit(None)
                return
            file_path = prev_file[0]
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

        if self.archive is None:
            logger.info("Archive is None")
            return

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
            "Overwrite?", "Overwrite File?"
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

        if self.archive is None:
            logger.info("Archive is None")
            return

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
        if self.archive is None:
            logger.info("Archive is None")
            return
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
        if self.archive is None:
            logger.info("Archive is None")
            return
        file_path, data = self.archive.next(c)
        if file_path == "":
            logger.debug("file_path is empty")
            return None
        logger.debug(f"file_path={file_path}")
        return self.open_file(file_path, data)

    def next_page(self, event):
        logger.debug("called")
        # back to the second page then next
        if self.archive is None:
            logger.info("Archive is None")
            return
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
        if self.archive is None:
            logger.info("Archive is None")
            return
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
        _ = event
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
        if self.archive is None:
            logger.debug("archive is None")
            return
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

        match suffix:
            case ".zip":
                logger.debug("zip")
                archive = ZipArchive(file_path, data)
            case ".rar":
                logger.debug("rar")
                archive = RarArchive(file_path, data)
            case ".7z":
                logger.debug("7z")
                archive = SevenZipArchive(file_path, data)
            case ".pdf":
                logger.debug("pdf")
                archive = PdfArchive(file_path, data)
            case ".tar" | ".gz":
                logger.debug("tar or gz")
                archive = TarArchive(file_path, data)
            case _:
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
        if self.archive is None:
            logger.info("Archive is None")
            return
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
        page = f"({self.archive.i + 1}/{len(self.archive)}):"

        logger.debug(page)
        logger.debug(title)

        self.title(page + title)
        self.statusbar.configure(text=f"{page} {self.archive.file_path}/{title}")
        self.image.title = title

        logger.debug(file_path)
        suffix = file_path.suffix.lower()
        logger.debug(suffix)
        if suffix in ArchiveBase.support_image_type:
            return self.open_image(file_path, data)
        # elif suffix in [".tiff"]:
        #    # can have multi images
        #    pass
        elif suffix in [".svg"]:
            return self.open_svg(file_path, data)
        elif suffix in ArchiveBase.support_type:
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
        if "cairosvg" not in globals():
            global cairosvg
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
