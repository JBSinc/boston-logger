import os

from setuptools import setup

CURDIR = os.path.abspath(os.path.dirname(__file__))
PACKAGE_PATH = "boston_logger"

with open(os.path.join(CURDIR, "README.md")) as readme:
    README = readme.read()

test_requires = [
    "pytest",
    "pytest-coverage",
    "pytest-mock",
    "python-dateutil",
]

TOX_ENV = os.environ.get("TOX_ENV_NAME", "django22")  # Added in tox 3.4
if "django20" in TOX_ENV:
    test_requires.append("Django>=2.0,<2.1")
elif "django21" in TOX_ENV:
    test_requires.append("Django>=2.1,<2.2")
elif "django30" in TOX_ENV:
    test_requires.append("Django>=3.0,<3.1")
elif "django31" in TOX_ENV:
    test_requires.append("Django>=3.1,<3.2")
elif "django32" in TOX_ENV:
    test_requires.append("Django>=3.2,<3.3")
elif "django40" in TOX_ENV:
    test_requires.append("Django>=4.0,<4.1")
elif "django41" in TOX_ENV:
    test_requires.append("Django>=4.1,<4.2")
else:
    # Default to the regular requirements
    test_requires.append("Django>=2.2,<5")


setup(
    name="boston-logger",
    packages=[PACKAGE_PATH],
    author="Aaron McMillin",
    author_email="AMcMillin@jbssolutions.com",
    long_description=README,
    long_description_content_type="text/markdown",
    # For a list of valid classifiers, see https://pypi.org/classifiers/
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: System :: Logging",
        "License :: OSI Approved :: ISC License (ISCL)",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3 :: Only",
    ],
    python_requires=">=3.7, <4",
    install_requires=[
        "requests >= 2.18.0",
        "configular >= 1.1.0",
    ],
    extras_require={
        "django": ["Django >= 1.10"],
        "test": test_requires,
    },
    project_urls={"Source": "https://github.com/JBSinc/boston-logger"},
    use_scm_version={
        # PyPi doesn't allow local versions
        "local_scheme": "no-local-version",
    },
    setup_requires=["setuptools_scm"],
)
