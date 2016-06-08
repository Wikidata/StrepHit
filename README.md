# StrepHit
*StrepHit* is a **Natural Language Processing** pipeline that understands human language, extracts facts from text and produces **[Wikidata](https://www.wikidata.org/wiki/Wikidata:Main_Page) statements** with **references**.

*StrepHit* is a IEG project **funded by the [Wikimedia Foundation](https://wikimediafoundation.org/wiki/Home)**.

*StrepHit* will enhance the data quality of Wikidata by **suggesting references to validate statements**, and will help Wikidata become the gold-standard hub of the Open Data landscape.

## Official Project Page
https://meta.wikimedia.org/wiki/Grants:IEG/StrepHit:_Wikidata_Statements_Validation_via_References

## Documentation
https://www.mediawiki.org/wiki/StrepHit

## Get Ready
- Install **Python 2.7**, **pip** and **Java 8** (it is needed only in an optional step which uses the Stanford CoreNLP library, you can skip it for now. Look out for `java.lang.UnsupportedClassVersionError: ...: Unsupported major.minor version xx.x`, that means you need it) 
- Clone the repository and create the workspace:
```
$ git clone https://github.com/Wikidata/StrepHit.git
$ mkdir StrepHit/dev
```
- Install all the Python requirements (preferably in a [virtualenv](http://docs.python-guide.org/en/latest/dev/virtualenvs/))
```
$ cd StrepHit
$ pip install -r requirements.txt
```
- Install the third party dependencies:
    - [TreeTagger](http://www.cis.uni-muenchen.de/~schmid/tools/TreeTagger/)
    - [Stanford CoreNLP](http://nlp.stanford.edu/software/stanford-corenlp-full-2015-12-09.zip):
     This is an optional dependency, you can skip this for now.
     Unzip and place JARs inside the `dev` dir, or use our utility:
```
$ python -m strephit commons download stanford_corenlp
```
- Register for a free account on the [Dandelion APIs](https://dandelion.eu/accounts/register/?next=/docs/api/datatxt/nex/getting-started/)
- Create the file `strephit/commons/secret_keys.py` with your Dandelion credentials. They can be seen in [your dashboard](https://dandelion.eu/profile/dashboard/)
```
NEX_URL = 'https://api.dandelion.eu/datatxt/nex/v1/'
NEX_APPID = 'your app ID'
NEX_APPKEY = 'your app key'
```

## Get Started

 - Produce quick statements from semi-structured data in the corpus (takes time, and a good internet connection):
```
python -m strephit extraction process_semistructured samples/corpus.jsonlines semistructured.qs
```

 - Extract sentences and perform entity linking:
```
$ python -m strephit commons pos_tag samples/corpus.jsonlines bio en -o dev/corpus-sample-tagged.jsonlines
$ python -m strephit corpus_analysis rank_verbs dev/corpus-sample-tagged.jsonlines bio en --dump-verbs dev/verbs.json
$ python -m strephit extraction extract_sentences samples/corpus.jsonlines en dev/verbs.json -o dev/sample-sentences.jsonlines
$ python -m strephit commons entity_linking dev/sample-sentences.jsonlines en -o dev/sample-sentences-linked.jsonlines
```

 - Extract data with the rule-based classifier:
```
$ python -m strephit rule_based classify dev/sample-sentences-linked.jsonlines en samples/lexical-db.json -o dev/classified.jsonlines
```

 - Train the supervised classifier and extract data:
```
$ python -m strephit annotation parse_results samples/crowdflower-results.csv dev/sample-training-set.jsonlines
$ python -m strephit classification train dev/sample-training-set.jsonlines en -o dev/sample-classifier.pkl
$ python -m strephit classification classify dev/sample-sentences-linked.jsonlines dev/classified.jsonlines en --model dev/sample-classifier.pkl
```

 - Serialize the classification results in quick statements:
```
$ python -m strephit commons serialize dev/classified.jsonlines samples/lexical-db.json classified.qs en
```

As you saw, you can compose strephit commands and receive help. Do not specify any argument, or use `--help` to see the available options:
```
$ python -m strephit                                                                             
Usage: __main__.py [OPTIONS] COMMAND [ARGS]...

Options:
  --log-level <TEXT CHOICE>...
  --cache-dir DIRECTORY
  --help                        Show this message and exit.

Commands:
  annotation          Corpus annotation via crowdsourcing
  classification      Roles classification
  commons             Common utilities used by others
  corpus_analysis     Corpus analysis module
  extraction          Data extraction from the corpus
  rule_based          Unsupervised fact extraction
  side_projects       Side projects scripts
  web_sources_corpus  Corpus retrieval from the web
```


## License
The source code is under the terms of the [GNU General Public License, version 3](http://www.gnu.org/licenses/gpl.html).
