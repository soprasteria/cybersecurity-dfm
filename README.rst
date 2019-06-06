****************************************
Data Feeds Manager
****************************************

![Analysis](analysis.png)
![Explore](explore.png)

=============
License
=============

Data Feeds Manager is a service which crawl feeds, extract core text content, generate text training set for machine learning and manage score selection based on predictions.

Copyright (C) 2016  Alexandre CABROL PERALES from Sopra Steria Group.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

=============
Description
=============

Data Feeds Manager aim to manage Feed based on data received from them.

This service crawl Feeds to assess their content and rank them regarding topics predicted by `DeepDetect`_.

This service let you generate machine learning models from news to `DeepDetect`_.

This service use `ElasticSearch`_ as data storage, `DeepDetect`_ for content Tagging and `Kibana`_ for data visualization.
`TinyTinyRSS`_ is also used as RSS Feed aggregator but could be replaced by any RSS Feed Manager service which provide un aggregated RSS feed.

Currently RSS Feeds and `Twitter`_ are supported, `Reddit`_ and `Dolphin`_ are planned to be supported in the futur.

=============
Definition
=============
- News are called doc (type in elasticsearch)
- *Source* of news are called also feeds (RSS or Twitter currently)
- *Tag* is a keyword (in rss feeds) or a hashtag (in twitter) people set in the news before post it
- *Topic* is a group of Tags related to the same subject
- *Model Config* is a group of Topics which are linked to the same theme
- *Model* is a machine learning model in Deep Detect when it is supervised it used a training set for generation
- *Training Set* is extraction of all news related to a model dispatch by topics in order to train a supervised machine learnign algorithm


=============
Requirements
=============

The reference platform is Ubuntu Server 16.04 LTS.

According to ElasticSearch:
"Less than 8 GB tends to be counterproductive (you end up needing many, many small machines), and greater than 64 GB has problems."

DeepDetect can use NVIDIA CUDA GPU or standard x86_64 CPU. Current DFM install doesn't install this feature of DeepDetect.
See more here: https://github.com/beniz/deepdetect#caffe-dependencies

DFM will crawl large amount of data from the web if you have multiple RSS Feeds or Twitter searches.
A good bandwith with unlimited traffic is recommended (fiber, ...).

Minimal hardware might be:
- 8Gb Ram
- 4 CPUs
- 500Gb Hard Disk
- Internet Bandwith 24 Mb/s

Recommended hardware might be:
- 64 Gb Ram
- 32 CPUs or 2 NVIDIA GPU (Tesla)
- 2 Tb Hard Disk SSD
- Internet Bandwith 10 Gb/s

.. _ElasticSearch: https://www.elastic.co/downloads/elasticsearch
.. _Kibana: https://www.elastic.co/downloads/kibana
.. _DeepDetect: https://github.com/beniz/deepdetect
.. _TinyTinyRSS: https://tt-rss.org/gitlab/fox/tt-rss
.. _Dolphin: https://www.boonex.com/downloads
.. _Twitter: https://twitter.com
.. _Reddit: https://www.reddit.com/

=============
Install
=============
This installation has been tested with *Ubuntu 16.04.1 LTS*.
Installation folder */opt/dfm*
Require git installed (*apt-get install git*).
Run following commands in a terminal::
    cd /opt
    git clone https://github.com/soprasteria/cybersecurity-dfm.git
    cd dfm
    ./install_ubuntu.sh

The *install.sh* will install all dependencies, build when it is required, and create account dfm to run daemons.
There are 4 daemons with web protocol setup in supervisor:
- ES for elasticsearch, search engine acting like main storage (port 9200)
- KB for kibana, Dashboards (port 5601)
- DEDE for deepdetect, Machine Learning server (port 8080)
- DFM for Data Feed Manager, orchestrator of other services above (port 12345)

When installation is done.

- Edit /opt/dfm/dfm/settings.cfg and add your twitter account credentials.
- restart dfm with *supervisorctl restart dfm*
- Open web-browser then connect to http://localhost:12345
- Click on Source button in the menu
- Add a source (could be tinytiny-rss feed, rss feed or twitter search)
- Refresh the page then click on crawl link at the right of the table which list the sources to collecte the news
- Click on Topics page and create a Topic which selected tags.
- Click on Model then group Topics in the same model.
- Then click on generate model at the right of the table.

To setup Dashboards:
- Open web-browser the connect to http://localhost:5601
- Click on Settings button
- put a "*" in "Index name or pattern"
- Select updated for "Time-field name"
- Click on "Create"
- Click on "Discover" then change the top right time range to weeks or months
- Explore more in details `Kibana`_ documentation


=============
Other information
=============
- You can tune memory allocated to ElasticSearch in /etc/supervisor/conf.d/es.conf (default is 8Gb, it might be half of your memory) https://www.elastic.co/guide/en/elasticsearch/guide/current/heap-sizing.html
- Max number of files is important also for ElasticSearch in /etc/sysctl.conf read https://www.elastic.co/guide/en/elasticsearch/guide/current/_file_descriptors_and_mmap.html
- Main text is extracted from the news (in text field) and full html version is stored (in html field) as an ElasticSearch attachement.
- URL in twitts are browsed to get the target internet page.
- News which are too small (under *NEWS_MIN_TEXT_SIZE* config variable) are excluded and deleted from the database.
- For readability title of models are used as key between DeepDetect and DFM. Topic title are also used as key (label) between DeepDetect and DFM.
- The rss feed on the frontpage of DFM (port 12345) will provide you the best predicted news related to the topics in your models of the week. If there is not prediction you will have no news in this feed.
- The best prediction threshold is defined in /opt/dfm/dfm/settings.cfg  by default OVERALL_SCORE_THRESHOLD=0.1 . If the prediction scores of your news are lower than 0.1 you will have no news in the DFM frontpage feed.
- If you set Debug at True in settings.cfg the process will fork and can not be stopped by supervisor you will have to kill it on your own.
- link field in data structure is used to generate id of all objects so all objects (sources,topics,models) have a link used to generate the uuid
- Crontab of DFM account is used to call scheduled tasks from the API (http://localhost:12345/api/schedule/...), you can use this url for one time actions like:
  - crawl one source (eg: http://localhost:12345/api/schedule/cbf1d10571c4da9d101c1b4fab3d3d93)
  - crawl all source http://localhost:12345/api/schedule/sources_crawl
  - gather text body and html of doc (news) http://localhost:12345/api/schedule/contents_crawl
  - predict all news stored with text body http://localhost:12345/api/schedule/contents_predict
  - re-generate all prediction models http://localhost:12345/api/schedule/generate_models
- Flask logger is used to log messages. Most of messages are in DEBUG mode. For some reason not totally clear log file generated by flask (/opt/dfm/dfm/dfm.log) is less talkative than supervisor log file (/var/log/supervisor/dfm-stdout*.log).
- To get efficiency in topics prediction we recommend:
  - To have same number of news by topics for one model
  - To have more than 1000 news by topics
  - To create topics which doesn't mostly overlap (avoid to create multiple topics with synonims tags)

=============
Todo List
=============
- [ ] OPML import/export
- [ ] Social Networks other webservices integration (Reddit, Linkedin,... )
- [X] Extract text from documents (CSV,DOC,DOCX,EML,EPUB,GIF,JPG,JSON,MSG,ODT,PDF,PPTX,PS,RTF,TXT,XSLX,XSL)
- [ ] Extract text from video's audio speech
- [ ] Search engines crawling
- [ ] Pass javascript adds redirection
- [ ] Pass captcha filter
- [ ] Pass cookie acceptance


`Learn more <https://github.com/soprasteria/cybersecurity-dfm>`_.
