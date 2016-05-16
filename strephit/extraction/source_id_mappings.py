#!/usr/bin/env python
# -*- encoding: utf-8 -*-

# Statements come in the following form:
# {PERSON} Px {SOURCE_ID_URL}
SOURCE_ID_TO_WIKIDATA = {
    # http://vocab.getty.edu/page/ulan/500115588
    "vocab_getty_edu": "P245",
    # http://rkd.nl/explore/artists/32439
    "rkd_nl": "P650",
    # http://www.nndb.com/people/803/000024731/
    "nndb_com": "P1263",
    # http://www.genealogics.org/getperson.php?personID=I00129900&tree=LEO
    "genealogics": "P1819",
    # https://tools.wmflabs.org/mix-n-match/api.php?query=redirect&catalog=11&ext_id=GOGH,+Vincent+van
    "wga_hu": "P1882",
    # http://www.museothyssen.org/en/thyssen/ficha_artista/237
    "museothyssen_org": "P2431",
    # http://artuk.org/discover/artists/van-gogh-vincent-18531890
    "bbc_co_uk": "P1367",
    # https://collection.cooperhewitt.org/people/18060351/
    "cooperhewitt_org": "P2011"
}
