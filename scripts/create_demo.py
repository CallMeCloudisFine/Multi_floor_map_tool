"""Generate a deterministic three-floor ASCII PCD without third-party dependencies."""
from pathlib import Path
import argparse


def generate(path):
    points = []
    for z in (0.0, 3.0, 6.0):
        for x in range(41):
            for y in range(31):
                points.append((x / 4, y / 4, z))
        for h in range(1, 11):
            for x in range(41):
                points.append((x / 4, 0.0, z + h / 5))
    header = ('VERSION 0.7\nFIELDS x y z\nSIZE 4 4 4\nTYPE F F F\n'
              f'COUNT 1 1 1\nWIDTH {len(points)}\nHEIGHT 1\n'
              f'VIEWPOINT 0 0 0 1 0 0 0\nPOINTS {len(points)}\nDATA ascii\n')
    with Path(path).open('x') as stream:
        stream.write(header)
        stream.writelines(f'{x} {y} {z}\n' for x, y, z in points)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('output', nargs='?', default='demo.pcd')
    generate(parser.parse_args().output)
