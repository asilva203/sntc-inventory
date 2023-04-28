from classes.sntc import SNTC
from datetime import datetime
import json
import sys
import requests

def listProductTypes(hwTypes):
    options = {}
    i = 1
    for item in hwTypes:
        if item == None:
            continue
        else:
            options[i] = item
            print('{}: {}'.format(i, item))
            i += 1
    options[i] = 'All'
    print('{}: {}'.format(i, options[i]))

    return options

def selectProductType(hwTypes):
    hwList = listProductTypes(hwTypes)
    selection = input('Select Product Type: ')

    try:
        int(selection)
    except:
        print('Invalid Entry\n')
        return selectProductType(hwTypes)
    
    try:
        pType = hwList[int(selection)]
    except:
        print('Invalid Selection\n')
        return selectProductType(hwTypes)
    
    return pType



def main():
    # Create the SNTC object
    sntcObject = SNTC()
    custName = sntcObject.customerName
    # Filter only to the latest snapshot and my selection
    filter = {
        'snapshot':'LATEST',
        'hwType':'Chassis'
    }

    # Get all of the network elements first, since I can't filter this by Product Type
    print('Getting Network Elements')
    ne = sntcObject.getElements(filter)
    print('Done!')

    # Create a set for Product types, then pick which ones to filter by
    hwTypes = set()
    for item in ne:
        hwTypes.add(item['productType'])
    productType = selectProductType(hwTypes)
    if productType == 'All':
        pass
    else:
        filter['productType'] = productType
    
    # Gather all of the network hardware according to my Product Type
    print('Getting Network Hardware...')
    hw = sntcObject.getHardware(filter)
    print('Done!')

    # Create inventories based on what I have from network hardware and elements
    hwInv = {}
    neInv = {}

    for item in hw:
        hwInv[item['hwInstanceId']] = item
    for item in ne:
        neInv[item['neInstanceId']] = item
    
    # Add the additional data from the network inventory to the hardware inventory
    for instance in hwInv:
        hwInv[instance]['hostname'] = neInv[hwInv[instance]['neInstanceId']]['hostname']
        hwInv[instance]['ipAddress'] = neInv[hwInv[instance]['neInstanceId']]['ipAddress']
        hwInv[instance]['reachabilityStatus'] = neInv[hwInv[instance]['neInstanceId']]['reachabilityStatus']
    

    file = open('Output/{}-chassisInventory-{}.csv'.format(custName,datetime.now().strftime('%Y%m%d%H%M%S')),'w')
    file.write('Hostname,IP Address,Instance ID,Product Type,Product Family,Product Name,Product ID,Software Version,Serial Number,Reachability\n')
    for item in hwInv:
        file.write('{},{},{},{},{},"{}",{},"{}",{},{}\n'.format(
            hwInv[item]['hostname'],
            hwInv[item]['ipAddress'],
            hwInv[item]['neInstanceId'],
            hwInv[item]['productType'],
            hwInv[item]['productFamily'],
            hwInv[item]['productName'],
            hwInv[item]['productId'],
            hwInv[item]['swVersion'],
            hwInv[item]['serialNumber'],
            hwInv[item]['reachabilityStatus']
        ))
    file.close()
    print('DONE!')

    

main()
