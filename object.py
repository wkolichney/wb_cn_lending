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

