"""fotaro.

Usage:
  fotaro make <data-dir>
  fotaro serve <data-dir>
  fotaro daemon <data-dir>
"""

from multiprocessing import Process

from docopt import docopt

from .fotaro import Fotaro

from .server import run_server


def _main():
    args = docopt(__doc__)
    data_dir = args["<data-dir>"]
    if args["make"]:
        Fotaro.make(data_dir)
    elif args["serve"]:
        run_server(data_dir)
    elif args["daemon"]:
        fo = Fotaro(data_dir)
        fo.run_daemon()


if __name__ == "__main__":
    _main()
