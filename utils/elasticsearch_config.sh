#!/bin/bash
curl -PUT http://localhost:9200/watch -d '{
 "settings": {
   "analysis": {
     "char_filter": {
       "&_to_and": {
         "type": "mapping",
           "mappings": [ "&=> and "]
       }
     },
     "analyzer": {
       "html_analyzer": {
         "type": "custom",
         "char_filter": [ "html_strip", "&_to_and" ],
         "tokenizer": "standard",
         "filter": [ "lowercase" ]
       }
     }
   }
  },
    "mappings" : {
      "model" : {
        "_all" : {
          "enabled" : true
        },
        "properties" : {
          "active" : {
            "type" : "boolean",
            "null_value" : false
          },
          "freq" : {
            "type" : "integer"
          },
          "limit" : {
            "type" : "integer"
          },
          "link" : {
            "type" : "string",
            "index" : "not_analyzed"
          },
          "related_topics" : {
            "type" : "string",
            "index" : "not_analyzed"
          },
          "summary" : {
            "type" : "string"
          },
          "title" : {
            "type" : "string"
          },
          "updated" : {
            "type" : "date",
            "copy_to" : [ "_timestamp" ],
            "format" : "strict_date_optional_time||epoch_millis"
          }
        }
      },
      "source" : {
        "_all" : {
          "enabled" : true
        },
        "properties" : {
          "active" : {
            "type" : "boolean",
            "null_value" : false
          },
          "creator" : {
            "type" : "string"
          },
          "depth" : {
            "type" : "integer"
          },
          "enable_content" : {
            "type" : "boolean",
            "null_value" : true
          },
          "format" : {
            "type" : "string",
            "index" : "not_analyzed"
          },
          "freq" : {
            "type" : "integer"
          },
          "limit" : {
            "type" : "integer"
          },
          "link" : {
            "type" : "string",
            "index" : "not_analyzed"
          },
          "predict" : {
            "type" : "boolean",
            "null_value" : true
          },
          "step" : {
            "type" : "integer"
          },
          "summary" : {
            "type" : "string"
          },
          "tags" : {
            "type" : "string",
            "index" : "not_analyzed"
          },
          "title" : {
            "type" : "string"
          },
          "topics" : {
            "type" : "nested",
            "properties" : {
              "label" : {
                "type" : "string",
                "index" : "not_analyzed"
              },
              "score" : {
                "type" : "float"
              }
            }
          }
        }
      },
      "doc" : {
        "_all" : {
          "enabled" : true
        },
        "_parent" : {
          "type" : "source"
        },
        "_routing" : {
          "required" : true
        },
        "_timestamp" : {
          "enabled" : true
        },
        "properties" : {
          "author" : {
            "type" : "string",
            "index" : "not_analyzed"
          },
          "author_detail" : {
            "properties" : {
              "email" : {
                "type" : "string"
              },
              "href" : {
                "type" : "string"
              },
              "name" : {
                "type" : "string"
              }
            }
          },
          "authors" : {
            "properties" : {
              "email" : {
                "type" : "string"
              },
              "href" : {
                "type" : "string"
              },
              "name" : {
                "type" : "string"
              }
            }
          },
          "content" : {
            "type" : "nested",
            "properties" : {
              "base" : {
                "type" : "string"
              },
              "chat" : {
                "properties" : {
                  "all_members_are_administrators" : {
                    "type" : "boolean"
                  },
                  "first_name" : {
                    "type" : "string"
                  },
                  "id" : {
                    "type" : "long"
                  },
                  "last_name" : {
                    "type" : "string"
                  },
                  "title" : {
                    "type" : "string"
                  },
                  "type" : {
                    "type" : "string"
                  },
                  "username" : {
                    "type" : "string"
                  }
                }
              },
              "date" : {
                "type" : "long"
              },
              "entities" : {
                "properties" : {
                  "length" : {
                    "type" : "long"
                  },
                  "offset" : {
                    "type" : "long"
                  },
                  "type" : {
                    "type" : "string"
                  }
                }
              },
              "forward_date" : {
                "type" : "long"
              },
              "forward_from" : {
                "properties" : {
                  "first_name" : {
                    "type" : "string"
                  },
                  "id" : {
                    "type" : "long"
                  },
                  "last_name" : {
                    "type" : "string"
                  }
                }
              },
              "from" : {
                "properties" : {
                  "first_name" : {
                    "type" : "string"
                  },
                  "id" : {
                    "type" : "long"
                  },
                  "last_name" : {
                    "type" : "string"
                  },
                  "username" : {
                    "type" : "string"
                  }
                }
              },
              "language" : {
                "type" : "string"
              },
              "message" : {
                "type" : "string"
              },
              "message_id" : {
                "type" : "long"
              },
              "text" : {
                "type" : "string"
              },
              "type" : {
                "type" : "string"
              },
              "value" : {
                "type" : "string"
              }
            }
          },
          "feedburner_origlink" : {
            "type" : "string"
          },
          "format" : {
            "type" : "string",
            "index" : "not_analyzed"
          },
          "gd_image" : {
            "properties" : {
              "height" : {
                "type" : "string"
              },
              "rel" : {
                "type" : "string"
              },
              "src" : {
                "type" : "string"
              },
              "width" : {
                "type" : "string"
              }
            }
          },
          "guidislink" : {
            "type" : "boolean"
          },
          "href" : {
            "type" : "string"
          },
          "html" : {
            "type" : "attachment",
            "fields" : {
              "content" : {
                "type" : "string"
              },
              "author" : {
                "type" : "string"
              },
              "title" : {
                "type" : "string"
              },
              "name" : {
                "type" : "string"
              },
              "date" : {
                "type" : "date",
                "format" : "strict_date_optional_time||epoch_millis"
              },
              "keywords" : {
                "type" : "string"
              },
              "content_type" : {
                "type" : "string"
              },
              "content_length" : {
                "type" : "integer"
              },
              "language" : {
                "type" : "string"
              }
            }
          },
          "id" : {
            "type" : "string"
          },
          "link" : {
            "type" : "string",
            "index" : "not_analyzed"
          },
          "links" : {
            "properties" : {
              "href" : {
                "type" : "string"
              },
              "length" : {
                "type" : "string"
              },
              "rel" : {
                "type" : "string"
              },
              "title" : {
                "type" : "string"
              },
              "type" : {
                "type" : "string"
              }
            }
          },
          "media_thumbnail" : {
            "properties" : {
              "height" : {
                "type" : "string"
              },
              "url" : {
                "type" : "string"
              },
              "width" : {
                "type" : "string"
              }
            }
          },
          "occurences" : {
            "type" : "integer",
            "null_value" : 1
          },
          "origin" : {
            "type" : "string",
            "index" : "not_analyzed"
          },
          "published" : {
            "type" : "date",
            "format" : "strict_date_optional_time||epoch_millis"
          },
          "published_parsed" : {
            "properties" : {
              "__class__" : {
                "type" : "string"
              },
              "__value__" : {
                "type" : "string"
              }
            }
          },
          "query" : {
            "properties" : {
              "bool" : {
                "properties" : {
                  "must_not" : {
                    "properties" : {
                      "exists" : {
                        "properties" : {
                          "field" : {
                            "type" : "string"
                          }
                        }
                      }
                    }
                  }
                }
              },
              "wildcard" : {
                "properties" : {
                  "link" : {
                    "properties" : {
                      "value" : {
                        "type" : "string"
                      }
                    }
                  }
                }
              }
            }
          },
          "related_links" : {
            "type" : "string",
            "index" : "not_analyzed"
          },
          "rss_entry" : {
            "type" : "nested"
          },
          "source" : {
            "type" : "string",
            "index" : "not_analyzed"
          },
          "source_type" : {
            "type" : "string",
            "index" : "not_analyzed"
          },
          "summary" : {
            "type" : "string"
          },
          "summary_detail" : {
            "properties" : {
              "base" : {
                "type" : "string"
              },
              "language" : {
                "type" : "string"
              },
              "type" : {
                "type" : "string"
              },
              "value" : {
                "type" : "string"
              }
            }
          },
          "tags" : {
            "type" : "string",
            "index" : "not_analyzed"
          },
          "text" : {
            "type" : "string"
          },
          "thr_total" : {
            "type" : "string"
          },
          "title" : {
            "type" : "string"
          },
          "title_detail" : {
            "properties" : {
              "base" : {
                "type" : "string"
              },
              "language" : {
                "type" : "string"
              },
              "type" : {
                "type" : "string"
              },
              "value" : {
                "type" : "string"
              }
            }
          },
          "topics" : {
            "type" : "nested",
            "properties" : {
              "label" : {
                "type" : "string",
                "index" : "not_analyzed"
              },
              "score" : {
                "type" : "float"
              }
            }
          },
          "updated" : {
            "type" : "date",
            "copy_to" : [ "_timestamp" ],
            "format" : "strict_date_optional_time||epoch_millis"
          },
          "updated_parsed" : {
            "properties" : {
              "__class__" : {
                "type" : "string"
              },
              "__value__" : {
                "type" : "string"
              }
            }
          }
        }
      },
      "topic" : {
        "_all" : {
          "enabled" : true
        },
        "properties" : {
          "active" : {
            "type" : "boolean",
            "null_value" : false
          },
          "freq" : {
            "type" : "integer"
          },
          "link" : {
            "type" : "string",
            "index" : "not_analyzed"
          },
          "summary" : {
            "type" : "string"
          },
          "tags" : {
            "type" : "string",
            "index" : "not_analyzed"
          },
          "title" : {
            "type" : "string"
          },
          "updated" : {
            "type" : "date",
            "copy_to" : [ "_timestamp" ],
            "format" : "strict_date_optional_time||epoch_millis"
          }
        }
      }
    }
}'
echo '\n'

curl -XGET http://localhost:9200/watch/_mappings/?pretty=true
