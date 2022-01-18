import setuptools

with open("README.md") as fh:
    long_description = fh.read()

setuptools.setup(
    name="pypck",
    version="0.7.13",
    author="Andre Lengwenus",
    author_email="alengwenus@gmail.com",
    description="LCN-PCK library",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/alengwenus/pypck",
    packages=setuptools.find_packages(exclude=(["tests", "tests.*"])),
    install_requires=[],
    license="EPL-2.0",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Eclipse Public License 2.0 (EPL-2.0)",
        "Operating System :: OS Independent",
        "Topic :: Home Automation",
    ],
    python_requires=">=3.8",
)
