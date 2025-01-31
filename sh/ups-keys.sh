#!/bin/bash

ups=$1
host=$HOSTNAME

if [[ $ups = ups.discovery ]]; then

    echo -e "{\n\t\"data\":["
    first=1
    upsc -l 2>&1 | grep -v SSL | while read discovered ; do
        if [ $first -eq 0 ]; then
            echo -e ","
        fi
        echo -en "\t\t{ \"{#UPSNAME}\":\t\"${discovered}\" }"
        first=0
    done
    echo -e "\n\t]\n}"

else

key=$2

if [[ $key = ups.status ]]; then
        state=`upsc $ups@$host $key 2>&1 | grep -v SSL`
        case "$state" in
                "OL")           echo 1 ;; #'On line (mains is present)' ;;
                "OB")           echo 2 ;; #'On battery' ;;
                "LB")           echo 3 ;; #'Low battery' ;;
                "RB")           echo 4 ;; #'The battery needs to be replaced' ;;
                "CHRG")         echo 5 ;; #'The battery is charging' ;;
                "DISCHRG")      echo 6 ;; #'The battery is discharging (inverter is providing load power)' ;;
                "BYPASS")       echo 7 ;; #'UPS bypass circuit is active echo no battery protection is available' ;;
                "CAL")          echo 8 ;; #'UPS is currently performing runtime calibration (on battery)' ;;
                "OFF")          echo 9 ;; #'UPS is offline and is not supplying power to the load' ;;
                "OVER")         echo 10 ;; #'UPS is overloaded' ;;
                "TRIM")         echo 11 ;; #'UPS is trimming incoming voltage (called "buck" in some hardware)' ;;
                "BOOST")        echo 12 ;; #'UPS is boosting incoming voltage' ;;
                "OL CHRG")      echo 13 ;; #'On battery (mains absent) and the battery is charging' ;;
                * )             echo 0 ;; #'unknown state' ;;
        esac
else
        for upsname in `upsc -l $host 2>&1 | grep -v SSL`; do
            upsc $upsname ups.status 2>&1 | grep -v SSL
        done
fi

fi
