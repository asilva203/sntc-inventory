from datetime import datetime
from sntc import SNTC
import json
import os
import sys

def main():
    sntcObject = SNTC()
    custName = sntcObject.customerName
    # If there is an issue with returning everything
    # Try limiting the scope by adding "'hwType':'Chassis'" to the filter
    filter = {
        'snapshot':'LATEST'
    }
    print('Collecting covered assets...')
    coveredAssets = sntcObject.getCoverage(filter)
    print('Collecting uncovered assets...')
    uncoveredAssets = sntcObject.getNotCovered(filter)
    #print('Collecting contracts...')
    #contracts = sntcObject.getContracts(filter)
    print('Collecting hardware...')
    hw = sntcObject.getHardware(filter)
    print('Collecting network elements...')
    ne = sntcObject.getElements(filter)
    
    invData = {}
    hwInv = {}
    neInv = {}
    assets = {}
    for item in coveredAssets:
        assets[item['serialNumber']] = {
            'Contract Number':item['contractNumber'],
            'Coverage Status':item['coverageStatus'],
            'Service Level':item['serviceLevel'],
            'Coverage Start Date':item['coverageStartDate'].split('T')[0],
            'Coverage End Date':item['coverageEndDate'].split('T')[0],
            'Serial':item['serialNumber'],
            'neInstanceId':item['neInstanceId']
        }

    for item in uncoveredAssets:
        assets[item['serialNumber']] = {
            'Contract Number':'N/A',
            'Coverage Status':'INACTIVE',
            'Service Level':'N/A',
            'Coverage Start Date':'N/A',
            'Coverage End Date':'N/A',
            'Serial':item['serialNumber'],
            'neInstanceId':item['neInstanceId']
        }

    for item in hw:
        hwInv[item['serialNumber']] = item
    for item in ne:
        neInv[item['neInstanceId']] = item
    
    for asset in assets:
        neInstanceId = assets[asset]['neInstanceId']
        if asset in hwInv.keys():
            assets[asset]['Product Family'] = hwInv[asset]['productFamily']
            assets[asset]['Product ID'] = hwInv[asset]['productId']
            assets[asset]['Product Type'] = hwInv[asset]['productType']
        else:
            assets[asset]['Product Family'] = 'Unknown'
            assets[asset]['Product ID'] = 'Unknown'
            assets[asset]['Product Type'] = 'Unknown'
        if neInstanceId in neInv.keys():
            assets[asset]['Hostname'] = neInv[neInstanceId]['hostname']
            assets[asset]['Sys Name'] = neInv[neInstanceId]['sysName']
            assets[asset]['Create Date'] = neInv[neInstanceId]['createDate'].split('T')[0]
            assets[asset]['Reachability'] = neInv[neInstanceId]['reachabilityStatus']
        else:
            print('Asset {} not found in NE inventory'.format(asset))

    file = open('Output/{}-Coverage-{}.csv'.format(custName,datetime.now().strftime('%Y%m%d%H%M%S')),'w')
    file.write('Parent Hostname,Parent Sys Name,Product Family,PID,Product Type,Serial,Coverage Status,Service Level,Contract Number,Coverage Start Date,Coverage End Date,First Seen,Reachability\n')
    for asset in assets:
        file.write('{},{},{},{},{},{},{},{},{},{},{},{},{}\n'.format(assets[asset]['Hostname'],assets[asset]['Sys Name'],assets[asset]['Product Family'],assets[asset]['Product ID'],assets[asset]['Product Type'],assets[asset]['Serial'],assets[asset]['Coverage Status'],assets[asset]['Service Level'],assets[asset]['Contract Number'],assets[asset]['Coverage Start Date'],assets[asset]['Coverage End Date'],assets[asset]['Create Date'],assets[asset]['Reachability']))
    file.close()
    #for asset in assets:
    #    print(json.dumps(assets[asset],indent=2))
    sys.exit(0)
    # Create the inventory dictionary based on neInstanceID
    for item in hw:
        if item['serialNumber'] == None:
            continue
        else:
            invData[item['serialNumber']] = {
                'neInstanceId':item['neInstanceId'],
                'Product Family':item['productFamily'],
                'Product Name':item['productName'],
                'Product ID':item['productId'],
                'Software':item['swVersion'],
                'Serial':item['serialNumber']
            }
    

    for item in coveredAssets:
        if item['serialNumber'] in invData.keys():
            invData[item['serialNumber']]['Contract Number'] = item['contractNumber']
            invData[item['serialNumber']]['Coverage Status'] = item['coverageStatus']
            invData[item['serialNumber']]['Coverage Start Date'] = item['coverageStartDate'].split('T')[0]
            invData[item['serialNumber']]['Coverage End Date'] = item['coverageEndDate'].split('T')[0]
        else:
            print('Serial {} not found for Covered PID {}'.format(item['serialNumber'],item['productId']))
        #if invData[item]['Serial'] == None:
        #    print(json.dumps(invData[item],indent=2))
    for item in uncoveredAssets:
        if item['serialNumber'] in invData.keys():
            invData[item['serialNumber']]['Contract Number'] = 'N/A'
            invData[item['serialNumber']]['Coverage Status'] = 'INACTIVE'
            invData[item['serialNumber']]['Coverage Start Date'] = 'N/A'
            invData[item['serialNumber']]['Coverage End Date'] = 'N/A'
        else:
            print('Serial {} not found for Uncovered PID {}'.format(item['serialNumber'],item['productId']))

    file = open('Output/{}-Coverage-{}.csv'.format(custName,datetime.now().strftime('%Y%m%d%H%M%S')),'w')
    file.write('Parent Hostname,Parent Sys Name,Product Family,PID,Serial,Coverage Status,Contract Number,Contract Start Date,Contract End Date\n')
    for item in invData:
        if invData[item]['neInstanceId'] in neInv.keys():
            neInvKey = invData[item]['neInstanceId']
            file.write('{},{},{},{},{},{},{},{},{}\n'.format(neInv[neInvKey]['hostname'],neInv[neInvKey]['sysName'],invData[item]['Product Family'],invData[item]['Product ID'],invData[item]['Serial'],invData[item]['Coverage Status'],invData[item]['Contract Number'],invData[item]['Coverage Start Date'],invData[item]['Coverage End Date']))
            #print(json.dumps(invData[item],indent=2))
        else:
            print('item not found in network elements')
    file.close()
main()