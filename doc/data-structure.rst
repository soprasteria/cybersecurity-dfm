.. _data-structure:

Data structure
==============
dfm create an index called by default watch which can be changed by settings.
This index has serveral types of objects.

Type Source
--------------
This contain definition of a source and it settings.

.. literalinclude:: ../utils/elasticsearch_config.sh
   :language: bash
   :lines: 23-82

Type Doc
--------
This contain a doc (a news) with all metadatas, html, extracted text and predicted topics.

.. literalinclude:: ../utils/elasticsearch_config.sh
   :language: bash
   :lines: 83-151

Type Topic
--------
This contain a topic (group of tags) with all parameters.

.. literalinclude:: ../utils/elasticsearch_config.sh
  :language: bash
  :lines: 152-179
Type Model (Config)
--------
This contain configuration for a DeepDetect model (theme grouping several topics) with all parameters.

.. literalinclude:: ../utils/elasticsearch_config.sh
  :language: bash
  :lines: 180-207
