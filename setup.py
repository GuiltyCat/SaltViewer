import setuptools

setuptools.setup(
    name="salt-viwer",
    version="0.0.1",
    description="Simple image viewer",
    long_description="Supports many images, animation images, and archives.",
    url="https://github.com/GuiltyCat/SaltViewer",
    author="GuiltyCat",
    keywords="image, viewer, archive, animation",
    install_requires=[
        "natsort",
        "pillow",
        "send2trash",
        "rarfile",
        "py7zr",
        "cairosvg",
    ],
    py_modules=['salt_viewer'],
    entry_points={"console_scripts": ["sv=salt_viewer:main"]},
)
