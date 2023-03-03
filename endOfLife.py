from datetime import datetime
from sntc import SNTC
from eox import EOX
import json
import os

def main():
    sntcObject = SNTC()
    custName = sntcObject.customerName
    # If there is an issue with returning everything
    # Try limiting the scope by adding "'hwType':'Chassis'" to the filter
    filter = {
        'snapshot':'LATEST'
    }
    eolChassis = sntcObject.getHardwareEol(filter)
    print(len(eolChassis))
    hwInv = {}
    neInv = {}
    eolInventory = {}

    for item in eolChassis:
        # I don't care if the next milestone is EoSale or Announced
        # Commenting out to see if maybe this comes in handy
        #if item['nextHwEolMilestone'] in ['EoSale','Announced']:
        #    continue
        # Include Items that are currently LDoS
        if item['currentHwEolMilestone'] == 'LDoS':
            if item['hwInstanceId'] in eolInventory.keys():
                # Skip if there is no product ID
                if item['productId'] == None:
                    continue
                else:
                    for key in item.keys():
                        # If the item already exists in the inventory, skip
                        if item[key] == eolInventory[item['hwInstanceId']]['eolData'][key]:
                            continue
                        else:
                            eolInventory[item['hwInstanceId']]['eolData'][key] += ',{}'.format(item[key])

            else:
                eolInventory[item['hwInstanceId']] = {'eolData': item}
                eolInventory[item['hwInstanceId']]['eolData']['nextHwEolMilestone'] = 'Already LDoS'
                eolInventory[item['hwInstanceId']]['eolData']['nextHwEolMilestoneDate'] = item['currentHwEolMilestoneDate']
        # Look forward for two or three years, may need to refactor this and just filter in the file
        elif item['nextHwEolMilestoneDate']:
            if item['nextHwEolMilestoneDate'].split('-')[0] in ['2022','2023','2024','2025','2026','2027','2028','2029','2030']:
                if item['hwInstanceId'] in eolInventory.keys():
                    for key in item.keys():
                        if item[key] == eolInventory[item['hwInstanceId']]['eolData'][key]:
                            continue
                        else:
                            if type(eolInventory[item['hwInstanceId']]['eolData'][key]) == str:
                                eolInventory[item['hwInstanceId']]['eolData'][key] += ',{}'.format(item[key])
                            else:
                                eolInventory[item['hwInstanceId']]['eolData'][key] = '{},{}'.format(str(eolInventory[item['hwInstanceId']]['eolData'][key]),str(item[key]))
                            #eolInventory[item['hwInstanceId']]['eolData'][key] += ',{}'.format(item[key])
                else:
                    eolInventory[item['hwInstanceId']] = {'eolData': item}
    
    # Gather all hardware and Network elements for processing
    newHw = sntcObject.getHardware()
    newNe = sntcObject.getElements()

    # Make inventories of each one
    for item in newHw:
        hwInv[item['hwInstanceId']] = item
    for item in newNe:
        neInv[item['neInstanceId']] = item
    
    # Update the EoL Inventory list with some additional fields
    for item in eolInventory:
        if item in hwInv.keys():
            eolInventory[item]['hwProductId'] = hwInv[item]['productId']
            eolInventory[item]['serialNumber'] = hwInv[item]['serialNumber']
            eolInventory[item]['parentId'] = hwInv[item]['managedNeInstanceId']
            eolInventory[item]['productType'] = hwInv[item]['productType']
            eolInventory[item]['productFamily'] = hwInv[item]['productFamily']
            eolInventory[item]['parentName'] = neInv[eolInventory[item]['parentId']]['sysName']
            eolInventory[item]['Reachability'] = neInv[eolInventory[item]['parentId']]['reachabilityStatus']
            if type(eolInventory[item]['eolData']['currentHwEolMilestone']) == str:
                eolInventory[item]['eolData']['currentHwEolMilestone'] = ','.join(sorted(eolInventory[item]['eolData']['currentHwEolMilestone'].split(',')))
            else: pass
            if type(eolInventory[item]['eolData']['nextHwEolMilestone']) == str:
                eolInventory[item]['eolData']['nextHwEolMilestone'] = ','.join(sorted(eolInventory[item]['eolData']['nextHwEolMilestone'].split(',')))
            else: pass
        else:
            eolInventory[item]['hwProductId'] = 'Unknown'
            eolInventory[item]['serialNumber'] = 'Unknown'
            eolInventory[item]['parentId'] = 'Unknown'
            eolInventory[item]['productType'] = 'Unknown'
            eolInventory[item]['productFamily'] = 'Unknown'
            eolInventory[item]['parentName'] = 'Unknown'
            eolInventory[item]['Reachability'] = 'Unknown'
    
    # Check for Output directory
    if not os.path.exists('Output'):
        os.mkdir('Output')
    else: pass

    # Collect all the PIDs to send to the EoX class
    pidSet = set()
    for item in eolInventory:
        pidSet.add(eolInventory[item]['eolData']['productId'])
    print(pidSet)
    services = EOX()
    eoxDict = services.getEoxData(pidSet)

    file = open('Output/{}-EoL-{}.csv'.format(custName,datetime.now().strftime('%Y%m%d%H%M%S')),'w')
    file.write('Parent,Parent ID,Hardware PID,EoL PID,Product Type,Product Family,Serial Number,Next EoL Milestone,Next EoL Milestone Date,Current EoL Milestone,Current EoL Milestone Date,LDoS Date,Replacement PID,EoL Link,Reachability\n')
    for item in eolInventory:
        ldosDate = ''
        replacement = ''
        eolLink = ''
        pid = eolInventory[item]['eolData']['productId']
        if pid in eoxDict.keys():
            if eoxDict[pid]['LastDateOfSupport']['value']:
                m = eoxDict[pid]['LastDateOfSupport']['value'].split('-')[1]
                d = eoxDict[pid]['LastDateOfSupport']['value'].split('-')[2]
                y = eoxDict[pid]['LastDateOfSupport']['value'].split('-')[0]
                ldosDate = '{}/{}/{}'.format(m,d,y)
            else:
                ldosDate = 'Unknown'
            if eoxDict[pid]['EOXMigrationDetails']['MigrationProductId']:
                replacement = eoxDict[pid]['EOXMigrationDetails']['MigrationProductId']
            elif eoxDict[pid]['EOXMigrationDetails']['MigrationProductName']:
                if '\n' in eoxDict[pid]['EOXMigrationDetails']['MigrationProductName']:
                    eoxDict[pid]['EOXMigrationDetails']['MigrationProductName'] = eoxDict[pid]['EOXMigrationDetails']['MigrationProductName'].replace('\n','--')
                else: pass 
                replacement = eoxDict[pid]['EOXMigrationDetails']['MigrationProductName']
            else:
                replacement = 'Unknown'
            if eoxDict[pid]['LinkToProductBulletinURL']:
                eolLink = eoxDict[pid]['LinkToProductBulletinURL']
            else:
                eolLink = 'Unknown'
        else:
            ldosDate = 'Unknown'
            replacement = 'Unknown'
            eolLink = 'Unknown'

        file.write('{},{},{},{},{},{},{},"{}","{}","{}","{}",{},{},{},{}\n'.format(
            eolInventory[item]['parentName'],
            eolInventory[item]['parentId'],
            eolInventory[item]['hwProductId'],
            eolInventory[item]['eolData']['productId'],
            eolInventory[item]['productType'],
            eolInventory[item]['productFamily'],
            eolInventory[item]['serialNumber'],
            eolInventory[item]['eolData']['nextHwEolMilestone'],
            eolInventory[item]['eolData']['nextHwEolMilestoneDate'],
            eolInventory[item]['eolData']['currentHwEolMilestone'],
            eolInventory[item]['eolData']['currentHwEolMilestoneDate'],
            ldosDate,
            replacement,
            eolLink,
            eolInventory[item]['Reachability']
            ))

    file.close()

    print('DONE!!!')



main()