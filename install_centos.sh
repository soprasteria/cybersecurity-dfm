#!/bin/bash
############################################################################
#                                                                          #
#                        Install Data Feeds Manager                        #
#                                                                          #
#                     Made by Alexandre CABROL PERALES                     #
#                      on behalf of Sopra Steria Group                     #
#                                                                          #
#              Desc : REST API Server to manage  Feeds by Data             #
#                                                                          #
#       Data Feeds Manager is an  Feed data management server.             #
#    Copyright (C) 2016  Alexandre CABROL PERALES from Sopra Steria Group. #
#                                                                          #
#    This program is free software: you can redistribute it and/or modify  #
#    it under the terms of the GNU General Public License as published by  #
#    the Free Software Foundation, either version 3 of the License, or     #
#    (at your option) any later version.                                   #
#                                                                          #
#    This program is distributed in the hope that it will be useful,       #
#    but WITHOUT ANY WARRANTY; without even the implied warranty of        #
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         #
#    GNU General Public License for more details.                          #
#                                                                          #
#    You should have received a copy of the GNU General Public License     #
#    along with this program.  If not, see <http://www.gnu.org/licenses/>. #
############################################################################


##############################################
#              Variables                     #
##############################################

# log file
 DATE_FORMAT="+%Y-%m-%d"
 DATE=`date ${DATE_FORMAT}`
 OUTPUT_LOG="/var/log/install_dfm-${DATE}.log"
 OUTPUT_PIPE="/var/spool/install_dfm.pipe"

# system version
 # VERSION=`uname -r`

# script variables
 ES_VERSION="2.3.4"
 KB_VERSION="4.5.3"
 # ES 2 can not work with JAVA 9 please check https://github.com/elastic/elasticsearch/issues/18761
 JAVA_VERSION="jdk-8u45-linux-x64"
 EPEL_VERSION="7-9.noarch"
 INSTALL_PATH=`pwd`
 DFM_USER="dfm"
 PHANTOM_JS="phantomjs-2.1.1-linux-x86_64"

##############################################
#               Functions                    #
##############################################

# display a section
function showSection {
LINE_STR=`echo "############################################################"`
LINE_STR_LENGTH=`expr length "$LINE_STR"`
echo -e '\E[;35m'"\033[1m$LINE_STR\033[0m"
STR_MESSAGE=`echo " $1 "`
STR_LENGTH=`expr length "$STR_MESSAGE"`
let MAX_STR_LENGTH=$LINE_STR_LENGTH-2
while [ $STR_LENGTH -lt $MAX_STR_LENGTH ]
do
        STR_MESSAGE=`echo "$STR_MESSAGE#"`
        STR_LENGTH=`expr length "$STR_MESSAGE"`
        if [ $STR_LENGTH -lt $MAX_STR_LENGTH ]; then STR_MESSAGE=`echo "#$STR_MESSAGE"`
           STR_LENGTH=`expr length "$STR_MESSAGE"`
        fi
done
STR_MESSAGE=`echo '\E[;35m'"\033[1m#$STR_MESSAGE#\033[0m"`
echo -e $STR_MESSAGE
echo -e '\E[;35m'"\033[1m$LINE_STR\033[0m"
}

# save old config file
OLD=`date +%s`
function saveOLD {
 let OLD=$OLD+1
 cp $1 ${1}.old${OLD}
}

# test command given in argument
function runCMD {
  # check command exit code and display a message
  CMD="$@"
  LAST_CMD=`echo -e "$CMD"`
  echo -e '\E[;34m'"\033[1m###### $LAST_CMD ######\033[0m"
  eval $LAST_CMD
        if [ $? -ne 0 ]; then
           echo -e '\E[;41m'"\033[1m###### $LAST_CMD FAILED ######\033[0m"

            echo -e " check log file => $OUTPUT_LOG"
            echo -e "exit script [y/N] or retry your command:"
            read decision
            if [ "$decision" == "y" ]
             then echo -e "stopped ..."
              rm $OUTPUT_PIPE
                exit 1
	   elif [ "$decision" == "N" ]
		then echo -e "continuing ..."
           else
            echo -e "Unknown demand, rerunning command ..."
	    runCMD "$CMD"
           fi
        else

                    echo -e '\E[;42m'"\033[1m###### OK ######\033[0m"
        fi
}

# test latest command
function testCMD {
  # check command exit code and display a message
        if [ $? -ne 0 ]; then
           echo -e '\E[;41m'"\033[1m###### FAILED ######\033[0m"

            echo -e " check log file => $OUTPUT_LOG"
            echo -e "exit script [y/N]:"
            read decision
            if [ "$decision" == "y" ]
             then echo -e "stopped ..."
                 exec 1>&3 3>&- 2>&4 4>&-
                         wait $tpid
              rm $OUTPUT_PIPE
                exit 1
            else
                echo -e "continuing ..."
                fi
        else

            echo -e '\E[;42m'"\033[1m###### OK ######\033[0m"
        fi
}

##############################################
#                  Body                      #
##############################################
# initialize log output and display
 if [ ! -e $OUTPUT_PIPE ]; then
     mkfifo $OUTPUT_PIPE
 fi

 if [ -e $OUTPUT_LOG ]; then
     rm $OUTPUT_LOG
 fi

 exec 3>&1 4>&2
 tee $OUTPUT_LOG < $OUTPUT_PIPE >&3 &
 tpid=$!
 exec > $OUTPUT_PIPE 2>&1



echo -e "#####################################################################################################"
echo -e "# Data Feeds Manager Installer  Copyright (C) 2016  Alexandre CABROL PERALES for Sopra Steria Group #"
echo -e "# This program comes with ABSOLUTELY NO WARRANTY;                                                   #"
echo -e "# This is free software, and you are welcome to redistribute it                                     #"
echo -e "# under certain conditions; PLEASE READ LICENSE FILE.                                               #"
echo -e "#####################################################################################################"
echo -e ""

##############################################


showSection "Upgrade"
runCMD "wget http://dl.fedoraproject.org/pub/epel/7/x86_64/e/epel-release-${EPEL_VERSION}.rpm"
runCMD "rpm -Uvh epel-release-${EPEL_VERSION}.rpm"
runCMD "yum -y update"
runCMD "yum -y upgrade"

# Install Packages

showSection "Install all packages commonly needed"
grep DFM_PATH /etc/environment
if [ $? -gt 0 ]; then echo "DFMPATH=`pwd`">>/etc/environment
export DFMPATH=`pwd`
fi
runCMD "source /etc/profile"
# Get Java
java -version > /dev/null
if [ $? -ne 0 ]
   then runCMD "wget --no-cookies --no-check-certificate --header \"Cookie: gpw_e24=http%3A%2F%2Fwww.oracle.com%2F; oraclelicense=accept-securebackup-cookie\" \"http://download.oracle.com/otn-pub/java/jdk/8u45-b14/$JAVA_VERSION.rpm\""
   runCMD "rpm -ivh jdk-8u45-linux-x64.rpm"
fi
runCMD "java -version"
runCMD "yum groupinstall -y 'Development Tools'"
runCMD "yum install -y python-setuptools curl wget git build-essential python-devel cmake3"
/bin/cmake
if [ $? -eq 0 ]
   then cp /bin/cmake /bin/cmake.tmp
   cp /bin/cmake3 /bin/cmake
fi
showSection "Configure Supervisor"
runCMD "easy_install pip"
runCMD "pip install supervisor"
runCMD "echo_supervisord_conf > supervisord.conf"
mkdir -p /etc/supervisor/conf.d
ls /etc/supervisor/ | grep supervidord.conf
if [ $? -ne 0 ]
   then runCMD "cp supervisord.conf /etc/supervisor/supervisord.conf"
   sed -i "s/^\[supervisord\]$/\[supervisord\]\n### minfds parameter added for ElasticSearch\nminfds=125000/g" /etc/supervisor/supervisord.conf
   else sed -i.old "s/^\[supervisord\]$/\[supervisord\]\n### minfds parameter added for ElasticSearch\nminfds=125000/g" /etc/supervisor/supervisord.conf
fi
ls /etc/rc.d/init.d/ | grep supervisord
if [ $? -ne 0 ]
   then cp /etc.rc.d.init.d/supervisord.d /etc.rc.d.init.d/supervisord.d.old
   runCMD "cp ${INSTALL_PATH}/utils/supervisor/supervisord_centos_service /etc/rc.d/init.d/supervisord"
   chmod +x /etc/rc.d/init.d/supervisord
fi

grep 'minfds=125000' /etc/supervisor/supervisord.conf
if [ $? -ne 0 ]
  then sed -i.old "s/^\[supervisord\]$/\[supervisord\]\n### minfds parameter added for ElasticSearch\nminfds=125000/g" /etc/supervisor/supervisord.conf
fi
cat /etc/supervisor/supervisord.conf | grep "files = /etc/supervisor/conf.d/\*.conf"
if [ $? -ne 0 ]
   then echo "[include]" >> /etc/supervisor/supervisord.conf
   echo "files = /etc/supervisor/conf.d/*.conf" >> /etc/supervisor/supervisord.conf
fi

runCMD "service supervisord start"

showSection "create user $DFM_USER $INSTALL_PATH"
runCMD "useradd -r -M -b $INSTALL_PATH $DFM_USER"

# showSection "Install Tiny Tiny RSS"
# runCMD "apt-get install -y tt-rss" # Wasn't tested on centos

showSection "Install ElasticSearch $ES_VERSION"
if [ ! -f "elasticsearch-$ES_VERSION.tar.gz" ]
  then runCMD "wget https://download.elastic.co/elasticsearch/release/org/elasticsearch/distribution/tar/elasticsearch/2.3.4/elasticsearch-$ES_VERSION.tar.gz"
fi
if [ ! -L elasticsearch ]
 then runCMD "tar -xzf elasticsearch-$ES_VERSION.tar.gz"
runCMD "ln -s elasticsearch-$ES_VERSION elasticsearch"
fi
runCMD "elasticsearch/bin/plugin install mapper-attachments"

#Elasticsearch need to increase number of files on your system
# see https://www.elastic.co/guide/en/elasticsearch/guide/current/_file_descriptors_and_mmap.html
echo "vm.max_map_count=262144" >> /etc/sysctl.conf
runCMD "sysctl -w vm.max_map_count=262144"

showSection "Start & Setup ElasticSearch $ES_VERSION"
runCMD "chown -Rf $DFM_USER elasticsearch*"
sed -i.default 's@dfm_path@'$INSTALL_PATH'@g' utils/supervisor/es.conf
runCMD "cp -f utils/supervisor/es.conf /etc/supervisor/conf.d/es.conf"

echo "#half of the memory dedicated to ES see https://www.elastic.co/guide/en/elasticsearch/guide/current/heap-sizing.html">>/etc/supervisor/conf.d/es.conf
head -n 1 /proc/meminfo |sed 's/[^ ]\+ \+\([^ ]\+\) .*/numfmt --from-unit=512 --to=iec --padding=7 \1/'|bash| awk '{print "environment=ES_HEAP_SIZE="$1}'>>/etc/supervisor/conf.d/es.conf

runCMD "supervisorctl reread"
runCMD "supervisorctl reload"
sleep 15
runCMD "curl -XGET localhost:9200"
runCMD "utils/elasticsearch_config.sh"

showSection "Install Kibana $KB_VERSION"
if [ ! -f "kibana-$KB_VERSION-linux-x64.tar.gz" ]
  then runCMD "wget https://download.elastic.co/kibana/kibana/kibana-$KB_VERSION-linux-x64.tar.gz"
fi
if [ ! -L kibana ]
 then runCMD "tar -xzf kibana-$KB_VERSION-linux-x64.tar.gz"
 runCMD "ln -s kibana-$KB_VERSION-linux-x64 kibana"
fi

showSection "Start Kibana $ES_VERSION"
runCMD "chown -Rf $DFM_USER kibana*"
sed -i.default "s@dfm_path@$INSTALL_PATH@g" utils/supervisor/kb.conf
runCMD "cp -f utils/supervisor/kb.conf /etc/supervisor/conf.d/kb.conf"
runCMD "supervisorctl reread"
runCMD "supervisorctl reload"
sleep 15
runCMD "curl -XGET localhost:5601"

showSection "Install DeepDetect Dependencies"
mkdir dependencies
cd dependencies
yum install -y atlas-devel opencv-devel.x86_64 protobuf-devel.x86_64 protobuf-compiler.x86_64 gtest-devel.x86_64 openblas-devel.x86_64 eigen3-devel.noarch hdf5-devel.x86_64 leveldb-devel.x86_64 lmdb-devel.x86_64 snappy-devel.x86_64 libcurl-devel.x86_64 libcurl.x86_64 utf8cpp-devel.noarch openssl-devel.x86_64 yum-utils.noarch

runCMD "ln -sf /usr/local/include/eigen3/Eigen/ /usr/local/include/"
runCMD "wget https://sourceforge.net/projects/boost/files/boost/1.60.0/boost_1_60_0.tar.gz"
tar -xvzf boost_1_60_0.tar.gz
cd boost_1_60_0/
runCMD "./bootstrap.sh --with-libraries=atomic,date_time,exception,filesystem,iostreams,locale,program_options,regex,signals,system,test,thread,timer,log"
runCMD "./b2 install"

cd ..

runCMD "git clone https://github.com/datacratic/curlpp"
cd curlpp
#quick fix autogen twice ??
runCMD "./autogen.sh"
./configure --prefix=/usr --enable-ewarning=no
runCMD "./autogen.sh"
runCMD "./configure --prefix=/usr --enable-ewarning=no"
runCMD "make"
runCMD "make install"

cd ..

runCMD "wget http://downloads.cpp-netlib.org/0.11.2/cpp-netlib-0.11.2-final.tar.gz"
tar -xvzf cpp-netlib-0.11.2-final.tar.gz
cd cpp-netlib-0.11.2-final
mkdir cpp-netlib-build
cd cpp-netlib-build/
runCMD "cmake -DCMAKE_BUILD_TYPE=Debug -DCMAKE_C_COMPILER=gcc -DCMAKE_CXX_COMPILER=g++ .."
runCMD "make"
runCMD "make install"

cd ../..

mkdir /usr/local/include/boost/network
runCMD "cp /usr/include/openblas/* /usr/local/include/boost"
runCMD "cp -rva ${INSTALL_PATH}/cpp-netlib-0.11.2-final/boost/ /usr/local/include/boost/network"

runCMD "wget https://github.com/gflags/gflags/archive/v2.0.zip"
unzip v2.0.zip
cd gflags-2.0/
runCMD "./configure"
runCMD "make"
runCMD "make install"

cd ..
runCMD "wget https://github.com/google/glog/archive/v0.3.3.zip"
unzip v0.3.3.zip
cd glog-0.3.3/
runCMD "./configure"
runCMD "make && make install"

cd $INSTALL_PATH/

showSection "Install DeepDetect"
runCMD "git clone https://github.com/beniz/deepdetect.git"
cp $INSTALL_PATH/utils/deepdetect_centos_cmakelist $INSTALL_PATH/deepdetect/CMakeLists.txt
cd $INSTALL_PATH"/deepdetect"
mkdir build
cd build
runCMD "cmake .. -DUSE_XGBOOST=ON"
runCMD "make"
#showSection "Run DeepDetect Tests"
#runCMD "ctest"

showSection "Start & Setup DeepDetect"
runCMD "cd $INSTALL_PATH"
runCMD "chown -Rf $DFM_USER deepdetect*"
sed -i.default "s@dfm_path@$INSTALL_PATH@g" utils/supervisor/dede.conf
runCMD "cp -f utils/supervisor/dede.conf /etc/supervisor/conf.d/dede.conf"
runCMD "cp /lib/libcurlpp.so.0 /usr/local/lib/"
runCMD "supervisorctl reread"
runCMD "supervisorctl reload"
sleep 15
runCMD "curl -XGET localhost:8080"

showSection "Install DFM"
runCMD "yum install -y python-devel python2-pip python-setuptools libxml-devel libxslt-devel zlib-devel graphviz libjpeg-devel libpng12-devel"
runCMD "yum install -y chrpath openssl-devel libXft-devel freetype freetype-devel fontconfig fontconfig-devel"

#add phantomjs support for complex web page
runCMD "wget https://bitbucket.org/ariya/phantomjs/downloads/$PHANTOM_JS.tar.bz2"
runCMD "tar xvjf $PHANTOM_JS.tar.bz2"
runCMD "ln -sf $INSTALL_PATH/$PHANTOM_JS/bin/phantomjs /usr/local/bin"
runCMD "touch $INSTALL_PATH/ghostdriver.log"
runCMD "chown dfm:dfm $INSTALL_PATH/ghostdriver.log"
# Requirements installation
runCMD "cd $INSTALL_PATH"
runCMD "pip install --upgrade pip"
runCMD "pip install --upgrade setuptools"
runCMD "pip install -r requirements.txt"
runCMD "cd $INSTALL_PATH/dfm"
runCMD "curl https://raw.githubusercontent.com/codelucas/newspaper/master/download_corpora.py|python"
runCMD "mv $HOME/nltk_data ."
runCMD "chown -Rf dfm:dfm nltk_data"
runCMD "cd $INSTALL_PATH"
runCMD "ln -s ../deepdetect/clients/python/dd_client.py dfm/dd_client.py"
runCMD "make"
# setup tools with strange answer error: invalid command 'install_requires'
#runCMD "python setup.py install_requires"
runCMD "mkdir models"
runCMD "mkdir training"

showSection "Start & Setup DFM"
runCMD "chown -Rf $DFM_USER *"
sed -i.default "s@dfm_path@$INSTALL_PATH@g" utils/supervisor/dfm.conf
runCMD "cp -f utils/supervisor/dfm.conf /etc/supervisor/conf.d/dfm.conf"
runCMD "supervisorctl reread"
runCMD "supervisorctl reload"
sleep 5
runCMD "curl -XGET localhost:12345"

showSection "Set DFM cron tasks"
sudo -u $DFM_USER crontab -l >current.crontab
sed -i.default 's@dfm_path@'$INSTALL_PATH'@g' utils/scheduledTask.crontab
cat utils/scheduledTask.crontab >> current.crontab

runCMD "touch /var/run/dfm_contents_crawl.pid"
runCMD "chown $DFM_USER /var/run/dfm_contents_crawl.pid"
runCMD "touch /var/run/dfm_sources_crawl.pid"
runCMD "chown $DFM_USER /var/run/dfm_sources_crawl.pid"
runCMD "touch /var/run/dfm_generate_models.pid"
runCMD "chown $DFM_USER /var/run/dfm_generate_models.pid"
runCMD "touch /var/run/dfm_contents_predict.pid"
runCMD "chown $DFM_USER /var/run/dfm_contents_predict.pid"

runCMD "sudo -u $DFM_USER crontab current.crontab"
ls /bin | grep cmake.tmp
if [ $? -eq 0 ]
   then rm -f /bin/cmake
   mv /bin/cmake.tmp /bin/cmake
fi

echo -e "###############################################################################################################################################"
echo -e "# Use 'supervisorctl' command to start/stop services related to dfm (data feeds manager), es (elasticsearch), kb (kibana), dede (deepdetect) #"
echo -e "###############################################################################################################################################"

##############################################

# ending script
showSection "End of script"


exec 1>&3 3>&- 2>&4 4>&-
 wait $tpid
 rm $OUTPUT_PIPE


 exit 0
