#!/bin/sh

#BSUB -J sumo_sim
#BSUB -n 101
#BSUB -q long
#BSUB -W 24:00
#BSUB -e %J.err
#BSUB -R rusage[mem=1024]

source ~/.bashrc

# Path to executable
cd /home/vs57d/siouxfalls_enhanced/scripts

# start a new host file from scratch
SCOOPHOST_FILE=hosts_$LSB_JOBID
rm -f $SCOOPHOST_FILE
touch $SCOOPHOST_FILE
echo "# SCOOP hostfile created by LSF on `date`"
# check if we were able to start writing the conf file
if [ -f $SCOOPHOST_FILE ]; then
    :
else
    echo "$0: can't create $SCOOPHOST_FILE"
    exit 1
fi
HOST=""
NUM_PROC=""
FLAG=""
TOTAL_CPUS=0
for TOKEN in $LSB_MCPU_HOSTS
    do
        if [ -z "$FLAG" ]; then # -z means string is empty
            HOST="$TOKEN"
            FLAG="0"
        else
            NUM_PROC="$TOKEN"
            FLAG="1"
        fi
        if [ "$FLAG" = "1" ]; then
            _x=0
            if [ $_x -lt $NUM_PROC ]; then
                TOTAL_CPUS=`expr "$TOTAL_CPUS" + "$NUM_PROC"`
                echo "$HOST $NUM_PROC" >> $SCOOPHOST_FILE
            fi
            # get ready for the next host
            FLAG=""
            HOST=""
            NUM_PROC=""
        fi
    done
echo "Your SCOOP boot hostfile looks like:"
echo "TOTAL_CPUS: ${TOTAL_CPUS}"
# Python script
script=ga_simulator_scoop.py
# SCOOP command
python3 -m scoop -n 101 -vv --debug --hostfile $SCOOPHOST_FILE $script > testscoop_$LSB_JOBID.stdout.log