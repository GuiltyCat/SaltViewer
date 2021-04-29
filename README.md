SaltViewer
===============

Very simple image viewer on tkinter.

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

I use `python3.9.3`. However it will work on old version greater than `python3.5`.


This scripts use these pip modules.

- cairosvg
- natsort
- pdf2python
- pillow
- py7zr
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

Cutout from default configuration file.


```
[Keymap]

DoublePage  = d
TrashFile   = Delete

NextPage    = h
PrevPage    = l

# You can use repetition for NextPage and PrevPage.
# For example, 2h means goto next 2 page, type 100h go to next 100 page.
# If you want to reset number, type <Esc>, <Ctrl+[> or simply <[>

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
```


TODO
--------

- Cache image for speed
