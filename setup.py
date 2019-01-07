import setuptools
import os

__here__ = os.path.dirname(__file__)


with open(os.path.join(__here__, "README.md"), "r") as fh:
    long_description = fh.read()


full_requires = ["uvicorn"]
test_requires = ["pytest", "hypothesis", "requests", "pytest-asyncio"]


setuptools.setup(
    name="shallot",
    version="0.1.0",
    author="Peter Peter",
    author_email="dev.peterpeter5@gmail.com",
    description="Fast, small ASGI-compliant webframework",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/peterpeter5/shallot",
    packages=setuptools.find_packages(),
    install_requires=["aiofiles"],
    extras_require={
        "full": full_requires,
        "test":  test_requires + full_requires,
        "docs": ["sphinx", "recommonmark"]
    },
    python_requires=">=3.6",
    classifiers=[
        "Programming Language :: Python :: 3",
    ],
)
