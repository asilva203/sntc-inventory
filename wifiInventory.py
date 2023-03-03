# This script pulls down all the wireless product types from SNTC.
# It then maps the APs with the wireless controllers they are associated with
# and also provides an output of controllers that don't have any APs associated

from datetime import datetime
from sntc import SNTC
import os

# main function
def main():
    sntcObject = SNTC()
    custName = sntcObject.customerName
    netElements = sntcObject.getElements()
    inventory = sntcObject.getHardware(params={'productType':'Wireless'})
    controllerInv = {'unknown':{'swVersion':'unknown', 'productId':'unknown', 'APs':[]}}
    wifiElements = []

    for ne in netElements:
        if ne['productType'] == 'Wireless':
            wifiElements.append(ne)

    for e in wifiElements:
        if 'Controller' in e['productFamily']:
            controllerInv[e['neInstanceId']] = ''

    for e in inventory:
        if e['neInstanceId'] in controllerInv.keys():
            controllerInv[e['neInstanceId']] = e
            controllerInv[e['neInstanceId']]['APs'] = []
    
    for e in wifiElements:
        if 'Controller' in e['productFamily']:
            continue
        elif e['managedNeInstanceId'] in controllerInv.keys():
            controllerInv[e['managedNeInstanceId']]['APs'].append(e)
        else:
            controllerInv['unknown']['APs'].append(e)

    # Check for Output directory
    if not os.path.exists('Output'):
        os.mkdir('Output')
    else: pass

    noAps = open('Output/nowaps.csv','w')
    noAps.write('NE Instance ID,Hostname,Product ID,Serial,Version,Reachability\n')
    invFile = open('Output/{}-wirelessinventory-{}.csv'.format(custName,datetime.now().strftime('%Y%m%d%H%M%S')),'w')
    invFile.write('Name,PID,WLC Name,WLC Model,Version,Reachability\n')
    for controller in controllerInv:
        if controllerInv[controller]['APs']:
            for AP in controllerInv[controller]['APs']:
                invFile.write('{},{},{},{},{},{}\n'.format(AP['hostname'], AP['productId'], AP['sysName'],controllerInv[controller]['productId'],controllerInv[controller]['swVersion'],AP['reachabilityStatus']))
        else:
            if controller == 'unknown':
                pass
            else:
                for e in wifiElements:
                    if controller == e['neInstanceId']:
                        controllerInv[controller]['hostname'] = e['hostname']
                        controllerInv[controller]['reachabilityStatus'] = e['reachabilityStatus']
                        break
                    else: continue
                noAps.write('{},{},{},{},{},{}\n'.format(controllerInv[controller]['neInstanceId'],controllerInv[controller]['hostname'],controllerInv[controller]['productId'],controllerInv[controller]['serialNumber'],controllerInv[controller]['swVersion'],controllerInv[controller]['reachabilityStatus']))
    #print(json.dumps(controllerInv,indent=2))
    noAps.close()
    invFile.close()

main()