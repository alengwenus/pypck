import setuptools

with open("README.md") as fh:
    long_description = fh.read()

setuptools.setup(
    name="pypck",
    version="0.7.15",
    author="Andre Lengwenus",
    author_email="alengwenus@gmail.com",
    description="LCN-PCK library",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/alengwenus/pypck",
    packages=setuptools.find_packages(exclude=(["tests", "tests.*"])),
    install_requires=[],
    license="MIT",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Home Automation",
    ],
    python_requires=">=3.8",
)
