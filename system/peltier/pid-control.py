#! /usr/bin/env python

import signal
import time

### TSX1820p

import socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_address = ('10.0.8.11', 9221)

def connect():
    sock.connect(server_address)

def close():
    sock.close()

def send(cmd):
    cmd += '\n'
    sock.send(cmd.encode())

def recv():
  data = sock.recv(4096)
  data = data.decode()
  while data[-1] != '\n':
    data += sock.recv(4096)
  return data.strip()

def ask(cmd):
    send(cmd)
    return recv()

def get_current():
    return float(ask('I1O?')[:-1])

def get_voltage():
    return float(ask('V1O?')[:-1])

def update_current(current):
    send(f'I1 {current}')

### LM73

def get_temperature():
    with open('/tmp/lm73.txt', 'r') as file:
        content = file.read()
    content = content.split()
    if len(content) != 3:
        return None
    temperature = content[1]
    try:
        return float(temperature)
    except (ValueError, IndexError):
        return None

### register signals

def signal_handler(signum, frame):
    print(f"Received signal {signum}, shutting down...")
    send('OP1 0')
    send('I1 0.01')
    exit(0)

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

### main program

connect()
print(' --- TCP device opened: 10.0.8.11/9221 ')
send('OP1 0')
send('I1 0.01')
send('V1 12')
send('OP1 1')

from simple_pid import PID
pid = PID(-0.05, -0.005, -0.05, setpoint = 20.)
pid.output_limits = (0.01, 1.)
pid.sample_time = 3.
pid.auto_mode = False

current = get_current()
pid.set_auto_mode(True, last_output = current)

while True:
    time.sleep(1)

    ### update PID parameters from file
    ### setpoint, min, max, p, i, d
    with open('/emmi/system/peltier/pid-control.conf') as f:
        for line in f:
            line = line.strip()
            if line.startswith("#") or not line:
                continue
            setpoint, Imin, Imax, P, I, D = map(float, line.split())
#            print(setpoint, Imin, Imax, P, I, D)
            pid.setpoint = setpoint
            pid.tunings = (P, I, D)
            pid.output_limits = (Imin, Imax)

    v = get_temperature()
    if v is None:
        continue
    control = pid(v)
    if control is None:
        continue
    control = round(control, 2)
    update_current(control);

    ### write on file the values of the power supply
    voltage = get_voltage()
    current = get_current()
    with open('/tmp/tsx1820p.txt', 'w') as file:
        file.write(f'{voltage} {current}\n')


    
close()

