import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="enlighten-croedig", # Replace with your own username
    version="0.1.0",
    author="Christoph A. Roedig",
    author_email="chris@roedig.us",
    description="Simple API client to easily extract data from Enphase Enlighten",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/chrisroedig/sampleproject",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)