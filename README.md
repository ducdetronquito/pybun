# Pybun

**The bun toolkit, packaged for Python** 🍞 + 🐍 = 🚀


[Bun](https://bun.sh/) is an all-in-one toolkit for JavaScript and TypeScript apps.
The [pybun](https://pypi.org/project/pybun/) Python package redistributes the Bun executable so that it can be used as a dependency in your Python projects.


Usage
-----

### Command line

```shell
pybun --version
```

### Run library module as a script

```shell
python -m pybun --version
```

### From python

```python
import sys, subprocess

subprocess.call([sys.executable, "-m", "pybun"])
```

License
-------

Pybun itself is released under [The Unlicense](https://choosealicense.com/licenses/unlicense/) license.

The bun executable [has its own licence](https://bun.sh/docs/project/licensing).


Credits
-------

Thanks a lot to the [zig-pypi](https://github.com/ziglang/zig-pypi) maintainers: their code heavily helped me to understand how to do the same with Bun!
