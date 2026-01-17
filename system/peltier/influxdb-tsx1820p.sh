#! /usr/bin/env bash

data_file="/tmp/tsx1820p.txt"
initial_time=0

while true; do
    sleep 1s

    ### check file was updated
    current_time=$(stat -c %Y ${data_file})
    if [ "${current_time}" -eq "${initial_time}" ]; then
        continue
    fi
    initial_time=${current_time}

    vout=$(cat ${data_file} | awk {'print $1'})
    iout=$(cat ${data_file} | awk {'print $2'})
    pout=$(echo "${vout} * ${iout}" | bc)
    data="cernia,device=tsx1820p,name=vout value=${vout}"
    /emmi/influxdb/influx_write.sh "${data}"
    data="cernia,device=tsx1820p,name=iout value=${iout}"
    /emmi/influxdb/influx_write.sh "${data}"
    data="cernia,device=tsx1820p,name=pout value=${pout}"
    /emmi/influxdb/influx_write.sh "${data}"
    sleep 1s
    
done
