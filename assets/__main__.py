# pyright: basic
import os
import sys


def main():
    argv = [os.path.join(os.path.dirname(__file__), "bun"), *sys.argv[1:]]

    if os.name == "posix":
        os.execv(argv[0], argv)
    else:
        import subprocess

        sys.exit(subprocess.call(argv))


if __name__ == "__main__":
    main()
