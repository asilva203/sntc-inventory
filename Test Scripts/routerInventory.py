# This script goes in and collects the routers from the selected inventory
# and the creates a CSV of the name, serial, IP, model, sofware version, and reachability status
from datetime import datetime
from sntc import SNTC
import os

def main():
    myInventory = {}
    parentSet = set()
    sntcObject = SNTC()
    custName = sntcObject.customerName
    netElements = sntcObject.getElements()
    hardware = sntcObject.getHardware(params={'productType':'Routers'})
    invData = {}
    for item in hardware:
        invData[item['neInstanceId']] = {
            'Product Family':item['productFamily'],
            'Product Name':item['productName'],
            'Product ID':item['productId'],
            'Software':item['swVersion'],
            'Serial':item['serialNumber'],
            'Installed Memory':item['installedMemory'],
            'Installed Flash':item['installedFlash']
            }
    for element in netElements:
        if element['neInstanceId'] in invData.keys():
            invData[element['neInstanceId']]['IP Address'] = element['ipAddress']
            invData[element['neInstanceId']]['Hostname'] = element['hostname']
            invData[element['neInstanceId']]['Sys Name'] = element['sysName']
            invData[element['neInstanceId']]['Reachability'] = element['reachabilityStatus']
        else: continue

    # Check for Output directory
    if not os.path.exists('Output'):
        os.mkdir('Output')
    else: pass

    file = open('Output/{}-Routers-{}.csv'.format(custName,datetime.now().strftime('%Y%m%d%H%M%S')),'w')
    file.write('Hostname,Sys Name,Product Family,Product Name,Product ID,Serial,IP address,Software,Installed Memory,Installed Flash,Reachability\n')
    for router in invData:
        data = invData[router]
        file.write('{},{},{},{},{},{},{},{},{},{},{}\n'.format(data['Hostname'],data['Sys Name'],data['Product Family'],data['Product Name'],data['Product ID'],data['Serial'],data['IP Address'],data['Software'],data['Installed Memory'],data['Installed Flash'],data['Reachability']))
    
    file.close()

main()