# This script pulls down all the wireless product types from SNTC.
# It then maps the APs with the wireless controllers they are associated with
# and also provides an output of controllers that don't have any APs associated

from datetime import datetime
from classes.sntc import SNTC
import os
import json

def main():
    sntcObject = SNTC()
    custName = sntcObject.customerName
    print('Gathering all Network Elements')
    netElements = sntcObject.getElements()
    print('Done!!!')
    # Don't need this after refactoring
    #netHardware = sntcObject.getHardware(params={'productType':'Wireless'})
    controllerInv = {'unknown':{'swVersion':'unknown', 'productId':'unknown', 'APs':[]}}
    wifiElements = []
    
    # Pull out only the wireless product type, even though the filter should have
    # already taken care of this
    for element in netElements:
        if element['productType'] == 'Wireless':
            wifiElements.append(element)

    # Look for only products that are a "Controller".  Assign the instance ID as the key
    for element in wifiElements:
        if 'Controller' in element['productFamily']:
            controllerInv[element['neInstanceId']] = element
            controllerInv[element['neInstanceId']]['APs'] = []

    # Go through all the wifi elements to associate the APs with the respective controllers
    for element in wifiElements:
        # If the element is a controller, we don't care, already inventoried
        if 'Controller' in element['productFamily']:
            continue
        # If the managed NE instance ID is a controller, add the AP to the AP list
        elif element['managedNeInstanceId'] in controllerInv.keys():
            controllerInv[element['managedNeInstanceId']]['APs'].append(element)
        else:
            controllerInv['unknown']['APs'].append(element)

    # Check for Output directory
    if not os.path.exists('Output'):
        os.mkdir('Output')
    else: pass

    # Output for WLCs with no APs
    noAps = open('Output/nowaps.csv','w')
    noAps.write('NE Instance ID,Hostname,Product ID,Version,Reachability\n')

    # Output for WLCs with Access Points
    invFile = open('Output/{}-wirelessinventory-{}.csv'.format(custName,datetime.now().strftime('%Y%m%d%H%M%S')),'w')
    invFile.write('Name,PID,WLC Name,WLC Model,Version,Reachability\n')

    # Write my output files
    for controller in controllerInv:
        if controllerInv[controller]['APs']:
            for AP in controllerInv[controller]['APs']:
                invFile.write('{},{},{},{},{},{}\n'.format(AP['hostname'], AP['productId'], AP['sysName'],controllerInv[controller]['productId'],controllerInv[controller]['swVersion'],AP['reachabilityStatus']))
        else:
            if controller == 'unknown':
                pass
            else:
                for element in wifiElements:
                    if controller == element['neInstanceId']:
                        controllerInv[controller]['hostname'] = element['hostname']
                        controllerInv[controller]['reachabilityStatus'] = element['reachabilityStatus']
                        break
                    else: continue
                noAps.write('{},{},{},{},{}\n'.format(controllerInv[controller]['neInstanceId'],controllerInv[controller]['hostname'],controllerInv[controller]['productId'],controllerInv[controller]['swVersion'],controllerInv[controller]['reachabilityStatus']))
                # Original write line
                #oAps.write('{},{},{},{},{},{}\n'.format(controllerInv[controller]['neInstanceId'],controllerInv[controller]['hostname'],controllerInv[controller]['productId'],controllerInv[controller]['serialNumber'],controllerInv[controller]['swVersion'],controllerInv[controller]['reachabilityStatus']))

    # Close the Files
    noAps.close()
    invFile.close()

main()

