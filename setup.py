import setuptools

with open("README.md", "r") as f:
    description = f.read()

setuptools.setup(
    name="salt-viewer",
    version="0.1.1",
    description="Simple image viewer",
    long_description=description,
    long_description_content_type='text/markdown',
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
    entry_points={"console_scripts": ["salt-viewer=salt_viewer:main"]},
)
