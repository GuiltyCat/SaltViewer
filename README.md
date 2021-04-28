SaltViewer
===============

Now on development.

Why
-------------

I use mcomix for a long time. However,

- mcomix do not support GIF animation.
- mcomix do not support switch rm command and trash command.
- mcomix3 do not support delete command.

Thus I need mcomix alternative.
I need these functions.

- Support many image type
- Support archive like zip, rar, 7z without extraction
- Support animation image like GIF.
- Support delete and trash command.


Feature
------------

- [x] Pure python
- [x] Single script
- [] Support archive
	- [x] Zip
	- [x] Rar
	- [x] 7z
- [x] Support image type
    - obey pillow
	- [] png
- [x] Support dual page mode
- [x] Support animation
	- [x] duration auto adjustment
	- [x] GIF
- [x] Delete image
- [x] Configure file
- [] Cache image for speed

How to use
-----------

### Install Requirements

My envirionment is `python3.9.3`. However it will work on old version of `python`.

- natsort
- pillow
- send2trash
- rarfile
- py7zr

- unrar(preferred), unar or bsdtar

```
pip install natsort pillow send2trash
```

```
sudo apt install unrar
sudo pacman -S unrar
```

### Run

```
python archived_image_viewer.py <image file | archive file>
```


