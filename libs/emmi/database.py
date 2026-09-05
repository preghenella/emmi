import glob
import os
#import numpy as np

def convert_string(s: str):
    try:
        return int(s)
    except ValueError:
        pass

    try:
        return float(s)
    except ValueError:
        return s

def build_database(pattern):
    database = []
    files = glob.glob(pattern)
    for f in sorted(files):
        abspath = os.path.abspath(f)
        basename = os.path.basename(f)
        tag, ext = os.path.splitext(basename)
        if ext != '.tif':
            continue
        print(f' --- new database entry: {tag}')
        dbentry = { 'path':abspath }
        fields = tag.split('_')
        for field in fields:
            if '=' not in field:
                continue
            key, value = field.split('=', 1)
            dbentry[key] = convert_string(value)
        database.append(dbentry)
    return database

def build_coordinates(database, coordinate_system="mm"):
    if coordinate_system == "encoder":
        x_vals = sorted({d['x'] for d in database if 'x' in d}, reverse=True)
        y_vals = sorted({d['y'] for d in database if 'y' in d}, reverse=True)
    elif coordinate_system == "mm":
        x_vals = sorted({float(d['x']) for d in database if 'x' in d}, reverse=True)
        y_vals = sorted({float(d['y']) for d in database if 'y' in d}, reverse=True)
    else:
        raise ValueError(f'unknown coordinate_system: {coordinate_system}')
    coords = [ [ (y, x) for x in x_vals ] for y in y_vals ]
    return coords

def get_filename(database, conditions):
    for d in database:
        if all(d[k] == v for k, v in conditions.items()):
            return d['path']
    return None
