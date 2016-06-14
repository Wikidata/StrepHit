**StrepHit** is an intelligent reading agent that understands text and translates it into `Wikidata <https://www.wikidata.org/wiki/Wikidata:Main_Page>`_ statements.

More specifically, it is a Natural Language Processing pipeline that extracts facts from text and produces Wikidata statements with references. Its final objective is to enhance the data quality of Wikidata by suggesting references to validate statements.

**StrepHit** was born in January 2016 and is funded by a `Wikimedia Foundation Individual Engagement Grant <https://meta.wikimedia.org/wiki/Grants:IEG/StrepHit:_Wikidata_Statements_Validation_via_References>`_ (IEG).

This page contains the technical documentation.

Source Code
===========

The whole codebase can be found on *GitHub*: 
`https://github.com/Wikidata/StrepHit <https://github.com/Wikidata/StrepHit>`_

Features
========

* `Web spiders <https://github.com/Wikidata/StrepHit/tree/master/strephit/web_sources_corpus>`_ to collect a biographical corpus from a `list of reliable sources <https://meta.wikimedia.org/wiki/Grants:IEG/StrepHit:_Wikidata_Statements_Validation_via_References/Timeline#Biographies>`_
* `Corpus analysis <https://github.com/Wikidata/StrepHit/tree/master/strephit/corpus_analysis>`_ to understand the most meaningful verbs 
* `Extraction <https://github.com/Wikidata/StrepHit/tree/master/strephit/extraction>`_ of sentences and semi-structured data from a corpus
* Train an automatic classifier through `crowdsourcing <https://github.com/Wikidata/StrepHit/tree/master/strephit/annotation>`_
* **Extract facts** from text in 2 ways:
    - `Supervised <https://github.com/Wikidata/StrepHit/tree/master/strephit/classification>`_
    - `Rule-based <https://github.com/Wikidata/StrepHit/tree/master/strephit/rule_based>`_
* Several `utilities <https://github.com/Wikidata/StrepHit/tree/master/strephit/commons>`_, ranging from NLP tasks like `tokenization <https://en.wikipedia.org/wiki/Tokenization_(lexical_analysis)>`_ and `part-of-speech tagging <https://en.wikipedia.org/wiki/Part-of-speech_tagging>`_, to facilities for parallel processing, caching and logging

Pipeline
========

1. Corpus Harvesting
2. Corpus Analysis
3. Sentence Extraction
4. N-ary Relation Extraction
5. Dataset Serialization
