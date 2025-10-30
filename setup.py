from setuptools import setup

setup(
    name="melon",
    version="0.1.0",
    py_modules=["melon"],
    entry_points={
        "console_scripts": [
            "melon=melon:main",
        ],
    },
    install_requires=[
        "openai",
        "python-dotenv",
        "rich",
    ],
)