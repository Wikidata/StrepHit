# -*- encoding: utf-8 -*-
FRAME_REPO = [
    {
        "lu":
        {
            "lemma": "pubblicare",
            "tokens":
            [
    "pubblica",
    "pubblicano",
    "pubblico",
    "pubblicarlo",
    "pubblic\u00f2",
    "pubblicarli",
    "pubblicarle",
    "pubblicarla",
    "pubblicarne",
    "pubblicato",
    "pubblicandone",
    "pubblicati",
    "pubblicate",
    "pubblicavano",
    "pubblicata",
    "pubblichiamo",
    "pubblicarono",
    "pubblicassi",
    "pubblicava",
    "pubblicare",
    "pubblichi",
    "pubblichino",
    "pubblicheremo",
    "pubblicher\u00e0",
    "pubblicando",
    "pubblicai",
    "pubblicher\u00f2"
            ],
            "frames":
            [
                {
                    "frame": u"Pubblicazione",
                    "FEs":
                    [
                        { "Autore": "core" },
                        { "Editore": "core" },
                        { "Lavoro": "core" },
                        { "Luogo": "extra" },
                        { "Tempo": "extra" }
                    ],
                    "DBpedia":
                    [
                        { "Person": "Autore" },
                        { "Organisation": "Editore" },
                        { "Work": "Lavoro" },
                        { "Place": "Luogo" }
                    ]
                }
            ]
        }
    },    
    {
        "lu": 
        {
            "lemma": "giocare",
            "tokens":
            [
  "giocare",
    "giocassero",
    "giocherebbe",
    "giocandosi",
    "giocassimo",
    "giocarvi",
    "giocherebbero",
    "giocammo",
    "giocarsela",
    "giocatesi",
    "giocarsi",
    "giocarsele",
    "giocavo",
    "giocano",
    "giocai",
    "giocate",
    "giocarla",
    "giocheranno",
    "giocata",
    "giocarono",
    "giocavi",
    "giocherei",
    "giocavano",
    "giocheremo",
    "giocato",
    "giocati",
    "giocarsene",
    "giocava",
    "gioc\u00f2",
    "giochino",
    "giocher\u00e0",
    "giocando",
    "gioca",
    "giocarli",
    "giochiamocela",
    "giocher\u00f2",
    "giocarle",
    "gioco",
    "giocarmela",
    "giocasse",
    "giocandoli",
    "giocavamo",
    "giocarmelo",
   "giocarcela",
    "giocheremmo",
    "giocarci",
    "giochi",
    "giochiamo",
    "giocarmi"
            ],
            "frames":
            [
                {
                    "frame": "Attivita",
                    "FEs":
                    [
                        { "Attivita": "core" },
                        { "Partecipante": "core" },
                        { "Luogo": "extra" },
                        { "Tempo": "extra" },
                    ],
                    "DBpedia":
                    [
                        { "Activity": "Attivita" },
                        { "Person": "Partecipante" },
                        { "Organisation": "Partecipante" },
                        { "Place": "Luogo" }
                    ]
                }
            ]
        }
    },
    {
        "lu":
        {
            "lemma": "assumere",
            "tokens":
            [
   "assumer\u00e0",
    "assumano",
    "assumiamo",
    "assunse",
    "assumiti",
    "assumono",
    "assumerlo",
    "assumersi",
    "assumersene",
    "assumeremo",
    "assumerne",
    "assumer",
    "assunti",
    "assumerci",
    "assumere",
    "assunto",
    "assunta",
    "assunte",
    "assumevo",
    "assumevano",
    "assumeva",
    "assumendosi",
    "assumo",
    "assumessero",
    "assumi",
    "assume",
    "assumerebbe",
    "assuma",
    "assumermi",
    "assumerti",
    "assumeranno",
    "assumendosene",
    "assunsero",
    "assumendo"
            ],
            "frames":
            [
                {
                    "frame": "Assunzione",
                    "FEs":
                    [
                        { "Datore": "core" },
                        { "Assunto": "core" },
                        { "Luogo": "extra" },
                        { "Tempo": "extra" }
                    ],
                    "DBpedia":
                    [
                        { "Organisation": "Datore" },
                        { "Person": "Assunto" },
                        { "Place": "Luogo" }
                    ]
                }
            ]
        }
    },
    {
        "lu":
        {
            "lemma": "acquistare",
            "tokens":
            [
   "acquistare",
    "acquistarne",
    "acquistano",
    "acquistarla",
    "acquistassero",
    "acquistiamo",
    "acquistati",
    "acquistavano",
    "acquistava",
    "acquistarle",
    "acquistato",
    "acquistata",
    "acquistarli",
    "acquistate",
    "acquistarlo",
    "acquisterete",
    "acquister\u00e0",
    "acquistando",
    "acquist\u00f2",
    "acquisteranno",
    "acquisterebbe",
    "acquirente",
    "acquisti",
    "acquister\u00f2",
    "acquirenti",
    "acquista",
    "acquistandolo",
    "acquisto",
    "acquistandola",
    "acquistavo"
            ],
            "frames":
            [
                {
                    "frame": u"Acquisto",
                    "FEs":
                    [
                        { "Compratore": "core" },
                        { "Comprato": "core" },
                        { "Luogo": "extra" },
                        { "Tempo": "extra" }
                    ],
                    "DBpedia":
                    [
                        { "Agent": "Compratore" },
                        { "Work": "Comprato" },
                        { "Place": "Luogo" }
                    ]
                }
            ]
        }
    },
    {
        "lu":
        {
            "lemma": "agglomerare",
            "tokens":
            [
		"agglomerato"
            ],
            "frames":
            [
                {
                    "frame": "Agglomerazione",
                    "FEs":
                    [
                        { "Agglomerato": "core" },
                        { "Responsabile": "core" },
                        { "Luogo": "extra" },
                        { "Tempo": "extra" }
                    ],
                    "DBpedia":
                    [
                        { "Work": "Agglomerato" },
                        { "Agente": "Responsabile" },
                        { "Place": "Luogo" }
                    ]
                }
            ]
        }
    }
]
