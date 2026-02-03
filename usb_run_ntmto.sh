#!/bin/bash

while true; do
    for d in /media/user/*; do
        if [ -d "$d" ]; then
            echo "USB detected at $d"

            cd /home/user/group-9-team-project-main/red-circle-finder || exit 1

            # clear old images
            rm -f input_images/*

            # copy images from USB commented out, only if there are no subfolders.
            # cp "$d"/*.{jpg,jpeg,png,JPG,JPEG,PNG} input_images/ 2>/dev/null

            #if there are subfolders
            find "$d" -type f \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" \) -print0 
            | xargs -0 -I{} cp "{}" input_images/


            # run the script
            python find_red_circles.py --in_dir input_images --out_dir matched --crop

            echo "Done. Waiting for next USB."
            
            # wait until USB is removed before triggering again
            while [ -d "$d" ]; do
                sleep 1
            done
        fi
    done
    sleep 1
done

#TJP
