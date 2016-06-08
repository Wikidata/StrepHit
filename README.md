# StrepHit
*StrepHit* is a **Natural Language Processing** pipeline that understands human language, extracts facts from text and produces **[Wikidata](https://www.wikidata.org/wiki/Wikidata:Main_Page) statements** with **references**.

*StrepHit* is a IEG project **funded by the [Wikimedia Foundation](https://wikimediafoundation.org/wiki/Home)**.

*StrepHit* will enhance the data quality of Wikidata by **suggesting references to validate statements**, and will help Wikidata become the gold-standard hub of the Open Data landscape.

## Official Project Page
https://meta.wikimedia.org/wiki/Grants:IEG/StrepHit:_Wikidata_Statements_Validation_via_References

## Documentation
https://www.mediawiki.org/wiki/StrepHit

## Get Ready
- Install **Python 2.7**, **pip** and **Java 8** (it is needed only in an optional step, you can skip it for now. Look out for `java.lang.UnsupportedClassVersionError: ...: Unsupported major.minor version xx.x`, that means you need it) 
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

## License
The source code is under the terms of the [GNU General Public License, version 3](http://www.gnu.org/licenses/gpl.html).
