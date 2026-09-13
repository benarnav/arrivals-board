"""Assemble a drive-ready folder for one city:  python3 pack.py nyc-MTA

Copies everything CIRCUITPY needs into dist/<city>/: the city's code.py, city.py and
data module, the shared modules from common/, the fonts the code loads and the img
folder. Drag the folder's contents to the root of the drive, keeping your secrets.py
and lib/ in place.
"""
import os
import shutil
import sys

SHARED = ["common/arrivals_board.py", "common/feeds.py"]
CITIES = {
    "nyc-MTA": ["mta.py", "common/gtfsrt.py"],
    "washdc-WMATA": ["wmata.py", "common/gtfsrt.py"],
    "sf-BART": ["bart.py", "gtsr4.pem"],
}
FONTS = ["helvR14.bdf", "helvR10.bdf", "helv-9.bdf"]


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in CITIES:
        print("usage: python3 pack.py " + "|".join(CITIES))
        sys.exit(2)
    city = sys.argv[1]
    root = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(root, "dist", city)
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(out)
    for path in ["code.py", "city.py"] + CITIES[city] + SHARED:
        source = os.path.join(root, path) if "/" in path else os.path.join(root, city, path)
        shutil.copy(source, os.path.join(out, os.path.basename(path)))
    shutil.copytree(os.path.join(root, city, "img"), os.path.join(out, "img"))
    os.makedirs(os.path.join(out, "fonts"))
    for font in FONTS:
        shutil.copy(os.path.join(root, "fonts", font), os.path.join(out, "fonts", font))
    print("ready:", os.path.relpath(out, root))
    for name in sorted(os.listdir(out)):
        print("  ", name)


if __name__ == "__main__":
    main()
