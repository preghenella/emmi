#! /usr/bin/env bash

if [ $# -ne 1 ]; then
    echo " usage: $0 [tset] "
    exit 1
fi
tset=$1

cat <<EOF > /emmi/system/peltier/pid-control.conf
# tset	Imin	Imax	P	I	D
${tset}	0.01	1.5	-0.1 	-0.01	-0.1
EOF
