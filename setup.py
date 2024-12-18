from setuptools import setup, find_packages

setup(
    name="marinabox",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "docker",
        "requests",
        "fastapi",
        "uvicorn",
        "click",
        "boto3",
    ],
    entry_points={
        'console_scripts': [
            'marinabox=marinabox.cli:cli',
            'mb=marinabox.cli:cli',
        ],
    },
    author="Your Name",
    description="A container management system for browser automation",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/marinabox",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
)