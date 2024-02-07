from datetime import datetime
from classes.sntc import SNTC
from classes.support import Support
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
    print('Gathering EOL Hardware')
    eolChassis = sntcObject.getHardwareEol(filter)
    print('Done!')
    print('{} objects found'.format(len(eolChassis)))
    hwInv = {}
    neInv = {}
    eolInventory = {}

    for item in eolChassis:
        # Include Items that are currently LDoS
        if item['currentHwEolMilestone'] == 'LDoS':
            # Check to see if the hardware instance ID is already in my keys
            # If it is, check to see if the product ID exists, and skip if it does not
            if item['hwInstanceId'] in eolInventory.keys():
                if item['productId'] == None:
                    continue
                else:
                    for key in item.keys():
                        if item[key] == eolInventory[item['hwInstanceId']]['eolData'][key]:
                            continue
                        else:
                            eolInventory[item['hwInstanceId']]['eolData'][key] += ',{}'.format(item[key])
            # If the hardware instance ID is not in the inventory, populate it
            # and update the next milestone to be "Already LDOS" with the LDOS date
            else:
                eolInventory[item['hwInstanceId']] = {'eolData': item}
                eolInventory[item['hwInstanceId']]['eolData']['nextHwEolMilestone'] = 'Already LDoS'
                eolInventory[item['hwInstanceId']]['eolData']['nextHwEolMilestoneDate'] = item['currentHwEolMilestoneDate']
        # Check to see if the remaining hardware instance IDs are in the inventory
        # If it is, check to see if the data is the same or not
        elif item['hwInstanceId'] in eolInventory.keys():
            for key in item.keys():
                # If the data is the same, continue to the next key
                if item[key] == eolInventory[item['hwInstanceId']]['eolData'][key]:
                    continue
                # If the data is not the same, add the additional string, or other data to the field
                else:
                    if type(eolInventory[item['hwInstanceId']]['eolData'][key]) == str:
                        eolInventory[item['hwInstanceId']]['eolData'][key] += ',{}'.format(item[key])
                    else:
                        eolInventory[item['hwInstanceId']]['eolData'][key] = '{},{}'.format(str(eolInventory[item['hwInstanceId']]['eolData'][key]),str(item[key]))
        # Finally simply populate the data if it's not there
        else:
            eolInventory[item['hwInstanceId']] = {'eolData': item}

    # Gather all hardware and Network elements for processing
    print('Gathering Hardware...')
    newHw = sntcObject.getHardware()
    print('Done!')
    print('{} Hardware elements found'.format(len(newHw)))
    print('Gathering Network Elements...')
    newNe = sntcObject.getElements()
    print('Done!')
    print('{} Network elements found'.format(len(newNe)))

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
    #print(pidSet)
    services = Support()
    eoxDict = services.getEoxData(pidSet)

    file = open('Output/{}-EoL-{}.csv'.format(custName,datetime.now().strftime('%Y%m%d%H%M%S')),'w')
    file.write('Parent,Parent ID,Hardware PID,EoL PID,Product Type,Product Family,Serial Number,Next EoL Milestone,Next EoL Milestone Date,Current EoL Milestone,Current EoL Milestone Date,EoVulnerability Date,LDoS Date,Replacement PID,EoL Link,Reachability\n')
    for item in eolInventory:
        ldosDate = ''
        eovulnDate = ''
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
                eovulnDate = 'Unknown'
            if eoxDict[pid]['EndOfSecurityVulSupportDate']['value']:
                m = eoxDict[pid]['EndOfSecurityVulSupportDate']['value'].split('-')[1]
                d = eoxDict[pid]['EndOfSecurityVulSupportDate']['value'].split('-')[2]
                y = eoxDict[pid]['EndOfSecurityVulSupportDate']['value'].split('-')[0]
                eovulnDate = '{}/{}/{}'.format(m,d,y)
            else:
                eovulnDate = 'Unknown'
            
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

        file.write('{},{},{},{},{},{},{},"{}","{}","{}","{}",{},{},"{}",{},{}\n'.format(
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
            eovulnDate,
            ldosDate,
            replacement,
            eolLink,
            eolInventory[item]['Reachability']
            ))

    file.close()

    print('DONE!!!')
    
main()