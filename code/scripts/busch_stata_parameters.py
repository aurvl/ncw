"""Parameters transcribed from Busch et al.'s distributed Stata program.

The calculation uses these Python values directly; it does not parse the Stata
source at run time. Source line references identify the transcription origin.
"""

# Transcribed from `1. Model loop all data.do`, lines 218-238 and 313-326.
# Each ISO list inherits 0 for any country-specific parameter not assigned.
COUNTRY_PARAMETER_GROUPS = {
    'w': {
        0.188: 'ATG BLZ BRB CRI CUB DMA DOM GRD GTM HND HTI JAM KNA LCA MEX NIC PAN SLV TTO VCT'.split(),
        0.268: 'ARG BOL BRA CHL COL ECU GUF GUY PER PRY SUR URY VEN'.split(),
        0.355: (
            'AFG ARM AZE BGD BTN CHN GEO IDN IND IRN IRQ JOR KAZ KGZ KHM LAO LBN LKA MMR MNG '
            'MYS NPL OMN PAK PHL PNG PRK PSE SYR THA TJK TKM TLS TUR UZB VNM YEM'
        ).split(),
        0.392: (
            'AGO BDI BEN BFA BWA CAF CIV CMR COD COG COM CPV DJI DZA EGY ERI ESH ETH GAB GHA '
            'GIN GMB GNB GNQ KEN LBR LBY LSO MAR MDG MDV MLI MOZ MRT MUS MWI NAM NER NGA RWA '
            'SDN SEN SLE SOM SSD STP SWZ SYC TCD TGO TUN TZA UGA ZAF ZMB ZWE'
        ).split(),
        0.415: 'COK FJI FSM KIR MHL NRU PLW SLB TKL TON TUV VUT WSM'.split(),
    },
    'p': {
        52.65: 'ATG BLZ BRB CRI CUB DMA DOM GRD GTM HND HTI JAM KNA LCA NIC PAN SLV TTO VCT'.split(),
        59.73: 'MEX'.split(),
        61.04: 'BOL BRA COL ECU GUF GUY PER SUR VEN'.split(),
        67.76: 'BGD IDN KHM LAO LKA MMR MYS OMN PHL PNG THA TLS VNM YEM'.split(),
        69.26: 'PRY'.split(),
        71.24: (
            'AGO BDI BEN BFA CAF CIV CMR COD COG COM CPV DJI ERI ETH GAB GHA GIN GMB GNB GNQ '
            'KEN LBR MDG MDV MLI MOZ MRT MUS MWI NER NGA RWA SDN SEN SLE SOM SSD STP SYC TCD '
            'TGO TZA UGA ZMB ZWE'
        ).split(),
        76.08: 'COK FJI FSM KIR MHL NRU PLW SLB TKL TON TUV VUT WSM'.split(),
        76.88: 'IND'.split(),
        80.003: 'ARG CHL URY'.split(),
        80.83: 'BWA NAM'.split(),
        88.84: (
            'AFG ARM AZE BTN CHN GEO IRN IRQ JOR KAZ KGZ LBN MNG NPL PAK PRK PSE SYR TJK TKM '
            'TUR UZB'
        ).split(),
        93.4: 'DZA EGY ESH LBY LSO MAR SWZ TUN ZAF'.split(),
    },
    'exotic': {
        0.05: 'AFG ARM AZE GEO IRN IRQ JOR KAZ KGZ LBN OMN PSE SYR TJK TKM TUR UZB YEM'.split(),
        0.18: 'BLZ CRI GTM HND JAM MEX NIC PAN SLV'.split(),
        0.31: 'CHN MNG PRK'.split(),
        0.32: 'ATG BRB CUB DMA DOM GRD HTI KNA LCA TTO VCT'.split(),
        0.4: 'BGD BTN IDN IND KHM LAO LKA MMR MYS NPL PAK PHL THA TLS VNM'.split(),
        0.5: 'DZA EGY ESH LBY MAR TUN'.split(),
        0.74: (
            'AGO BDI BEN BFA BWA CAF CIV CMR COD COG COM CPV DJI ERI ETH GAB GHA GIN GMB GNB '
            'GNQ KEN LBR LSO MDG MDV MLI MOZ MRT MUS MWI NAM NER NGA RWA SDN SEN SLE SOM SSD '
            'STP SWZ SYC TCD TGO TZA UGA ZAF ZMB ZWE'
        ).split(),
        0.78: 'COK FJI FSM KIR MHL NRU PLW PNG SLB TKL TON TUV VUT WSM'.split(),
        0.97: 'ARG BOL BRA CHL COL ECU GUF GUY PER PRY SUR URY VEN'.split(),
    },
}

# Transcribed from `1. Model loop all data.do`, lines 84-91.
CONTINENT_GROUPS = {
    'AFRI': (
        'AGO BDI BEN BFA BWA CAF CIV CMR COD COG COM CPV DJI DZA EGY ERI ESH ETH GAB GHA '
        'GIN GMB GNB GNQ KEN LBR LBY LSO MAR MDG MDV MLI MOZ MRT MUS MWI NAM NER NGA RWA '
        'SDN SEN SLE SOM SSD STP SWZ SYC TCD TGO TUN TZA UGA ZAF ZMB ZWE'
    ).split(),
    'AMER': (
        'ARG ATG BLZ BOL BRA BRB CHL COL CRI CUB DMA DOM ECU GRD GTM GUF GUY HND HTI JAM '
        'KNA LCA MEX NIC PAN PER PRY SLV SUR TTO URY VCT VEN'
    ).split(),
    'ASIA': (
        'AFG ARM AZE BGD BTN CHN COK FJI FSM GEO IDN IND IRN IRQ JOR KAZ KGZ KHM KIR LAO '
        'LBN LKA MHL MMR MNG MYS NPL NRU OMN PAK PHL PLW PNG PRK PSE SLB SYR THA TJK TKL '
        'TKM TLS TON TUR TUV UZB VNM VUT WSM YEM'
    ).split(),
}

# Transcribed from `1. Model loop all data.do`, lines 61-75.
GENUS_BY_TYPE = {
    1: 'neev',
    2: 'brev',
    3: 'brde',
    4: 'neev',
    5: 'cunn',
    6: 'euca',
    7: 'nede',
    8: 'neev',
    9: 'pinu',
    10: 'brde',
    11: 'neev',
    12: 'brde',
    13: 'brev',
    14: 'brde',
    15: 'neev',
}

# Ordered source rules from `1. Model loop all data.do`, lines 93-171.
# Keep each original condition intact for the Stata-condition evaluator.
DEFAULT_ROOT_SHOOT_RATIO = 0.26
ROOT_RATIO_RULES = {
    'nr_rootshoot': (
        (0.825, 'fao_ecoz==11 & continent=="AFRI"'),
        (0.221, 'fao_ecoz==11 & continent=="AMER"'),
        (0.207, 'fao_ecoz==11 & continent=="ASIA"'),
        (0.232, 'fao_ecoz==12 & continent=="AFRI"'),
        (0.2845, 'fao_ecoz==12 & continent=="AMER"'),
        (0.323, 'fao_ecoz==12 & continent=="ASIA"'),
        (0.332, 'fao_ecoz==13 & continent=="AFRI"'),
        (0.334, 'fao_ecoz==13 & continent=="AMER"'),
        (0.44, 'fao_ecoz==13 & continent=="ASIA"'),
        (0.348, 'fao_ecoz==16 & continent=="AMER"'),
        (0.322, 'fao_ecoz==16 & continent=="ASIA"'),
        (0.232, 'fao_ecoz==21 & continent=="AFRI"'),
        (0.175, 'fao_ecoz==21 & continent=="AMER"'),
        (0.23, 'fao_ecoz==21 & continent=="ASIA"'),
        (0.336, 'fao_ecoz==22 & continent=="AMER"'),
        (0.44, 'fao_ecoz==22 & continent=="ASIA"'),
        (1.338, 'fao_ecoz==23 & continent=="AMER"'),
        (1.338, 'fao_ecoz==23 & continent=="ASIA"'),
        (0.466, 'fao_ecoz==31 & continent=="AMER" & genus=="brde" | genus=="nede"'),
        (0.337, 'fao_ecoz==31 & continent=="AMER" & genus=="pinu" | genus=="cunn" | genus=="brev" | genus=="neev"'),
        (0.225, 'fao_ecoz==31 & continent=="ASIA" & genus=="brde" | genus=="nede"'),
        (0.243, 'fao_ecoz==31 & continent=="ASIA" & genus=="pinu" | genus=="cunn" | genus=="brev" | genus=="neev"'),
        (0.237, 'fao_ecoz==32 & continent=="AMER" & genus=="pinu" | genus=="cunn" | genus=="brev" | genus=="neev"'),
        (0.225, 'fao_ecoz==32 & continent=="ASIA" & genus=="brde" | genus=="nede"'),
        (0.243, 'fao_ecoz==32 & continent=="ASIA" & genus=="pinu" | genus=="cunn" | genus=="brev" | genus=="neev"'),
    ),
    'pl_rootshoot': (
        (0.17, 'fao_ecoz==11 & continent=="AMER"'),
        (0.325, 'fao_ecoz==11 & continent=="ASIA"'),
        (2.158, 'fao_ecoz==16 & continent=="AMER"'),
        (2.158, 'fao_ecoz==23 & continent=="ASIA"'),
        (0.203, 'fao_ecoz==31 & continent=="AMER" & genus=="pinu" | genus=="cunn" | genus=="brev" | genus=="neev"'),
        (0.307, 'fao_ecoz==31 & continent=="ASIA" & genus=="brde" | genus=="nede"'),
        (0.224, 'fao_ecoz==31 & continent=="ASIA" & genus=="pinu" | genus=="cunn" | genus=="brev" | genus=="neev"'),
        (0.237, 'fao_ecoz==32 & continent=="AMER" & genus=="pinu" | genus=="cunn" | genus=="brev" | genus=="neev"'),
        (0.307, 'fao_ecoz==32 & continent=="ASIA" & genus=="brde" | genus=="nede"'),
        (0.224, 'fao_ecoz==32 & continent=="ASIA" & genus=="pinu" | genus=="cunn" | genus=="brev" | genus=="neev"'),
    ),
}
