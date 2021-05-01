SaltViewer
===============

Very simple image viewer on tkinter.

<a href='https://svgshare.com/s/WiE' ><img src='https://svgshare.com/i/WiE.svg' width=300 height=300 title='SaltViewerIcon' /></a>

Why
-------------

I use mcomix on Linux for a long time. 
However, default mcomix do not support 

- GIF animation
- Trash command

Thus I need mcomix alternative.
I want to treat 

- Many image type
- Archive files, like zip, rar, 7z
- Animation image like GIF
- Trash image or archive


Feature
------------

- Single script
- Support archive
	- Zip, Rar, 7z, Pdf
- Support many image types
    - pillow
	- svg
- Support dual page mode
- Support animation
	- duration auto adjustment
	- GIF, PNG
- Repetition key
	- For example `100h` means go to next 100 page.
- Delete image
- Configure file


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
