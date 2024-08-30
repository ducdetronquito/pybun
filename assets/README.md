Bun PyPI distribution
=====================

[Bun](https://bun.sh/) is an all-in-one toolkit for JavaScript and TypeScript apps.
The [pybun](https://pypi.org/project/pybun/) Python package redistributes the Bun CLI executable so that it can be used as a dependency in your Python projects.


Usage
-----

To run the Bun CLI from the command line, you can use:

```shell
pybun --version
bun --version
python -m pybun --version
```

To run the Bun CLI from a Python program, use `sys.executable` to locate the Python binary to invoke. For example:

```python
import sys, subprocess

subprocess.call([sys.executable, "-m", "pybun"])
```

License
-------

The [Bun license](https://bun.sh/docs/project/licensing).
