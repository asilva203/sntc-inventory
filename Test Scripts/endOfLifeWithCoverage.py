from contextlib import nullcontext
from datetime import datetime
from sntc import SNTC
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
    print('Gathering end of life data...')
    eolChassis = sntcObject.getHardwareEol(filter)
    print('Complete')
    print(len(eolChassis))

    eolInventory = {}

    for item in eolChassis:
        # I don't care if the next milestone is EoSale or Announced
        if item['nextHwEolMilestone'] in ['EoSale','Announced']:
            continue
        # Include Items that are currently LDoS
        elif item['currentHwEolMilestone'] == 'LDoS':
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
            if item['nextHwEolMilestoneDate'].split('-')[0] in ['2022','2023','2024']:
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
    
    # Gather all hardware and Network elements and coverage for processing
    print('Gathering Hardware...')
    newHw = sntcObject.getHardware()
    print('Gathering Elements...')
    newNe = sntcObject.getElements()
    print('Gathering covered assets...')
    covered = sntcObject.getCoverage()
    print('Gathering uncovered assets...')
    notCovered = sntcObject.getNotCovered()
    print('Complete')
    hwInv = {}
    neInv = {}
    coveredInv = {}
    notCoveredInv = {}

    # Make inventories of each one
    for item in newHw:
        hwInv[item['hwInstanceId']] = item
    for item in newNe:
        neInv[item['neInstanceId']] = item
    for item in covered:
        coveredInv[item['serialNumber']] = item
    for item in notCovered:
        notCoveredInv[item['serialNumber']] = item
    
    # Update the EoL Inventory list with some additional fields
    for item in eolInventory:
        if item in hwInv.keys():
            eolInventory[item]['hwProductId'] = hwInv[item]['productId']
            eolInventory[item]['serialNumber'] = hwInv[item]['serialNumber']
            eolInventory[item]['neInstanceId'] = hwInv[item]['neInstanceId']
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
    
    # Try to fill in any coverage data
    for item in eolInventory:
        if eolInventory[item]['serialNumber'] in coveredInv.keys():
            eolInventory[item]['Coverage'] = coveredInv[eolInventory[item]['serialNumber']]
        elif eolInventory[item]['serialNumber'] in notCoveredInv.keys():
            eolInventory[item]['Coverage'] = {
                'coverageStatus':'Not Covered',
                'serviceLevel':'Not Covered',
                'contractNumber':'Not Covered',
                }
        else:
            eolInventory[item]['Coverage'] = {
                'coverageStatus':'Missing',
                'serviceLevel':'Missing',
                'contractNumber':'Missing',
                }
    # Check for Output directory
    if not os.path.exists('Output'):
        os.mkdir('Output')
    else: pass

    file = open('Output/{}-EoL-{}.csv'.format(custName,datetime.now().strftime('%Y%m%d%H%M%S')),'w')
    file.write('Parent,Parent ID,Hardware PID,EoL PID,Product Type,Product Family,Serial Number,Next EoL Milestone,Next EoL Milestone Date,Current EoL Milestone,Current EoL Milestone Date,Coverage Status,Service Level,Contract Number,Reachability\n')
    for item in eolInventory:
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
            eolInventory[item]['Coverage']['coverageStatus'],
            eolInventory[item]['Coverage']['serviceLevel'],
            eolInventory[item]['Coverage']['contractNumber'],
            eolInventory[item]['Reachability']
            ))

    file.close()

    print('DONE!!!')

main()