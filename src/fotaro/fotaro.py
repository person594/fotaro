"""fotaro.

Usage:
  fotaro.py <data-dir>

"""

from multiprocessing import Process

from docopt import docopt

from server import run_server
from overseer import run_overseer


if __name__ == "__main__":
    args = docopt(__doc__)
    data_dir = args["<data-dir>"]
    p_overseer = Process(target=run_overseer, args=(data_dir,))
    p_overseer.start()
    run_server(data_dir)
