import requests
import json
from collections import OrderedDict

sf_version = '32.0'

def create(sf_instance,headers,data):

    base_url = ('https://{instance}/services/data/v{sf_version}/sobjects/{object_name}/'
                             .format(instance=sf_instance,
                                     object_name='Contact',
                                     sf_version=sf_version))

    result = requests.request("post",base_url,headers = headers,data=json.dumps(data))
    return result

def describe(sf_instance,headers):
    base_url = ('https://{instance}/services/data/v{version}/'
                     .format(instance=sf_instance,
                             version=sf_version))
    url = base_url + "sobjects"
    result = requests.get(url, headers=headers)
    return result

def describeObject(sf_instance,headers):
    base_url = ('https://{instance}/services/data/v{version}/sobjects/'
                     .format(instance=sf_instance,
                             version=sf_version))
    url = base_url + "resource__c/describe"
    result = requests.get(url, headers=headers)
    return result.json(object_pairs_hook=OrderedDict)

def query(sf_instance,headers,query):
    base_url = ('https://{instance}/services/data/v{version}/'
                     .format(instance=sf_instance,
                             version=sf_version))

    url = base_url + 'query/'
    params = {'q': query}
    result = requests.get(url, headers=headers, params=params)
    return result.json(object_pairs_hook=OrderedDict)

def update(sf_instance,headers,recordId,data):
    base_url = ('https://{instance}/services/data/v{version}/sobjects'
                     .format(instance=sf_instance,
                             version=sf_version))

    url = base_url + '/TwitterObject__c/'+recordId
    result = requests.request('PATCH',url, headers=headers, data =json.dumps(data))
