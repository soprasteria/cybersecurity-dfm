#!/bin/bash
############################################################################
#                                                                          #
#   	                   Install Data Feeds Manager                      #
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
#VERSION=`uname -r`

# script variables
 ES_VERSION="2.3.4"
 KB_VERSION="4.5.3"
 # ES 2 can not work with JAVA 9 please check https://github.com/elastic/elasticsearch/issues/18761
 JAVA_VERSION="8"
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
	    echo -e "exit script [y/N] or retry your command [*]:"
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
runCMD "apt-get update"
runCMD "apt-get --yes upgrade"

# Install Packages

showSection "Install all packages commonly needed"
grep DFM_PATH /etc/environment
if [ $? -gt 0 ]; then echo "DFMPATH=`pwd`">>/etc/environment
export DFMPATH=`pwd`
fi
runCMD "source /etc/profile"
runCMD "apt-get install -y supervisor curl git build-essential openjdk-$JAVA_VERSION-jre-headless python-dev cmake"
grep 'minfds=125000' /etc/supervisor/supervisord.conf
if [ $? -ne 0 ]
  then sed -i.old "s/^\[supervisord\]$/\[supervisord\]\n### minfds parameter added for ElasticSearch\nminfds=125000/g" /etc/supervisor/supervisord.conf
fi
#Starting with Ubuntu 15.04, Upstart will be deprecated in favor of Systemd.
#runCMD "update-rc.d supervisor defaults"
#runCMD "service supervisor stop"
#runCMD "service supervisor start"
runCMD "systemctl enable supervisor"
runCMD "systemctl restart supervisor"

showSection "create user $DFM_USER $INSTALL_PATH"
runCMD "useradd -r -M -b $INSTALL_PATH $DFM_USER"

# currently ubuntu deb install fail with tt-rss due to config dialog requesting password confirmation for database without request before the password hint
# showSection "Install Tiny Tiny RSS"
# runCMD "apt-get install -y tt-rss"

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
runCMD "cp -bf --suffix=.backup utils/supervisor/es.conf /etc/supervisor/conf.d/es.conf"
sed 's@dfm_path@'$INSTALL_PATH'@g' /etc/supervisor/conf.d/es.conf

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
runCMD "cp -bf --suffix=.backup utils/supervisor/kb.conf /etc/supervisor/conf.d/kb.conf"
sed "s@dfm_path@$INSTALL_PATH@g" /etc/supervisor/conf.d/kb.conf
runCMD "supervisorctl reread"
runCMD "supervisorctl reload"
sleep 15
runCMD "curl -XGET localhost:5601"

showSection "Install DeepDetect Dependencies"
#removed curlpp-dev due to bad package in ubuntu 16.04 LTS see details below
#runCMD "apt-get install -y libgoogle-glog-dev libgflags-dev libeigen3-dev libopencv-dev libcppnetlib-dev libboost-dev libcurlpp-dev libcurl4-openssl-dev protobuf-compiler libopenblas-dev libhdf5-dev libprotobuf-dev libleveldb-dev libsnappy-dev liblmdb-dev libutfcpp-dev"
runCMD "apt-get install -y libgoogle-glog-dev libgflags-dev libeigen3-dev libopencv-dev libcppnetlib-dev libboost-dev libcurl4-openssl-dev protobuf-compiler libopenblas-dev libhdf5-dev libprotobuf-dev libleveldb-dev libsnappy-dev liblmdb-dev libutfcpp-dev libboost-all-dev"

showSection "Install curlpp from source due to issue in Ubuntu 16.04 LTS package see https://github.com/beniz/deepdetect/issues/126"
runCMD "apt-get install -y autoconf libtool-bin"
runCMD "git clone https://github.com/datacratic/curlpp"
runCMD "cd curlpp"
#quick fix autogen twice ??
runCMD "./autogen.sh"
./configure --prefix=/usr --enable-ewarning=no
runCMD "./autogen.sh"
runCMD "./configure --prefix=/usr --enable-ewarning=no"
runCMD "make"
runCMD "make install"
runCMD "cd .."

showSection "Install DeepDetect"
runCMD "git clone https://github.com/beniz/deepdetect.git"
runCMD "cd deepdetect"
runCMD "mkdir build"
runCMD "cd build"
runCMD "cmake .. -DUSE_XGBOOST=ON"
runCMD "make"

#showSection "Install Tests for DeepDetect"
#runCMD "cmake -DBUILD_TESTS=ON .."
#runCMD "make"

#showSection "Run DeepDetect Tests"
#runCMD "ctest"

showSection "Start & Setup DeepDetect"
runCMD "cd $INSTALL_PATH"
runCMD "chown -Rf $DFM_USER deepdetect*"
runCMD "cp -bf --suffix=.backup utils/supervisor/dede.conf /etc/supervisor/conf.d/dede.conf"
sed "s@dfm_path@$INSTALL_PATH@g" /etc/supervisor/conf.d/dede.conf
runCMD "supervisorctl reread"
runCMD "supervisorctl reload"
sleep 15
runCMD "curl -XGET localhost:8080"

showSection "Install DFM"
runCMD "apt-get install -y python-dev python-pip python-setuptools python-pip libxml2-dev libxslt1-dev zlib1g-dev graphviz libjpeg-dev libpng12-dev"
runCMD "apt-get install -y build-essential chrpath libssl-dev libxft-dev libfreetype6 libfreetype6-dev libfontconfig1 libfontconfig1-dev"

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
cp -f $DFM_PATH/utils/settings.cfg.default $DFM_PATH/dfm/settings.cfg
runCMD "chown -Rf $DFM_USER *"
runCMD "cp -bf --suffix=.backup utils/supervisor/dfm.conf /etc/supervisor/conf.d/dfm.conf"
sed "s@dfm_path@$INSTALL_PATH@g" /etc/supervisor/conf.d/dfm.conf
runCMD "supervisorctl reread"
runCMD "supervisorctl reload"
sleep 5
runCMD "curl -XGET localhost:12345"

showSection "Set DFM cron tasks"
sed -i.default 's@dfm_path@'$INSTALL_PATH'@g' current.crontab
sudo -u $DFM_USER crontab -l >current.crontab
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

echo -e "###############################################################################################################################################"
echo -e "# User 'supervisorctl' command to start/stop services related to dfm (data feeds manager), es (elasticsearch), kb (kibana), dede (deepdetect) #"
echo -e "###############################################################################################################################################"

##############################################

# ending script
showSection "End of script"


exec 1>&3 3>&- 2>&4 4>&-
 wait $tpid
 rm $OUTPUT_PIPE


 exit 0
