# StrepHit
*StrepHit* is a **Natural Language Processing** pipeline that understands human language, extracts facts from text and produces **[Wikidata](https://www.wikidata.org/wiki/Wikidata:Main_Page) statements** with **references**.

*StrepHit* is a IEG project **funded by the [Wikimedia Foundation](https://wikimediafoundation.org/wiki/Home)**.

*StrepHit* will enhance the data quality of Wikidata by **suggesting references to validate statements**, and will help Wikidata become the gold-standard hub of the Open Data landscape.

# Official Project Page
https://meta.wikimedia.org/wiki/Grants:IEG/StrepHit:_Wikidata_Statements_Validation_via_References

# Documentation
https://www.mediawiki.org/wiki/StrepHit

# Features
- **[Web spiders](strephit/web_sources_corpus)** to collect a biographical corpus from a [list of reliable sources](https://meta.wikimedia.org/wiki/Grants:IEG/StrepHit:_Wikidata_Statements_Validation_via_References/Timeline#Biographies)
- **[Corpus analysis](strephit/corpus_analysis)** to understand the most meaningful verbs 
- **[Extraction](strephit/extraction)** of sentences and semi-structured data from a corpus
- Train an automatic classifier through **[crowdsourcing](strephit/annotation)**
- **Extract facts** from text in 2 ways:
    - [Supervised](strephit/classification)
    - [Rule-based](strephit/rule_based)
- Several **[utilities](strephit/commons)**, ranging from NLP tasks like *[tokenization](https://en.wikipedia.org/wiki/Tokenization_(lexical_analysis))* and *[part-of-speech tagging](https://en.wikipedia.org/wiki/Part-of-speech_tagging)*, to facilities for parallel processing, caching and logging

# Pipeline
1. Corpus Harvesting
2. Corpus Analysis
3. Sentence Extraction
4. N-ary Relation Extraction
5. Dataset Serialization

# Get Ready
- Install **[Python 2.7](https://www.python.org/downloads/)** and **[pip](https://pip.pypa.io/en/stable/installing/)**
- Clone the repository and create the output folder:
```
$ git clone https://github.com/Wikidata/StrepHit.git
$ mkdir StrepHit/output
```
- Install all the Python requirements (preferably in a [virtualenv](http://docs.python-guide.org/en/latest/dev/virtualenvs/))
```
$ cd StrepHit
$ pip install -r requirements.txt
```
- Install [TreeTagger](http://www.cis.uni-muenchen.de/~schmid/tools/TreeTagger/)
- Register for a free account on the [Dandelion APIs](https://dandelion.eu/accounts/register/?next=/docs/api/datatxt/nex/getting-started/)
- Create the file `strephit/commons/secret_keys.py` with your API token. You can find it in [your dashboard](https://dandelion.eu/profile/dashboard/)
```
NEX_URL = 'https://api.dandelion.eu/datatxt/nex/v1/'
NEX_TOKEN = 'your API token here'
```

## Optional dependency
If you want to **[extract sentences](strephit/extraction/extract_sentences.py)** via __[syntactic parsing](https://en.wikipedia.org/wiki/Parsing)__, you will need to install:
- [Java 8](http://www.java.com/en/download/)
- [Stanford CoreNLP](http://stanfordnlp.github.io/CoreNLP/), through our utility:
```
$ python -m strephit commons download stanford_corenlp
```

# Command Line
You can run all the NLP pipeline components through a command line.
Do not specify any argument, or use `--help` to see the available options.
Each command can have a set of sub-commands, depending on its granularity.
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

# Get Started
- Generate a dataset of Wikidata assertions (*[QuickStatements](https://tools.wmflabs.org/wikidata-todo/quick_statements.php)* syntax) from semi-structured data in the corpus (takes time, and a good internet connection):
```
$ python -m strephit extraction process_semistructured -p 1 samples/corpus.jsonlines
```

- Produce a ranking of meaningful verbs:
```
$ python -m strephit commons pos_tag samples/corpus.jsonlines bio en
$ python -m strephit corpus_analysis rank_verbs output/pos_tagged.jsonlines bio en
```

- Extract sentences using the ranking and perform [Entity Linking](https://en.wikipedia.org/wiki/Entity_linking):
```
$ python -m strephit extraction extract_sentences samples/corpus.jsonlines output/verbs.json en
$ python -m strephit commons entity_linking -p 1 output/sentences.jsonlines en
```

- Extract facts with the rule-based classifier:
```
$ python -m strephit rule_based classify output/entity_linked.jsonlines samples/lexical_db.json en
```

- Train the supervised classifier and extract facts:
```
$ python -m strephit annotation parse_results samples/crowdflower_results.csv
$ python -m strephit classification train output/training_set.jsonlines en
$ python -m strephit classification classify output/entity_linked.jsonlines output/classifier_model.pkl en
```

- Serialize the classification results into a dataset of Wikidata assertions:
```
$ python -m strephit commons serialize -p 1 output/supervised_classified.jsonlines samples/lexical_db.json en
```

**N.B.**: you will find all the output files in the `output` folder.

## Note on Parallel Processing
By default, StrepHit uses as many processes as the number of CPU cores in the machine where it runs.
Add the `-p` parameter if you want to change the behavior.

Set `-p 1` to **disable** parallel processing.

# License
The source code is under the terms of the [GNU General Public License, version 3](http://www.gnu.org/licenses/gpl.html).
