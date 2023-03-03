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
    hardware = sntcObject.getHardware(params={'productType':'Switches'})
    #modules = sntcObject.getHardware(params={'productType':'Modules'})
    invData = {}
    # Pull in the pertinent information I want to see for the switches
    for item in hardware:
        invData[item['neInstanceId']] = {
            'Product Family':item['productFamily'],
            'Product Name':item['productName'],
            'Product ID':item['productId'],
            'Software':item['swVersion'],
            'Serial':item['serialNumber'],
            'Modules':[]
        }
        # Not sure if these are included or even applicable for what I want
        #   'Installed Memory':item['installedMemory'],
        #    'Installed Flash':item['installedFlash']
        #    }
    #for m in modules:
    #    if m['managedNeInstanceId'] in invData.keys():
    #        invData[m['managedNeInstanceId']]['Modules'].append(m)
    #    else: continue

    for element in netElements:
        if element['neInstanceId'] in invData.keys():
            invData[element['neInstanceId']]['IP Address'] = element['ipAddress']
            invData[element['neInstanceId']]['Hostname'] = element['hostname']
            invData[element['neInstanceId']]['Sys Name'] = element['sysName']
            invData[element['neInstanceId']]['Reachability'] = element['reachabilityStatus']
        else: continue
    
    #print(invData[638914054])
    #print(len(invData))

    # Check for Output directory
    if not os.path.exists('Output'):
        os.mkdir('Output')
    else: pass

    file = open('Output/{}-Switch Chassis-{}.csv'.format(custName,datetime.now().strftime('%Y%m%d%H%M%S')),'w')
    file.write('Switch Hostname,Sys Name,Product ID,Serial,Product Name,Product Family,Reachability\n'.format())
    for switch in invData:
        file.write('{},{},{},{},{},{},{}\n'.format(invData[switch]['Hostname'],invData[switch]['Sys Name'],invData[switch]['Product ID'],invData[switch]['Serial'],invData[switch]['Product Name'],invData[switch]['Product Family'],invData[switch]['Reachability']))

    file.close()
"""
    file = open('Output/{}-Switches-{}.csv'.format(custName,datetime.now().strftime('%Y%m%d%H%M%S')),'w')
    file.write('Hostname,Sys Name,Product Family,Product Name,Product ID,Serial,IP address,Software,Installed Memory,Installed Flash,Reachability\n')
    for router in invData:
        data = invData[router]
        file.write('{},{},{},{},{},{},{},{},{},{},{}\n'.format(data['Hostname'],data['Sys Name'],data['Product Family'],data['Product Name'],data['Product ID'],data['Serial'],data['IP Address'],data['Software'],data['Installed Memory'],data['Installed Flash'],data['Reachability']))
    
    file.close()
"""
main()