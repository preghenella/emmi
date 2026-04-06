#! /usr/bin/env python

import keithley as ky
import sys
import numpy as np
import matplotlib.pyplot as plt
import datetime
import time

### parse arguments
args = ky.parse_arguments()

### output file run tag
outfiletagname = ky.build_tagname(args)

### start
starttime = time.time()
print('--- Keithley \'zero\' program started: %s' % outfiletagname)

### add time tag
#timenow = datetime.datetime.now()
#timetag = timenow.strftime('%Y%m%d%H%M%S')
#outfiletagname += '.' + timetag

### define plots
plt.ion()
fig, ax = plt.subplots(1, 1, figsize=(5, 5))
ax.set_title('zero volt offset')
ax.set_xlabel('time (s)')
ax.set_ylabel('I (A)')
ax.set_ylim([-2.e-9, 2.e-9])
fig.tight_layout()

### connect and initialize
ky.connect()
ky.initialize()
ky.read_config()

########################
### ZERO VOLT OFFSET ###
########################

### configure source and trigger model
ky.source_measure_config(Vscan = [0.])
ky.trigger_config(Twait = 10., Tstep = 0., Tmeas = 30., Nmeas = 'INF')

### start trigger model and wait
ky.trigger_init()
ky.trigger_wait()

### read measurements
measurements = ky.read_measurements()

### plot measurements
ky.plot_measurements(measurements, 'REL', 'READ', ax, invertX = False, invertY = True);

### write measurements
ky.write_measurements(measurements, outfiletagname + '.zero.csv')

### write commands
ky.write_commands(outfiletagname + '.zero.scpi')

### close connection
ky.close()

### done
endtime = time.time()
print('\a')
print('--- Keithley \'zero\' program completed: %f seconds' % (endtime - starttime))

### wait for plot
print('--- plot is ready and saved: waiting for 5 seconds')
plt.savefig(outfiletagname + '.zero.png')
time.sleep(3)
