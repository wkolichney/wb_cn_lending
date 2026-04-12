DOCUMENT_URL = 'https://search.worldbank.org/api/v3/wds'
PROJECT_URL = 'https://search.worldbank.org/api/v3/projects'


PROJECT_COLUMNS = [
    'id',
    'project_name',
    'countryshortname',
    'curr_ibrd_commitment',
    'idacommamt',
    'totalamt',
    'grantamt',
    'lendprojectcost',
    'boardapprovaldate',
    'closingdate',
    'envassesmentcategorycode'
]

COUNTRY_COLUMNS = [
    'countryshortname',
    'regionname'
]



MAJOR_SECTOR_COLUMNS = [
    'project_id',
    "major_sector_code",
    'major_sector_name'
]

SECTOR_COLUMNS = [
    'project_id',
    'sector_code',
    'sector_name',
    'sector_percent'
]

DOCUMENT_COLUMNS = [
    'id',               # document_id
    'docna',            # document_name (nested)
    'docty',            # document_type
    'prdln',            # prdln
    'lndinstr',         # lndinstr (nested)
    'docdt',            # docdt
    'datestored',       # datestored
    'disclosure_date',  # disclosure_date
    'last_modified_date', # last_modified_date
    'pdfurl',           # pdfurl
    'txturl',           # txturl
    'url',              # url
    'majdocty',         # maj_document_type
    'disclstat',        # disclstat
    'versiontyp',       # versiontype
    'authors',          # author (nested)
    'seccl',            # security_class
    'lang',             # lang
    'repnb',            # repnb
    'volnb',            # volnb
    'display_title',    # display_title
    'chronical_docm_id', # chronical_docm_id
    'guid',             # guid
    'owner',            # owner
    'projectid',        # project_id (FK)
]