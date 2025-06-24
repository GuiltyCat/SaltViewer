SaltViewer
===============

Very simple image viewer on tkinter.

![SaltViewerIcon](./icon.svg)

Why
-------------

I need mcomix alternative. Thus this program is developed.

Support these.

- Many image type
    - pillow
	- svg
- Animation
	- GIF, PNG
	- duration auto adjustment
- Trash command
- Double page mode
- Full screen mode
- Vim like keymap (Vim like keyboard shortcut)
	- You can custamize by yourself
- Repetition key
	- For example `100h` means go to next 100 page
- Open archive files
	- Zip, Rar, 7z, Pdf, tar, tar.gz
- Trash image or archive
- Move file wiht key
- Support nested archive


Support Format
--------------

- .bmp
- .dib
- .eps
- .gif
- .icns
- .ico
- .im
- .jpg
- .jpeg
- .msp
- .pcx
- .png
- .ppm
- .sgi
- .spider
- .tga
- .tiff
- .webv
- .xbm
- .svg
- .avif
- .webp

- .zip
- .rar
- .7z
- .pdf
- .tar
- .tar.gz


How to install
-----------

```
git clone https://github.com/GuiltyCat/SaltViewer
cd SaltViewer
python -m venv venv
source venv/bin/activate
pip install .
```

I use `python3.13.3`. However it will work on old version greater than `python3.5`.


Also use these packages.

- unrar(preferred), unar or bsdtar
	- For rarfile
- poppler
	- For pdf2python


How to Use
---------

Now you can use `salt-viewer` command.

```
salt-viewer <image file | archive file>
```

If you use linux, you should use alias for time saving.

```
alias sv=salt-viewer
```

Document
======================


```
$ salt-viewer --help
usage: salt_viewer.py [-h] [--config CONFIG] [--default_config] [--debug] [--fullscreen]
                      [--prev_cache PREV_CACHE] [--next_cache NEXT_CACHE] [--fit_mode FIT_MODE]
                      [--page_order PAGE_ORDER] [--double] [--upscale UPSCALE]
                      [--downscale DOWNSCALE]
                      path

SaltViewer. Simple (archived) image viewer (https://github.com/GuiltyCat/SaltViewer)

positional arguments:
  path                  image file or archive file

options:
  -h, --help            show this help message and exit
  --config CONFIG       configuration file path. default is /home/miyamoto/.svrc
  --default_config      write default configuration to path. salt-viewer --default_config >~/.svrc
  --debug               run as debug mode. All log is printed.
  --fullscreen          run as fullscreen mode
  --prev_cache PREV_CACHE
                        number of previous page cache. Default is 4
  --next_cache NEXT_CACHE
                        number of previous page cache. Default is 10
  --fit_mode FIT_MODE   fit_mode. Both, Raw, Width, Height. Default is Both
  --page_order PAGE_ORDER
                        page order in double page mode. right2left or left2right. Default is
                        right2left
  --double              Double page mode. Default is None.
  --upscale UPSCALE     Upscale algorithm. Nearest, Box, Bilinear, Hamming, Bicubic, Lanczos.
                        Default is Lanczos
  --downscale DOWNSCALE
                        Downscale algorithm. Nearest, Box, Bilinear, Hamming, Bicubic, Lanczos.
                        Default is Lanczos
```

How to use
-----------------

The only way to control SaltViewer is key press.
You can custamize keymaps by argments or config file.

How to Use SaltViewer in default keymap. But you can custamize via
Basic keymaps.

- Page movements
	- NextPage: h. Support repetition.
	- PrevPage: l. Support repetition.
- Archive movements
	- NextArchive: j. Not support repetition.
	- PrevArchive: k. Not support repetition.

If you open image file in directory, NextArchive and PrevArchive command is works as NextPage and PrevPage.
This command is assumed to use when opening a archive file like zip.

If you open archive and press PrevArchive, the first page of previous archive is opened not the end page.


In nested archive, like zip in zip or rar in rar, SaltViewer automatically open recursively till reaching image file.
In other words, SaltViewer automatically open recursively and flatten nested archive in NextArchive.
However, in the case of PrevArchive, a first page of first archive in archives is opened.

To move archive in archive, you can use NextArchive and PrevArchive.
For example, assume that you open a sample1.zip below.

- sample1.zip
	- nested_sample1.rar
		- 1.jpg
		- 2.jpg
		- 3.jpg
	- nested_sample2.zip
		- 1.png
		- 2.png
		- 3.png
- sample2.7z
	- 1.svg

SaltViewer displays 1.jpg in nested_sample1.
Then if you type NextPage, 2.jpg in nested_sample1 is opened.
If you type NextArchive, SaltViewer open 1.png in nested_sample2.zip
Thsn if you type PrevArchive, SaltViewer open 1.jpg in nested_sample2. 

You can walk around archive like you are in directory.

If you reach the end of file and type, in this case 3.png in nested_sample2.zip, 1.svg in sample2.7z is opened.


Config file
--------------

Support config file.
Default reading place is `~/.svrc`.

You can write default default config file by running this command option.

```
salt-viewer --default_config ~/.svrc
```

Be careful, this command do NOT overwrite a existing file.


Keymap
----------

You can change these keymaps via configuration file.


```
[Keymap]

DoublePage  = d


# You can use repetition for NextPage and PrevPage.
# For example, 2h means goto next 2 page, type 100h go to next 100 page.
# If you want to reset number, type <Esc>, <Ctrl+[> or simply <[>
NextPage    = h
PrevPage    = l

NextArchive = j
PrevArchive = k

Head        = g
Tail        = G


FitNone     = N
FitWidth    = W
FitHeight   = H
FitBoth     = B

PageOrder   = o


TrashFile   = Delete
MoveFile    = m

Quit        = q
FullScreen  = f
Reload      = r


[MoveToList]

# When you press MoveFile key, then press key registered.
# File will be moved to registered place.

# a = /home/GuiltyCat/images/fantastic
# b = /home/GuiltyCat/images/bravo
# c = /home/GuiltyCat/images/wonderful
#
```

Setting
------------------

You can change these settings via configuration file.

```
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
```

MoveList
-----------------

You can set move list.

If you type MoveFile key, a place list is appear.
These list contains key and place pair.
Then you type a key, opening file will be moved to a place.

```
[MoveToList]

# When you press MoveFile key, then press key registered.
# File will be moved to registered place.

# a = /home/GuiltyCat/images/fantastic
# b = /home/GuiltyCat/images/bravo
# b = /home/GuiltyCat/images/wonderful
#
```



Page Cache
------------


SaltViewer's page cache do something strange.

SaltViewer read previous and next pages around a current page.
For speed, this preload is running on an other thread.

Preload thread read by one page, or half of self.next_cache pages not unpreloaded number of pages.
And automatically deleted out of range pages.

Sometimes `getitems` may takes too much time and preload cache use used in `getitems`.
Thus preload should be as many as possible.

If you make next_cache and prev_cache too much, it will occupy memory and make your PC freeze.
This problem happens when you tried to open high quality files.



Icon
-----------

You can create SaltViewer Icon by running.

```
pip install svgwrite
python icon.py
```

Then `icon.svg` is generated.


Yet Implemented
----------------

- Pre resize and convert
	- Big images takes time to resize and convert to tkImage
	- And do resize in preload
- Zoom in and Zoom out image
- Move around images



TODO
----------------

- History
- Merge move_file and trash because both have very similar code.
