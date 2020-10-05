from os import path

from setuptools import find_packages, setup

root = path.abspath(path.dirname(__file__))
with open(path.join(root, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="scrobblez",
    version="0.1.0",
    description="Scrobbler for MPRIS 2 compatible clients",
    url="https://github.com/YodaEmbedding/scrobblez",
    author="Mateen Ulhaq",
    author_email="mulhaq2005@gmail.com",
    license="MIT",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    install_requires=[
        "metadata_filter",
        "mpris2",
        "pylast",
        "pyxdg",
    ],
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "scrobblez = scrobblez.__main__:main",
        ],
    },
    zip_safe=False,
)
