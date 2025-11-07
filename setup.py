from setuptools import setup, find_packages

setup(
    name="pipeplay",
    version="0.1.0",
    description="PipePlay - PipeWire media player for Home Assistant integration",
    packages=find_packages(),
    install_requires=[
        "homeassistant>=2023.11.0",
        "pulsectl>=22.3.2",
        "asyncio-mqtt>=0.13.0",
        "pydbus>=0.6.0",
        "python-mpv>=1.0.4",
        "mutagen>=1.47.0",
        "aiofiles>=23.2.1",
    ],
    python_requires=">=3.9",
    entry_points={
        "console_scripts": [
            "pipeplay=pipeplay.main:main",
        ],
    },
)