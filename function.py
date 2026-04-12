import requests
import json
import pandas as pd
import wbgapi as wb
import time


def get_project(url, rows, os=0, retries=5):
    url = 'https://search.worldbank.org/api/v3/projects'
    url = f"{url}?format=json&rows={rows}&os={os}"
    for attempt in range(retries):
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            print(f'Error {response.status_code} at os={os}, attempt {attempt+1}/{retries}')
            time.sleep(15)  # wait before retrying
    return None


def get_document(project_id, retries=5):
    documents_url = 'https://search.worldbank.org/api/v3/wds'
    url = f"{documents_url}?format=json&rows=50&projectid={project_id}"
    for attempt in range(retries):
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            # warn if project has more docs than we fetched
            total = int(data.get('total', 0))
            if total > 50:
                print(f"Warning: {project_id} has {total} docs, only fetched 50")
            return data
        else:
            wait = 5 ** attempt
            print(f'Error {response.status_code} for {project_id}, attempt {attempt+1}/{retries}, waiting {wait}s')
            time.sleep(wait)
    return None


def get_document_bulk(rows, os=0, retries=3):
    documents_url = 'https://search.worldbank.org/api/v3/wds'
    url = f"{documents_url}?format=json&rows={rows}&os={os}"
    for attempt in range(retries):
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            wait = 2 ** attempt
            print(f'Error {response.status_code} at os={os}, attempt {attempt+1}/{retries}, waiting {wait}s')
            time.sleep(wait)
    return None



def parse_sector_data(project_id, sector_list):
    major_sectors = []
    sectors = []
    
    for item in sector_list:
        ms = item['major_sector']
        
        # row for project_major_sectors table
        major_sectors.append({
            'project_id': project_id,
            'major_sector_code': ms['major_sector_code'],
            'major_sector_name': ms['major_sector_name']  # for lookup table too
        })
        
        # rows for project_sectors table
        for sector in ms['sectors']:
            sectors.append({
                'project_id': project_id,
                'major_sector_code': ms['major_sector_code'],  # to link back
                'sector_code': sector['sector_code'],
                'sector_name': sector['sector_name'],          # for lookup table too
                'sector_percent': sector['sector_percent']
            })
    
    return major_sectors, sectors

