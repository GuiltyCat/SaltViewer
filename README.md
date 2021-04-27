ArchivedImageViewer
===============

Now on development.

Why
-------------

- mcomix do not support GIF animation.
- mcomix do not support trash command.
- mcomix3 do not support delete command.

Thus I need mcomix alternative.

Feature
------------

- [x] Pure python
- [x] Single script
- [x] Support archive
	- Zip, Rar, 7z
- [x] Support image type
    - obey pillow
- [x] Support dual page mode
- [] Support GIF animation
- [x] Delete image
- [x] Configure file
- [] Cache image for speed

Requirements
----------

My envirionment is `python3.9.3`. However it will work on old version of `python`.

- natsort
- pillow
- send2trash
- rarfile
- py7zr

```
pip install natsort pillow send2trash
```

How to use
-----------

Install requirements.

```
python archived_image_viewer.py <image file | zip file>
```
