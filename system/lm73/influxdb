#! /usr/bin/env bash

data_file="/tmp/lm73.txt"
initial_time=0

while true; do
    sleep 1s

    ### check file was updated
    current_time=$(stat -c %Y ${data_file})
    if [ "${current_time}" -eq "${initial_time}" ]; then
        continue
    fi
    initial_time=${current_time}

    ### update 
    temp=$(cat ${data_file} | awk {'print $2'})
    data="cernia,device=lm73,name=temperature value=${temp}"
    /emmi/influxdb/influx_write.sh "${data}"

done
