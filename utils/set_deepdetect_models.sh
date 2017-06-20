#!/bin/bash
cd ../
full_path=`pwd`
for dir in `find models -type d`
do
    dir=${dir%*/}
    nb_classes=`wc -l $dir/corresp.txt|sed 's/\([^ ]\+\) .*/\1/g'`
    echo ${full_path}/${dir##*/}
    echo $nb_classes
    curl -X DELETE "http://localhost:8080/services/$dir"
    curl -X PUT "http://localhost:8080/services/$dir" -d "{\"mllib\":\"xgboost\",\"description\":\"$dir\",\"type\":\"supervised\",\"parameters\":{\"input\":{\"connector\":\"txt\"},\"mllib\":{\"nclasses\":$nb_classes}},\"model\":{\"repository\":\"$full_path/$dir\"}}"

done
