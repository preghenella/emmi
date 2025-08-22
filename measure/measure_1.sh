#! /usr/bin/env bash
set -u

DDIR="/home/eic/DATA/EMMI/actual"
SDIR="/home/eic/CERNIA/devel"

### defaults

VSLEEP="15s"
TSLEEP="15m"
LSLEEP="15s"

NREPEAT=25
NFRAMES=20
EXPOSURE=5000

NREPEAT_ALL=25
XPOSITIONS_ALL="90200 96200" ### axis 4
YPOSITIONS_ALL="39500 42500 45500 48500 51500" ### axis 5
ZPOSITIONS_ALL="92600" ### axis 6

NREPEAT_GOLD=50
XPOSITIONS_GOLD="96200" ### axis 4
YPOSITIONS_GOLD="51500" ### axis 5
ZPOSITIONS_GOLD="92600" ### axis 6

POSITIONS=ALL

RMRAW=true
LIGHTONLY=false
TELEGRAM=true
RUNNAME=$(date +%Y%m%d-%H%M%S)

TEMPS=(17.0 19.0 21.0 23.0)
VBRKS=(51.1 51.2 51.3 51.4) ### breakdown voltage

VOVERS="9"

### externals

VOVERS=${EMMI_VOVERS:-$VOVERS}

POSITIONS=${EMMI_POSITIONS:-$POSITIONS}
for VAR in XPOSITIONS YPOSITIONS ZPOSITIONS NREPEAT; do
    SRC="${VAR}_${POSITIONS}"
    eval "$VAR=\"\${$SRC}\""
done

NREPEAT=${EMMI_NREPEAT:-$NREPEAT}
LIGHTONLY=${EMMI_LIGHTONLY:-$LIGHTONLY}
RMRAW=${EMMI_RMRAW:-$RMRAW}

### hacks

TEMPS=(20.0)
VBRKS=(51.3) ### breakdown voltage

### splash

splash() {

    echo " --------------------- "
    echo " EMMI MEASURE_1 SCRIPT "
    echo " --------------------- "
    echo
    echo " EXPOSURE: ${EXPOSURE} "
    echo " NFRAMES: ${NFRAMES} "
    echo
    echo " XPOSITIONS: ${XPOSITIONS} "
    echo " YPOSITIONS: ${YPOSITIONS} "
    echo " ZPOSITIONS: ${ZPOSITIONS} "
    echo
    echo " TEMPS: ${TEMPS} "
    echo " VBRKS: ${VBRKS} "
    echo " VOVERS: ${VOVERS} "
    echo
    echo " NREPEAT: ${NREPEAT} "
    echo
    echo " LIGHTONLY: ${LIGHTONLY} "
    echo " RMRAW: ${RMRAW} "
    echo 
    
}

### functions

telegram_message() {
    msg=$1
    telegram_message.sh "EMMI -- ${msg}"
}

telegram_image() {
    tif=$1
    /emmi/tools/display-image.py --input ${tif} --output /tmp/emmi.png &> /dev/null
    telegram_picture.sh /tmp/emmi.png "EMMI -- ${tif}"
}

dump_keithley() {

    data_file="/tmp/keithley.txt"
    initial_time=0
    
    while true; do
	sleep 0.1
	
	### check file was updated
	current_time=$(stat -c %Y ${data_file})
	if [ "${current_time}" -eq "${initial_time}" ]; then
            continue
	fi
	initial_time=${current_time}
	
	### update 
	curr=$(cat ${data_file} | awk {'print $1'})
	curr=${curr#"+"}
	
	data="${current_time} ${curr}"
	echo ${data}
	
    done
    
}

light_on() {
    echo " --- light on "
    /home/eic/CERNIA/keithley/serial-device-cmd.py --device ARDUINO_LIGHT --cmd "ON" &> /dev/null
}

light_off() {
    echo " --- light off "
    /home/eic/CERNIA/keithley/serial-device-cmd.py --device ARDUINO_LIGHT --cmd "OFF" &> /dev/null
}

mcm301_move() {
    axis=$1
    value=$2
    echo " --- moving axis ${axis} to ${value} "
    /home/eic/CERNIA/MCM301/mcm301_cmd.py --cmd "move ${axis} ${value}" &> /dev/null
    while /home/eic/CERNIA/MCM301/mcm301_cmd.py --cmd "get ${axis}" | grep "moving"; do
        sleep 0.5
    done &> /dev/null
    sleep 1
}

mcm301_home() {
    axis=$1
    echo " --- moving axis ${axis} to home "
    /home/eic/CERNIA/MCM301/mcm301_cmd.py --cmd "home ${axis}" &> /dev/null
    while /home/eic/CERNIA/MCM301/mcm301_cmd.py --cmd "get ${axis}" | grep "moving"; do
        sleep 0.5
    done &> /dev/null
    sleep 1
}

vbias_set() {
    VOLT=$1
    echo " --- vbias set to ${VOLT} "
    echo "V1 ${VOLT};*OPC?" | nc -w1 -W1 10.0.8.10 9221 &> /dev/null
}

vbias_on() {
    echo " --- vbias on "
    echo "OP1 1;*OPC?" | nc -w1 -W1 10.0.8.10 9221 &> /dev/null
}

vbias_off() {
    echo " --- vbias off "
    echo "OP1 0;*OPC?" | nc -w1 -W1 10.0.8.10 9221 &> /dev/null
}

main() {

    ### splash
    splash
    
    ### create RAW directory if needed
    [ $RMRAW = true ] || mkdir RAW
    
    ### make sure to start in an OFF state
    vbias_off && sleep ${VSLEEP}
    light_off && sleep ${LSLEEP}

    ### home
    mcm301_home 4
    mcm301_home 5
    mcm301_home 6

    ### loop over x positions
    for XPOS in ${XPOSITIONS}; do
	mcm301_move 4 ${XPOS} && sleep 1s
	
	### loop over y positions
	for YPOS in ${YPOSITIONS}; do
	    mcm301_move 5 ${YPOS} && sleep 1s
	    
	    ### loop over z positions
	    for ZPOS in ${ZPOSITIONS}; do
		mcm301_move 6 ${ZPOS} && sleep 1s

		### get a picture with light on
		echo " --- pedestal run "
		PREFIX="run=${RUNNAME}_x=${XPOS}_y=${YPOS}_z=${ZPOS}"
		PEDESTAL="${PREFIX}_data=light-pedestal"
		${SDIR}/cernia.py --nframes ${NFRAMES} --exposure 0.029 --prefix ${PEDESTAL} && \
		    ${SDIR}/average.py --input ${PEDESTAL}.stack.tif --output ${PEDESTAL}.tif --filter && \
		    rm ${PEDESTAL}.stack.tif
		
		light_on && sleep ${LSLEEP}
		LIGHT="${PREFIX}_data=light"
		${SDIR}/cernia.py --nframes ${NFRAMES} --exposure 50 --prefix ${LIGHT} --pedestal ${PEDESTAL}.tif && \
		    ${SDIR}/average.py --input ${LIGHT}.stack.tif --output ${LIGHT}.tif --filter && \
		    rm ${PEDESTAL}.tif ${LIGHT}.stack.tif
		[ $TELEGRAM = true ] && telegram_image ${LIGHT}.tif 
		light_off && sleep ${LSLEEP}
		
		[ ${LIGHTONLY} = true ] && continue
				
		### loop over temperature
		for i in "${!TEMPS[@]}"; do
		    TEMP="${TEMPS[$i]}"
		    VBRK="${VBRKS[$i]}"

		    /home/eic/CERNIA/peltier/update-tset.sh ${TEMP} && sleep ${TSLEEP}

		    ### loop over overvoltages
		    for VOVER in ${VOVERS}; do

			VOLT=$(echo "scale=1; ${VBRK} + ${VOVER}" | bc -l)
			vbias_set ${VOLT}
		    
			### get ready to measure
			PREFIX="run=${RUNNAME}_x=${XPOS}_y=${YPOS}_z=${ZPOS}_T=${TEMP}_v=${VOLT}"
			REPEAT=$(seq -f "%03.0f" 0 $((NREPEAT - 1)))
			
			### loop over repetitions
			for I in ${REPEAT}; do
			    
			    ### pedestal run
			    echo " --- pedestal run "
			    PEDESTAL="${PREFIX}_data=pedestal.${I}"
			    ${SDIR}/cernia.py --nframes ${NFRAMES} --exposure 0.029 --prefix ${PEDESTAL} && \
				${SDIR}/average.py --input ${PEDESTAL}.stack.tif --output ${PEDESTAL}.tif --filter && \
				rm ${PEDESTAL}.stack.tif
			    
			    ### dark run
			    echo " --- dark run "
			    DARK="${PREFIX}_data=dark.${I}"
			    ${SDIR}/cernia.py --nframes ${NFRAMES} --exposure ${EXPOSURE} --prefix ${DARK} --pedestal ${PEDESTAL}.tif && \
				${SDIR}/average.py --input ${DARK}.stack.tif --output ${DARK}.tif --filter && \
				[ $RMRAW = true ] && rm ${DARK}.stack.tif || mv ${DARK}.stack.tif RAW/.
			    
			    ### hot run
			    echo " --- hot run "
			    vbias_on && sleep ${VSLEEP}
			    HOT="${PREFIX}_data=hot.${I}"
			    dump_keithley > ${HOT}.keithley & KYPID=$!
			    ${SDIR}/cernia.py --nframes ${NFRAMES} --exposure ${EXPOSURE} --prefix ${HOT} --pedestal ${PEDESTAL}.tif && \
				${SDIR}/average.py --input ${HOT}.stack.tif --output ${HOT}.tif --filter && \
				[ $RMRAW = true ] && rm ${HOT}.stack.tif || mv ${HOT}.stack.tif RAW/.
			    kill ${KYPID}
			    vbias_off && sleep ${VSLEEP}
			    
			    ### subtract 
			    echo " --- subtract "
			    DIFF="${PREFIX}_data=diff.${I}"
			    ${SDIR}/subtract.py --input1 ${HOT}.tif --input2 ${DARK}.tif --output ${DIFF}.tif && \
				rm ${DARK}.tif ${HOT}.tif && \
				[ $RMRAW = true ] && rm ${PEDESTAL}.tif || mv ${PEDESTAL}.tif RAW/.
			    
			    [ -f ".breakloop" ] && break
			done
			### end of loop over repetitions
			
			### average repetitions
			DIFF=${PREFIX}_data=diff
			DIFFE=${PREFIX}_data=diffe
			tiffcp ${DIFF}.???.tif ${DIFF}.stack.tif && \
			    ${SDIR}/average.py --input ${DIFF}.stack.tif \
				   --output ${DIFF}.tif --output_error ${DIFFE}.tif --filter && \
			    rm ${DIFF}.???.tif ${DIFF}.stack.tif
			[ $TELEGRAM = true ] && telegram_image ${DIFF}.tif 

			### concatenate keithley
			cat ${PREFIX}_data=hot.???.keithley > ${PREFIX}_data=hot.keithley && \
			    [ $RMRAW = true ] && rm ${PREFIX}_data=hot.???.keithley || mv ${PREFIX}_data=hot.???.keithley RAW/.
			
			[ -f ".breakloop" ] && break		    
		    done
		    ### end of loop over overvoltages
		    
		    [ -f ".breakloop" ] && break		    
		done
		### loop over temperatures
		
		[ -f ".breakloop" ] && break		    
	    done
	    ### end of loop over z positions
	    
	    [ -f ".breakloop" ] && break		    
	done
	### end of loop over y positions
	
	[ -f ".breakloop" ] && break		    
    done
    ### end of loop over x positions

    ### create RAW tarball 
    [ $RMRAW = true ] || tar zcvf RAW.tgz RAW
    
    echo " --- all done, so long "
    
}

### create data directory

mkdir -p ${DDIR}/${RUNNAME}

### make a copy of this script to save the actual run conditions

new_name=${RUNNAME}.sh
this_script=$(realpath "$0")
cp ${this_script} ${DDIR}/${RUNNAME}/.

### call main

cd ${DDIR}/${RUNNAME}
echo " --- starting new run: ${RUNNAME} "
echo "     running from ${PWD} "
telegram_message "starting new run: ${RUNNAME}"
telegram_message "running from ${PWD}"
{ time -p main; } &> measure_1.log
telegram_message "run completed: ${RUNNAME}"
cd -

