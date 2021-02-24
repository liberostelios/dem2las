#!/usr/bin/python3

import sys
import struct
import numpy as np
from numpy import sin, cos, power, sqrt, pi, arange
import gdal
import laspy

band = 1
no_data_value = 0
limit = 10000000

def printProgress (iteration, total, prefix = '', suffix = '', decimals = 1, barLength = 100):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        barLength   - Optional  : character length of bar (Int)
    """
    formatStr       = "{0:." + str(decimals) + "f}"
    percents        = formatStr.format(100 * (iteration / float(total)))
    filledLength    = int(round(barLength * iteration / float(total)))
    bar             = '#' * filledLength + '-' * (barLength - filledLength)
    sys.stdout.write('\r%s |%s| %s%s %s' % (prefix, bar, percents, '%', suffix)),
    if iteration == total:
        sys.stdout.write('\n')
    sys.stdout.flush()

def getActualPoint(lx, ly, transform):
    startx = transform[0]
    starty = transform[3]
    resx = transform[1]
    resy = transform[5]
    rot = transform[2]

    x = startx + lx * cos(rot) * resx + ly * sin(rot) * resy
    y = starty + lx * sin(rot) * resx + ly * cos(rot) * resy

    return x, y

def saveLasFile(xvalues, yvalues, zvalues, classifications, filename):
    print("\nWriting {} points on file {}...".format(len(xvalues), filename))

    hdr = laspy.header.Header()

    outfile = laspy.file.File(filename, mode="w", header=hdr)
    allx = np.array(xvalues)
    ally = np.array(yvalues)
    allz = np.array(zvalues)

    xmin = np.floor(np.min(allx))
    ymin = np.floor(np.min(ally))
    zmin = np.floor(np.min(allz))

    outfile.header.offset = [xmin,ymin,zmin]
    outfile.header.scale = [0.001,0.001,0.001]

    outfile.x = allx
    outfile.y = ally
    outfile.z = allz

    outfile.close()

    print("File saved successfully!")

def main(argv=None):
    if argv is None:
        argv = sys.argv

    gdal.UseExceptions()

    if len(argv) < 3:
        print("Nee! Doesn't work without arguments...")
        print("SYNTAX: python dem2las.py [input_file] [output.las]")
        sys.exit(1)

    input_file = argv[1]
    output_file = argv[2]

    # Get the GDAL dataset
    try:
        src_ds = gdal.Open(input_file)
    except RuntimeError as e:
        print("Unable to open %s" % input_file)
        print(e)
        sys.exit(1)

    if band > src_ds.RasterCount:
        print("Band %i is out of index" % band)
        sys.exit(1)

    # Get the dataset's Trasnform information and the specified band
    srctransform = src_ds.GetGeoTransform()
    srcband = src_ds.GetRasterBand(band)

    print("Band size is {} x {}".format(srcband.XSize, srcband.YSize))

    # Some initialization which makes the main loop more efficient
    xsize = srcband.XSize
    ysize = srcband.YSize

    xvalues = []
    yvalues = []
    zvalues = []

    resx = srctransform[1]
    resy = srctransform[5]
    rot = srctransform[2]

    dx = cos(rot) * resx
    dy = sin(rot) * resx

    file_i = 0

    # Main loop for each scanline
    for y in range(ysize):
        # Get binary data and use struct to convert them into float
        scanline = srcband.ReadRaster(0, y, xsize, 1, xsize, 1, gdal.GDT_Float32)
        values = struct.unpack('f' * xsize, scanline)

        # Generate the Xs and Ys for this scanline
        minx, miny = getActualPoint(0, y, srctransform)
        maxx, maxy = getActualPoint(xsize, y, srctransform)
        if (dx != 0):
            xvals = arange(minx, maxx, dx)
        else:
            xvals = [minx] * xsize

        if (dy != 0):
            yvals = arange(miny, maxy, dy)
        else:
            yvals = [miny] * xsize

        # Those are the elevation values
        zvals = values

        # Clear Xs, Ys and Zs where the GDAL dataset has no value (to save space)
        indices = [i for i in range(len(zvals)) if zvals[i] != no_data_value]
        xvalues.extend([xvals[i] for i in indices])
        yvalues.extend([yvals[i] for i in indices])
        zvalues.extend([zvals[i] for i in indices])

        printProgress(y, ysize, barLength = 50)

        # As soon as we exceed the current limit of points, save the file (in order to save memory space for huge datasets)
        if (len(xvalues) > limit):
            saveLasFile(xvalues, yvalues, zvalues, [], "{}.{}.las".format(output_file, file_i))
            xvalues = []
            yvalues = []
            zvalues = []
            file_i = file_i + 1

    # Save the last one
    saveLasFile(xvalues, yvalues, zvalues, [], "{}.{}.las".format(output_file, file_i))

    print("Done! Thank you for your time. Bye-bye...")

if __name__ == "__main__":
    # execute only if run as a script
    main()