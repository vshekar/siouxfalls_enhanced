#!/bin/bash

#BSUB -J sumo_sim
#BSUB -n 1
#BSUB -q long
#BSUB -W 24:00
#BSUB -e %J.err
#BSUB -R rusage[mem=1024]
#BSUB -R select[rh=8]

python leap_run.py