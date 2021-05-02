SaltViewer
===============

Very simple image viewer on tkinter.

<a href='https://svgshare.com/s/WiE' ><img src='https://svgshare.com/i/WiE.svg' width=300 height=300 title='SaltViewerIcon' /></a>

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
- Keyboard shortcut
- Repetition key
	- For example `100h` means go to next 100 page.
- Open archive files
	- Zip, Rar, 7z, Pdf
- Trash image or archive


How to install
-----------


```
pip install salt-viewer
```

or

```
yay -S salt-viewer
```

I use `python3.9.3`. However it will work on old version greater than `python3.5`.


This scripts use these pip modules.

- cairosvg
- natsort
- pdf2python
- pillow
- py7zr
- pypdf3
- rarfile
- send2trash

And use these packages.

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

usage: salt_viewer.py [-h] [--config CONFIG] [--icon] [--default_config] [--debug] [--fullscreen] [--prev_cache PREV_CACHE] [--next_cache NEXT_CACHE] [--fit_mode FIT_MODE] [--page_order PAGE_ORDER] [--double] [--upscale UPSCALE] [--downscale DOWNSCALE] path

SaltViewer

positional arguments:
  path                  image file or archive file

optional arguments:
  -h, --help            show this help message and exit
  --config CONFIG       configuration file path. default is <HOME>/.svrc
  --icon                write icon to path
  --default_config      write default configuration to path. salt-viewer --default_config
  --debug               run as debug mode. All log is printed.
  --fullscreen          run as fullscreen mode
  --prev_cache PREV_CACHE
                        number of previous page cache. Default is 4
  --next_cache NEXT_CACHE
                        number of previous page cache. Default is 10
  --fit_mode FIT_MODE   fit_mode. Both, Raw, Width, Height. Default is Both
  --page_order PAGE_ORDER
                        page order in double page mode. right2left or left2right. Default is right2left
  --double              Double page mode. Default is False.
  --upscale UPSCALE     Upscale algorithm. Nearest, Box, Bilinear, Hamming, Bicubic, Lanczos. Default is Lanczos.
  --downscale DOWNSCALE
                        Downscale algorithm. Nearest, Box, Bilinear, Hamming, Bicubic, Lanczos. Default is Lanczos.
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

Head        = g
Tail        = G

Quit        = q
FullScreen  = f
Reload      = r
```

Setting
------------------

You can change these settings via configuration file.

```
[Setting]

# None, Width, Height or Both
DefaultFitMode = Both
DefaultFullScreen = True

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
salt-viewer --icon icon.svg
```

Icon format is svg only. Suffix is ignored.


Yet Implemented
----------------

- Pre resize and convert
	- Big images takes time to resize and convert to tkImage
	- And do resize in preload
- Zoom in and Zoom out image
- Move around images
