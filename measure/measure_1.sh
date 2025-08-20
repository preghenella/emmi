#! /usr/bin/env bash
set -x
set -u

DDIR="/home/eic/DATA/EMMI/preparation"
SDIR="/home/eic/CERNIA/devel"

### defaults

VSLEEP="15s"
TSLEEP="15m"
LSLEEP="15s"

NREPEAT=20
NFRAMES=20
EXPOSURE=5000

XPOSITIONS="88000 94000" ### axis 4
YPOSITIONS="41000 44000 47000 50000 53000" ### axis 5
ZPOSITIONS="92300" ### axis 6

RM=true
LIGHTONLY=false
RUNNAME=$(date +%Y%m%d-%H%M%S)

TEMPS=(17.0 19.0 21.0 23.0)
VBRKS=(51.1 51.2 51.3 51.4) ### breakdown voltage

VOVERS="9"

### hacks

TEMPS=(20.0)
VBRKS=(51.3) ### breakdown voltage

XPOSITIONS="94000"
YPOSITIONS="53000"

NREPEAT=10

VOVERS="5 7 9"

### functions

light_on() {
    /home/eic/CERNIA/keithley/serial-device-cmd.py --device ARDUINO_LIGHT --cmd "ON"
}

light_off() {
    /home/eic/CERNIA/keithley/serial-device-cmd.py --device ARDUINO_LIGHT --cmd "OFF"
}

mcm301_move() {
    axis=$1
    value=$2
    /home/eic/CERNIA/MCM301/mcm301_cmd.py --cmd "move ${axis} ${value}"
    while /home/eic/CERNIA/MCM301/mcm301_cmd.py --cmd "get ${axis}" | grep "moving"; do
        sleep 0.5
    done
    sleep 1
}

mcm301_home() {
    axis=$1
    /home/eic/CERNIA/MCM301/mcm301_cmd.py --cmd "home ${axis}"
    while /home/eic/CERNIA/MCM301/mcm301_cmd.py --cmd "get ${axis}" | grep "moving"; do
        sleep 0.5
    done
    sleep 1
}

vbias_set() {
    VOLT=$1
    echo "V1 ${VOLT};*OPC?" | nc -w1 -W1 10.0.8.10 9221
}

vbias_on() {
    echo "OP1 1;*OPC?" | nc -w1 -W1 10.0.8.10 9221
}

vbias_off() {
    echo "OP1 0;*OPC?" | nc -w1 -W1 10.0.8.10 9221
}

main() {

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
		    [ $RM = true ] && rm ${PEDESTAL}.stack.tif
		
		light_on && sleep ${LSLEEP}
		LIGHT="${PREFIX}_data=light"
		${SDIR}/cernia.py --nframes ${NFRAMES} --exposure 50 --prefix ${LIGHT} --pedestal ${PEDESTAL}.tif && \
		    ${SDIR}/average.py --input ${LIGHT}.stack.tif --output ${LIGHT}.tif --filter && \
		    [ $RM = true ] && rm ${PEDESTAL}.tif ${LIGHT}.stack.tif
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
				[ $RM = true ] && rm ${PEDESTAL}.stack.tif
			    
			    ### dark run
			    echo " --- dark run "
			    DARK="${PREFIX}_data=dark.${I}"
			    ${SDIR}/cernia.py --nframes ${NFRAMES} --exposure ${EXPOSURE} --prefix ${DARK} --pedestal ${PEDESTAL}.tif && \
				${SDIR}/average.py --input ${DARK}.stack.tif --output ${DARK}.tif --filter && \
				[ $RM = true ] && rm ${DARK}.stack.tif
			    
			    ### hot run
			    echo " --- hot run "
			    vbias_on && sleep ${VSLEEP}
			    HOT="${PREFIX}_data=hot.${I}"
			    ${SDIR}/cernia.py --nframes ${NFRAMES} --exposure ${EXPOSURE} --prefix ${HOT} --pedestal ${PEDESTAL}.tif && \
				${SDIR}/average.py --input ${HOT}.stack.tif --output ${HOT}.tif --filter && \
				[ $RM = true ] && rm ${HOT}.stack.tif
			    vbias_off && sleep ${VSLEEP}
			    
			    ### subtract 
			    echo " --- subtract "
			    DIFF="${PREFIX}_data=diff.${I}"
			    ${SDIR}/subtract.py --input1 ${HOT}.tif --input2 ${DARK}.tif --output ${DIFF}.tif && \
				[ $RM = true ] && rm ${PEDESTAL}.tif ${DARK}.tif ${HOT}.tif
			    
			    [ -f ".breakloop" ] && break
			done
			### end of loop over repetitions
			
			### average repetitions
			tiffcp ${PREFIX}_data=diff.???.tif ${PREFIX}_data=diff.stack.tif && \
			    ${SDIR}/average.py --input ${PREFIX}_data=diff.stack.tif \
				   --output ${PREFIX}_data=diff.tif --output_error ${PREFIX}_data=diffe.tif --filter && \
			    [ $RM = true ] && rm ${PREFIX}_data=diff.???.tif ${PREFIX}_data=diff.stack.tif
			
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

}

### create data directory

mkdir -p ${DDIR}/${RUNNAME}

### make a copy of this script to save the actual run conditions

new_name=${RUNNAME}.sh
this_script=$(realpath "$0")
cp ${this_script} ${DDIR}/${RUNNAME}/${RUNNAME}.sh

### call main

cd ${DDIR}/${RUNNAME}
time -p main &> measure_1.log
cd -

