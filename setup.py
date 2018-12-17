import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="pypck",
    version="0.5.7",
    author="Andre Lengwenus",
    author_email="alengwenus@gmail.com",
    description="LCN-PCK library",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/alengwenus/pypck",
    packages=setuptools.find_packages(),
    install_requires=['aenum'],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Eclipse Public License 1.0 (EPL-1.0)",
        "Operating System :: OS Independent",
        "Topic :: Home Automation"
    ],
)