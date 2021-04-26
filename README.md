ArchivedImageViewer
===============

Now on development.

Why
-------------

- mcomix do not support GIF animation.
- mcomix do not support trash command.
- mcomix3 do not support delete command.

Purpose
------------

- Pure python
- Single file
- Support archive
	- Zip
- Support image
	- obey pillow
- Support dual page mode
- Support GIF animation(Yet)
- Delete image(Yet)

Requirements
----------

My envirionment is `python3.9.3`. However it will work on old version of `python`.

- natsort
- pillow
- send2trash

```
pip install natsort pillow send2trash
```

How to use
-----------

```
python archived_image_viewer.py <image file | zip file>
```


