import socket
import numpy as np
import os
import matplotlib.pyplot as plt
import argparse
import time

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_address = ('keithley-2450', 5025)
idn_tag_bo = "KEITHLEY INSTRUMENTS,MODEL 2450,04474830,1.6.7c"
idn_tag_bo = "KEITHLEY INSTRUMENTS,MODEL 2450,04474830,1.7.16a"
idn_tag_cs = "KEITHLEY INSTRUMENTS,MODEL 2450,04596335,1.7.12b"
idn_tag_carla = "KEITHLEY INSTRUMENTS,MODEL 2450,04658538,1.7.12b"

echo = False
log = True
commands = []

def parse_arguments():
    
    ### choices 
    boards = ['SENSL', 'BCOM', 'FBK', 'HAMA1', 'HAMA2', 'HAMA3']
    temperatures = [293, 283, 273, 263, 253, 243]
    channels = [row + column
                for row in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
                for column in ['1', '2', '3', '4']]
    open_channels = ['OPEN-' + row + column
                     for row in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
                     for column in ['1', '2', '3', '4']]
    channels.append('OPEN')
    for ch in open_channels:
        channels.append(ch)

    ### arguments
    parser = argparse.ArgumentParser(description='Keithley ivscan program',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('--board',
                        type=str,
                        required=True,
                        choices=boards,
                        help='Board name')
    
    parser.add_argument('--serial',
                        type=int,
                        required=True,
                        help='Board serial number')
    
#    parser.add_argument('--temperature',
#                        type=int,
#                        required=True,
#                        choices=temperatures,
#                        help='Temperature in Kelvin')
    
    parser.add_argument('--temperature',
                        type=int,
                        required=True,
                        help='Temperature in Kelvin')
    
    parser.add_argument('--channel',
                        type=str,
                        required=True,
                        choices=channels,
                        help='Board channel')
    
    parser.add_argument('--notes',
                        type=str,
                        required=False,
                        default=None,
                        action='append',
                        nargs='+',
                        help='Additional notes')
    
    parser.add_argument('--nmeas',
                        type=int,
                        required=False,
                        default=9,
                        help='Number of measurements')
    
    parser.add_argument('--twait',
                        type=float,
                        required=False,
                        default=30.,
                        help='Initial waiting time')
    
    parser.add_argument('--tstep',
                        type=float,
                        required=False,
                        default=0.5,
                        help='Step waiting time')
    
    parser.add_argument('--vstep',
                        type=float,
                        required=False,
                        default=0.200,
                        help='Voltage step')
    
    parser.add_argument('--vbelow',
                        type=float,
                        required=False,
                        default=2.,
                        help='Start below predicted Vbd')
    
    parser.add_argument('--vabove',
                        type=float,
                        required=False,
                        default=15.,
                        help='Stop above predicted Vbd')
    
    args = parser.parse_args()

    return args

def build_tagname(args):
    tagname = args.board
    tagname += '_sn' + str(args.serial)
    tagname += '_' + str(args.temperature) + 'K'
    tagname += '_' + args.channel
    if args.notes is not None:
        for notes in args.notes:
            for note in notes:
                tagname += '_' + note
    return tagname

def connect():
    sock.connect(server_address)

def close():
    send('*RST')
    time.sleep(1)
    send('ABORT')
    sock.close()

def simple_close():
    sock.close()

def write_commands(filename):
    fout = open(filename, 'w')
    for cmd in commands:
        fout.write('%s \n' % (cmd))
    fout.close()
    print('--- commands written to file: {filename}'.format(filename = filename))
    
def send(command):
    if log:
        commands.append(command)
    if echo:
        print (command)
    command += '\n'
    sock.send(command.encode())

def recv():
    data = sock.recv(4096).decode()
    while data[-1] != '\n':
        data += sock.recv(4096).decode()
    return data.strip()
        
def initialize():
    send('ABORT')
    send('*RST')
    send('STAT:CLE')
    send('SYST:CLE')
    send('*IDN?')
    data = recv()
    print(data)
    while data != idn_tag_bo and data != idn_tag_cs and data != idn_tag_carla:
        print('receiving')
        data = recv()
        time.sleep(1)
    print('--- instrument initialised: %s ' % data)

def read_config(filename = 'config.keithley'):
    print("--- read configuration from file: %s" % filename)
    for line in open(filename):
        li = line.strip()
        if len(li) == 0 or li.startswith("#"):
            continue
        send(line.strip())

def output_on():
    send('OUTP:STAT ON')

def output_off():
    send('OUTP:STAT OFF')
            
def set_voltage(V):
    send('SOUR:VOLT:LEV {V}'.format(V = V))

def measure(n):
    send('TRAC:CLEAR')
    send('SENS:COUN {n}'.format(n = n))
    send('TRAC:TRIG')
    send('TRAC:DATA? 1, {n}, \"defbuffer1\", READ'.format(n = n))

def write_measurements(measurements, filename, ioflags = 'w'):
    fout = open(filename, ioflags)
    if os.stat(filename).st_size == 0:
        fout.write('# timestamp , source voltage , measured current , status , source status \n')
    for meas in measurements:
        fout.write('%f %e %e %s %s \n' % (meas['SEC'] + meas['FRAC'], meas['SOUR'], meas['READ'], meas['STAT'], meas['SOURSTAT']))
    fout.close()
    print('--- measurements written to file: {filename}'.format(filename = filename))
    
def read_measurements():
    send('TRAC:ACT?')
    n = int(recv())
    print('--- reading measurements: there are %d points in the buffer' % n)
    if n == 0:
        return []
    send('TRAC:DATA? 1, {n}, \"defbuffer1\", SEC, FRAC, REL, SOUR, READ, STAT, SOURSTAT'.format(n = n))
    data = recv().split(',')
    return [{ 'SEC'      : int(data[i]),
              'FRAC'     : float(data[i+1]),
              'REL'      : float(data[i+2]),
              'SOUR'     : float(data[i+3]),
              'READ'     : float(data[i+4]),
              'STAT'     : data[i+5],
              'SOURSTAT' : data[i+6]}
            for i in range(0, len(data), 7)]

def plot_measurements(measurements, xkey, ykey, ax, invertX = False, invertY = False):

    xval = []
    yval = []
    for meas in measurements:
        xval.append(meas[xkey])
        yval.append(meas[ykey])
    if invertX:
        xval = [-x for x in xval]
    if invertY:
        yval = [-x for x in yval]
    ax.scatter(xval, yval)
    plt.grid()
    plt.draw()
    plt.pause(0.1)

def source_measure_config(Vscan, Ilim = 25.e-6, reverse = False, Vsmart = None, Naver = 4, verbose = False):
    print('--- configuring the source and measure list: Vsmart = {Vsmart}, Naver = {Naver}'.format(Vsmart = Vsmart, Naver = Naver))
    
    send('SOUR:CONF:LIST:CRE \"SOURCE_CONFIG\"')
    send('SENS:CONF:LIST:CRE \"MEASURE_CONFIG\"')

    send('SOUR:VOLT:ILIM {Ilim}'.format(Ilim = Ilim))
    
    for V in Vscan:
        V = round(V, 3)
        ### source config
        if reverse:
            send('SOUR:VOLT:LEV {V}'.format(V = -V))
        else:
            send('SOUR:VOLT:LEV {V}'.format(V = V))
        send('SOUR:CONF:LIST:STOR \"SOURCE_CONFIG\"')
        ### measure config
        if Vsmart is None or V < Vsmart[0] or V > Vsmart[1]:
            send('SENS:CURR:AVER:COUNT 1')
        else:
            send('SENS:CURR:AVER:COUNT {Naver}'.format(Naver = Naver))
        send('SENS:CONF:LIST:STOR \"MEASURE_CONFIG\"')

    if (verbose):
        query_source_config(name)
        
def query_source_config(name):
    send('SOUR:CONF:LIST:SIZE? \"{name}\"'.format(name = name))
    npoints = int(recv())
    print('--- source list configuration list')
    for point in range(1, npoints + 1):
        send('SOUR:CONF:LIST:QUER? \"{name}\", {point}'.format(name = name, point = point))
        print('--- source configuration for point #{point}'.format(point = point))
        for conf in recv().split(','):
            print(conf)
                
def trigger_init():
    print('--- starting the trigger model')
    send('INIT')

def trigger_wait():
    print('--- waiting for the trigger model to terminate')
    send('*WAI')
                
def trigger_config(Twait = 60., Tstep = 1., Tmeas = 1., Nmeas = 'INF', name = 'SOURCE_CONFIG', verbose = False):
    print('--- configuring the trigger model: Twait = {Twait}, Tstep = {Tstep}, Tmeas = {Tmeas}, Nmeas = {Nmeas}'.format(Twait = Twait, Tstep = Tstep, Tmeas = Tmeas, Nmeas = Nmeas))
    
    ### retrive size of source configuration list
    send('SOUR:CONF:LIST:SIZE? \"{name}\"'.format(name = name))
    npoints = int(recv())

    ### configure the trigger model
    send('TRIG:LOAD \"EMPTY\"')
    send('TRIG:BLOC:BUFF:CLEAR 1, \"defbuffer1\"')
    send('TRIG:BLOC:CONF:REC 2, \"SOURCE_CONFIG\", 1')
    send('TRIG:BLOC:CONF:REC 3, \"MEASURE_CONFIG\", 1')
    send('TRIG:BLOC:SOUR:STAT 4, ON')
    send('TRIG:BLOC:MEAS 5, \"defbuffer1\", INF')
    send('TRIG:BLOC:DEL:CONS 6, {Twait}'.format(Twait = Twait))
    send('TRIG:BLOC:MEAS 7, \"defbuffer1\", 0')
#    send('TRIG:BLOC:NOP 8')
    send('TRIG:BLOC:BUFF:CLEAR 8, \"defbuffer1\"')
    send('TRIG:BLOC:BRAN:ALW 9, 13')
    send('TRIG:BLOC:CONF:NEXT 10, \"SOURCE_CONFIG\"')
    send('TRIG:BLOC:CONF:NEXT 11, \"MEASURE_CONFIG\"')
    send('TRIG:BLOC:DEL:CONS 12, {Tstep}'.format(Tstep = Tstep))
    send('TRIG:BLOC:BRAN:EVEN 13, SLIM, 20')
    send('TRIG:BLOC:MEAS 14, \"defbuffer1\", {Nmeas}'.format(Nmeas = Nmeas))
    send('TRIG:BLOC:DEL:CONS 15, {Tmeas}'.format(Tmeas = Tmeas))
    send('TRIG:BLOC:MEAS 16, \"defbuffer1\", 0')
    send('TRIG:BLOC:BRAN:COUN 17, {npoints}, 10'.format(npoints = npoints))
    send('TRIG:BLOC:SOUR:STAT 18, OFF')
    send('TRIG:BLOC:BRAN:ALW 19, 0')
    send('TRIG:BLOC:SOUR:STAT 20, OFF')

    ### print the setting of the trigger model
    if (verbose):
        query_trigger_config()

    return


    send('SENS:CONF:LIST:CRE \"MEASURE_CONFIG\"')

    send('SENS:CURR:AVER:COUNT 10')
    send('SENS:CURR:AVER:TCON REP')
    send('SENS:CURR:AVER ON')
    send('SENS:CONF:LIST:STOR \"MEASURE_CONFIG\"')

    send('SENS:CURR:AVER:COUNT 10')
    send('SENS:CURR:AVER:TCON REP')
    send('SENS:CURR:AVER OFF')
    send('SENS:CONF:LIST:STOR \"MEASURE_CONFIG\"')


    ### configure the trigger model
    ##### initialisation blocks
    send('TRIG:LOAD \"EMPTY\"')
    send('TRIG:BLOC:BUFF:CLEAR 1, \"defbuffer1\"')
    send('TRIG:BLOC:CONF:REC 2, \"SOURCE_CONFIG\", 1')
    send('TRIG:BLOC:CONF:REC 3, \"MEASURE_CONFIG\", 1')
    send('TRIG:BLOC:SOUR:STAT 4, ON')
    send('TRIG:BLOC:BRAN:COUN:RES 5, 8')
    send('TRIG:BLOC:MEAS 6, \"defbuffer1\"')
    send('TRIG:BLOC:BRAN:DELT 7, 1.e9, 9, 6')
    send('TRIG:BLOC:BRAN:COUN 8, 1, 5')
    send('TRIG:BLOC:CONF:REC 9, \"MEASURE_CONFIG\", 2')
    send('TRIG:BLOC:BRAN:ALW 10, 12')
    ### measurement blocks
    send('TRIG:BLOC:CONF:NEXT 11, \"{name}\"'.format(name = name))
    send('TRIG:BLOC:BRAN:EVEN 12, SLIM, 19')
    send('TRIG:BLOC:MEAS 13, \"defbuffer1\", INF')
    send('TRIG:BLOC:DEL:CONS 14, {Tmeas}'.format(Tmeas = Tmeas))
    send('TRIG:BLOC:MEAS 15, \"defbuffer1\", 0')
    send('TRIG:BLOC:BRAN:COUN 16, {npoints}, 11'.format(npoints = npoints))
    send('TRIG:BLOC:SOUR:STAT 17, OFF')
    send('TRIG:BLOC:BRAN:ALW 18, 0')
    send('TRIG:BLOC:SOUR:STAT 19, OFF')

    ### print the setting of the trigger model
    print('--- configuration list of the trigger model')
    send('TRIG:BLOC:LIST?')
    print(recv())

def query_trigger_config():
    print('--- configuration list of the trigger model')
    send('TRIG:BLOC:LIST?')
    print(recv())
    
