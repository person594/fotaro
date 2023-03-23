"""fotaro.

Usage:
  fotaro make <data-dir>
  fotaro run <data-dir>
"""

from multiprocessing import Process

from docopt import docopt

from .fotaro import Fotaro


def _main():
    args = docopt(__doc__)
    data_dir = args["<data-dir>"]
    if args["make"]:
        Fotaro.make(data_dir)
    elif args["run"]:
        fo = Fotaro(data_dir)
        fo.run()


if __name__ == "__main__":
    _main()
