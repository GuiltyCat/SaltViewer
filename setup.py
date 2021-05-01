import setuptools

with open("README.md", "r") as f:
    description = f.read()

requirements = [
    "natsort",
    "pillow",
    "send2trash",
    "rarfile",
    "py7zr",
    "cairosvg",
    "pdf2image",
    "pypdf3",
]
setuptools.setup(
    name="salt-viewer",
    version="0.1.3",
    description="Simple (archived) image viewer",
    long_description=description,
    long_description_content_type="text/markdown",
    url="https://github.com/GuiltyCat/SaltViewer",
    author="GuiltyCat",
    keywords="image, viewer, archive, animation",
    install_requires=requirements,
    setup_requires=requirements,
    py_modules=["salt_viewer"],
    entry_points={"console_scripts": ["salt-viewer=salt_viewer:main"]},
)
