#!/bin/sh
#python3 /usr/bin/qapplet_threading.py &

#touch /tmp/neco

if [[ -n $GDMSESSION ]]; then
    #touch /tmp/neco_gdm
    python3 /usr/bin/qapplet_threading.py &
fi
