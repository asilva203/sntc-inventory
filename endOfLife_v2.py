# New End of Life Script that takes hardware invenotry from SNTC
# and pulls end of life data from the EOX API instead of the 
# SNTC Collector
from datetime import datetime
from classes.sntc import SNTC
from classes.support import Support
import json
import os
import platform
import subprocess
import sys

# Fix data for things already LDoS so that we have dates for everything
def correctAlreadyLdos(eolData):
    for item in eolData:
        # First we search for anything that is already LDoS
        if item['currentHwEolMilestone'] == 'LDoS':
            # If the Hardware is LDoS, we simply need to update the next milestone and milestone date
            item['nextHwEolMilestone'] = 'Already LDoS'
            item['nextHwEolMilestoneDate'] = item['currentHwEolMilestoneDate']
        else: continue

    return

# Fix the data for things that are missing an End of Vulnerability Support date
# If one is not listed, we will just make it the same as the LDoS date
def correctMissingEoVuln(eolBulletins):
    for item in eolBulletins:
        # Check to see if there is an End of Vulnerability Support date in the bulletin info
        if item['eoVulnerabilitySecuritySupport'] == None:
            # If there is not, simply make it the Last Day of Support date
            item['eoVulnerabilitySecuritySupport'] = item['lastDateOfSupport']
        else: continue

    return

def fixEoxData(eoxData):
    #normalize/fix the EOX data to only have a single list entry for every item
    for pid in eoxData.copy():
        # First check to see if the length is one
        if len(eoxData[pid]) == 1:
            # If it is, check to see if the entry has the EOXError item, and pop the whole thing if it does
            if 'EOXError' in eoxData[pid][0].keys():
                eoxData.pop(pid)
            # If we don't have an EoVSS date, we will just use the LDoS Date
            elif not eoxData[pid][0]['EndOfSecurityVulSupportDate']['value']:
                eoxData[pid][0]['EndOfSecurityVulSupportDate']['value'] = eoxData[pid][0]['LastDateOfSupport']['value']
        
        # If the length is greater than 1, we will use the product bulletin number to determine if there is duplicate data
        # If data is duplicated, the only difference is possibly the Migration information
        else:
            bulletinNumber = eoxData[pid][0]['ProductBulletinNumber']
            for item in eoxData[pid][:]:
                # If it is the first time iterating through the list, the index will be 0
                # The only thing we really need to do here is fix the EoVSS date, if we need to
                if eoxData[pid].index(item) == 0:
                    if not eoxData[pid][0]['EndOfSecurityVulSupportDate']['value']:
                        eoxData[pid][0]['EndOfSecurityVulSupportDate']['value'] = eoxData[pid][0]['LastDateOfSupport']['value']
                # We then compare the bulletin number
                else:
                    # If it matches, we add the new migration data to the 0 index, then pop out the item in the list
                    if item['ProductBulletinNumber'] == bulletinNumber:
                        eoxData[pid][0]['EOXMigrationDetails']['MigrationInformation'] += ' or {}'.format(item['EOXMigrationDetails']['MigrationInformation'])
                        eoxData[pid][0]['EOXMigrationDetails']['MigrationProductId'] += ' or {}'.format(item['EOXMigrationDetails']['MigrationProductId'])
                        eoxData[pid].pop(eoxData[pid].index(item))


def getProductMigrationDetails(eoxData):
    migInventory = {}
    for pid in eoxData:
            migInventory[pid] = {'EOXMigrationDetails': {'MigrationInformation':'','MigrationProductId':''}}
            for entry in eoxData[pid]:
                migInventory[pid]['EOXMigrationDetails']['MigrationInformation'] += '{} or '.format(entry['EOXMigrationDetails']['MigrationInformation'])
                migInventory[pid]['EOXMigrationDetails']['MigrationProductId'] += '{} or '.format(entry['EOXMigrationDetails']['MigrationProductId'])
            migInventory[pid]['EOXMigrationDetails']['MigrationInformation'] = migInventory[pid]['EOXMigrationDetails']['MigrationInformation'][:-4]
            migInventory[pid]['EOXMigrationDetails']['MigrationProductId'] = migInventory[pid]['EOXMigrationDetails']['MigrationProductId'][:-4]
    
    return migInventory

# This is not well done, but it's enough to make the data really easy to work with
# With Baylor data, only three elements are not accounted for with this terrible code
def fixHwEolData(eolInventory):
    # First time through will just delete useless entries
    for hwid in eolInventory:
        # I only need to make adjustments if the length of this is greater than 1
        if len(eolInventory[hwid]['hwEolData']) > 1:
            # First delete everything that has a useless entry
            for entry in eolInventory[hwid]['hwEolData'][:]:
                if not entry['currentHwEolMilestone'] and not entry['currentHwEolMilestoneDate'] and not entry['nextHwEolMilestone'] and not entry['nextHwEolMilestoneDate']:
                    eolInventory[hwid]['hwEolData'].pop(eolInventory[hwid]['hwEolData'].index(entry))

    # This loop will look for entries that have 2 elements and compares the two
    # If the checks pass, the entries are the same and things just get updated
    for hwid in eolInventory:
        # We will compare the hwEolInstanceId and NE Instance ID in order to determine if the bulletin data and milestones are the same
        # For this loop, we only care about items that have two entries
        if len(eolInventory[hwid]['hwEolData']) == 2:
            for entry in eolInventory[hwid]['hwEolData'][:]: 
                if eolInventory[hwid]['hwEolData'].index(entry) == 0:
                    hwEolInstanceId = entry['hwEolInstanceId']
                    neInstanceId = entry['neInstanceId']
                else:
                    if entry['neInstanceId'] == neInstanceId and entry['hwEolInstanceId'] == hwEolInstanceId:
                        if eolInventory[hwid]['hwEolData'][0]['currentHwEolMilestone'] != entry['currentHwEolMilestone']:
                            eolInventory[hwid]['hwEolData'][0]['currentHwEolMilestone'] += ',{}'.format(entry['currentHwEolMilestone'])
                            eolInventory[hwid]['hwEolData'][0]['currentHwEolMilestone'] = ','.join(sorted(eolInventory[hwid]['hwEolData'][0]['currentHwEolMilestone'].split(',')))
                        if eolInventory[hwid]['hwEolData'][0]['nextHwEolMilestone'] != entry['nextHwEolMilestone']:
                            eolInventory[hwid]['hwEolData'][0]['nextHwEolMilestone'] += ',{}'.format(entry['nextHwEolMilestone'])
                            eolInventory[hwid]['hwEolData'][0]['nextHwEolMilestone'] = ','.join(sorted(eolInventory[hwid]['hwEolData'][0]['nextHwEolMilestone'].split(',')))
                        eolInventory[hwid]['hwEolData'].pop(eolInventory[hwid]['hwEolData'].index(entry))

    # This loop will just delete incorrect entries for 8821, where there an entry for 8821-EX
    for hwid in eolInventory:
        if len(eolInventory[hwid]['hwEolData']) > 1:
            hwProductId = eolInventory[hwid]['hardware']['productId']
            for entry in eolInventory[hwid]['hwEolData'][:]:
                if hwProductId in ['CP-8821-K9','CP-8821-K9=']:
                    if entry['hwEolInstanceId'] != 553341:
                        eolInventory[hwid]['hwEolData'].pop(eolInventory[hwid]['hwEolData'].index(entry))

    # This last loop will look at any other entries with more than one
    for hwid in eolInventory:
        if len(eolInventory[hwid]['hwEolData']) > 1:
            bul0 = eolInventory[hwid]['hwEolData'][0]['hwEolInstanceId']
            for entry in eolInventory[hwid]['hwEolData'][:]:
                if eolInventory[hwid]['hwEolData'].index(entry) == 0:
                    continue
                elif entry['hwEolInstanceId'] == bul0:
                    if eolInventory[hwid]['hwEolData'][0]['currentHwEolMilestone'] != entry['currentHwEolMilestone']:
                        eolInventory[hwid]['hwEolData'][0]['currentHwEolMilestone'] += ',{}'.format(entry['currentHwEolMilestone'])
                        eolInventory[hwid]['hwEolData'][0]['currentHwEolMilestone'] = ','.join(sorted(eolInventory[hwid]['hwEolData'][0]['currentHwEolMilestone'].split(',')))
                    if eolInventory[hwid]['hwEolData'][0]['nextHwEolMilestone'] != entry['nextHwEolMilestone']:
                        eolInventory[hwid]['hwEolData'][0]['nextHwEolMilestone'] += ',{}'.format(entry['nextHwEolMilestone'])
                        eolInventory[hwid]['hwEolData'][0]['nextHwEolMilestone'] = ','.join(sorted(eolInventory[hwid]['hwEolData'][0]['nextHwEolMilestone'].split(',')))
                    eolInventory[hwid]['hwEolData'].pop(eolInventory[hwid]['hwEolData'].index(entry))
                else:
                    continue

            
    return

# Open either finder or explorer and "select" the file to easily open after creation
def pointToFile(filename):
    if platform.system() == 'Darwin':
        subprocess.call(['open', '-R', filename])
    elif platform.system() == 'Windows':
        subprocess.Popen(r'explorer /select,"{}"'.format(filename))
    else:
        pass
    return


# Call to try and find the bulletin ID if it is missing from the original bulletin inventory
def findHwBulletinId(sntcObject,params):
    data = sntcObject.getHwEolBulletins(params)
    return data

def getFilter():
    filter = {
        'snapshot':'LATEST'
    }
    return filter

def createInventory(data,key):
    inventory = {}
    for item in data:
        inventory[item[key]] = item.copy()
    return inventory

# Main method
def createEolInventory():
    # Create the SNTC Object and collect th ecustomer name for later use
    sntcObject = SNTC()
    supportObject = Support()
    global custName
    custName = sntcObject.customerName
    # If there is an issue with returning everything
    # Try limiting the scope by adding "'hwType':'Chassis'" to the filter
    filter = getFilter()

    # Collect the inventory of hardware end of life bulletins and chassis
    print('Gathering EoL Hardware bulletins...')
    eolHwBulletins = sntcObject.getHwEolBulletins()
    print('Done!')

    print('Gathering EoL Hardware...')
    eolHw = sntcObject.getHardwareEol(filter)
    print('Done!')
    print('{} EoL objects found'.format(len(eolHw)))

    # First thing to do is fix the issue of LDoS software not showing Next Milestone/Date
    # Dictionary input, the original dictionary will update because of referencing
    # eolHw consist of only Module, Fan, Power Supply, and Chassis
    # I could potentially remove Fans and Power Supplies later
    # Once I get the actual Hardware, I could also potentially remove Transcievers
    correctAlreadyLdos(eolHw)
    
    # Similarly, fix the bulletins not having End of Vulnerability Support dates
    correctMissingEoVuln(eolHwBulletins)

    # Create an inventory of the hardware EoL bulletins making the hwEolInstanceId the key
    hwEolBulletinInventory = createInventory(eolHwBulletins,'hwEolInstanceId')
    
    print('Creating initial inventory...')
    # Create a "database" using the hwEolInventory dictionary
    # Using the "hwInstanceId" as the key
    hwEolInventory = {}
    
    eolInstanceIdIgnore = []
    # Build the initial Inventory, using the hwInstanceId as the key.
    # Worry about cleaning up later
    for item in eolHw:
        #If the Instance ID is already part of the keys, then we will need to add it to the existing list
        if item['hwInstanceId'] in hwEolInventory.keys():
            hwEolInventory[item['hwInstanceId']]['hwEolData'].append(item.copy())
            
            # We will do the same with bulletin data as we do initially
            bulletinId = item['hwEolInstanceId']
            # If the ID is in the bulletin inventory, simply add it to the latest ([-1]) list entry
            if bulletinId in hwEolBulletinInventory.keys():
                hwEolInventory[item['hwInstanceId']]['hwEolData'][-1]['bulletin'] = hwEolBulletinInventory[bulletinId].copy()
            else:
                # If it's already in our ignore list, ignore it and make the entry "none"
                if bulletinId in eolInstanceIdIgnore:
                    hwEolInventory[item['hwInstanceId']]['hwEolData'][-1]['bulletin'] = None
                # Otherwise perform a lookup
                else:
                    params = {'hwEolInstanceId': bulletinId}
                    response = findHwBulletinId(sntcObject,params)
                    # If we get something back, add it accordingly
                    if response:
                        hwEolInventory[item['hwInstanceId']]['hwEolData'][-1]['bulletin'] = response[0].copy()
                    # If I still can't find it, leave the data blank
                    else:
                        hwEolInventory[item['hwInstanceId']]['hwEolData'][-1]['bulletin'] = None
        
        # The data is simply converted from a dictionary to a list, just in case we have more
        # (which we do) than one set of data for a given hwInstanceId
        else:
            # First we just add the eol Data normally
            hwEolInventory[item['hwInstanceId']] = {'hwEolData': [item.copy()]}

            # Then let's check to see if the eolInstanceId for the hardware is in the hwBulletins data
            bulletinId = item['hwEolInstanceId']
            if bulletinId in hwEolBulletinInventory.keys():
                # If it is, then add this data to the "bulletin" info
                hwEolInventory[item['hwInstanceId']]['hwEolData'][0]['bulletin'] = hwEolBulletinInventory[bulletinId].copy()
            # If not, we will try to find if we maybe just didn't receive the bulletin data
            # If it doesn't exist, we simply leave the bulletin data blank
            else:
                # If it's already in our skip list, don't bother
                if bulletinId in eolInstanceIdIgnore:
                    hwEolInventory[item['hwInstanceId']]['hwEolData'][0]['bulletin'] = None
                # Otherwise, perform a lookup
                else:
                    params = {'hwEolInstanceId': bulletinId}
                    response = findHwBulletinId(sntcObject,params)
                    # If we get something back, add it accordingly
                    if response:
                        hwEolInventory[item['hwInstanceId']]['hwEolData'][0]['bulletin'] = response[0].copy()
                    # If I still can't find it, leave the data blank
                    else:
                        hwEolInventory[item['hwInstanceId']]['hwEolData'][0]['bulletin'] = None

    print('Done!')

    print('Gathering Hardware...')
    hw = sntcObject.getHardware()
    print('Done!')
    print('{} Hardware elements found'.format(len(hw)))
    hwInv = createInventory(hw,'hwInstanceId')
    if len(hwInv) == len(hw):
        print('Number of Hardware Instance IDs match number of Hardware elements.  Data is unique.')
    else:
        print('Object number mismatch.  Hardware Instance ID is not unique')
    
    print('Gathering Network Elements...')
    ne = sntcObject.getElements()
    print('Done!')
    print('{} Network elements found'.format(len(ne)))
    neInv = createInventory(ne,'neInstanceId')
    if len(neInv) == len(ne):
        print('Number of NE Instance IDs match number of Network elements.  Data is unique.')
    else:
        print('Object number mismatch.  Hardware Instance ID is not unique')
    # Create an inventory of parents only, where the neInstanceId matches the managedNeInstanceId
    parentInv = {}
    for e in ne:
        if e['neInstanceId'] == e['managedNeInstanceId']:
            parentInv[e['managedNeInstanceId']] = e.copy()
        else:
            continue

    missingHwIds = {}
    hwPidSet = set()
    # Now we supplement the Inventory with the Hardware Data
    # While we are at it, to save from another loop later, create the hardware PID set for migration details later
    for hwid in hwEolInventory.copy():
        if hwid in hwInv.keys():
            hwEolInventory[hwid]['hardware'] = hwInv[hwid].copy()
            hwPidSet.add(hwInv[hwid]['productId'])
        # If the Hardware ID in the EoL Inventory doesn't exist, pop it out to a "missing hardware IDs" dictionary
        else:
            missingHwIds[hwid] = hwEolInventory.pop(hwid)
    print('{} Hardware IDs not found in the Hardware Inventory'.format(len(missingHwIds)))

    print('Validating NE Instance IDs match for each Hardware ID')
    for hwid in hwEolInventory:
        neInstanceId = hwEolInventory[hwid]['hwEolData'][0]['neInstanceId']
        for i in hwEolInventory[hwid]['hwEolData']:
            if i['neInstanceId'] == neInstanceId:
                continue
            else:
                print('neInstance ID does not match for hardware ID {}'.format(hwid))
    print('Done!')



    # Next we can supplement with the NE Instance ID Data
    for hwid in hwEolInventory:
        neInstanceId = hwEolInventory[hwid]['hwEolData'][0]['neInstanceId']
        if neInstanceId in neInv.keys():
            hwEolInventory[hwid]['networkElement'] = neInv[neInstanceId]
        else:
            print('NE Instance ID not found in Network Element Keys')

    # Then let's add the parent data to the Inventory
    for hwid in hwEolInventory:
        parentId = hwEolInventory[hwid]['hardware']['managedNeInstanceId']
        if parentId in parentInv.keys():
            hwEolInventory[hwid]['parent'] = parentInv[parentId].copy()
        else:
            continue
    
    # Before adding anything else, fix the hwEolData to remove any potential duplicates
    fixHwEolData(hwEolInventory)

    # And finally, let's add the migration information
    print('Gathering Hardware Migration Details...')
    eoxData = supportObject.getEoxData(hwPidSet)
    fixEoxData(eoxData)
    #migData = getProductMigrationDetails(eoxData)
    print('Done!')
    print('Adding EOX details to inventory...')
    for hwid in hwEolInventory:
        if hwEolInventory[hwid]['hardware']['productId'] in eoxData.keys():
            hwEolInventory[hwid]['EOXRecord'] = eoxData[hwEolInventory[hwid]['hardware']['productId']].copy()
        else:
            hwEolInventory[hwid]['EOXRecord'] = None
    print('Done!')
    for hwid in hwEolInventory:
        if len(hwEolInventory[hwid]['hwEolData']) == 0:
            print(hwid,hwEolInventory[hwid]['hardware']['productId'])

    return hwEolInventory

    # TESTING SECTION TO SPOT CHECK SOME DATA
    #for hwid in hwEolInventory:
    #    if len(hwEolInventory[hwid]['hwEolData']) > 1:
    #        print(len(hwEolInventory[hwid]['hwEolData']), hwEolInventory[hwid]['hardware']['productId'])
    #        for eol in hwEolInventory[hwid]['hwEolData']:
    #            if eol['bulletin']:
    #                print('bulletin exists')
    #            print(json.dumps(eol,indent =2))
    #print(hwEolInventory.keys())
    #print(json.dumps(hwEolInventory[2050399920],indent=2))
    #print(json.dumps(hwEolInventory[2050360408],indent=2))
    #print(json.dumps(hwEolInventory[2050401880],indent=2))
    #print(json.dumps(hwEolInventory[2050406254],indent=2))
    #print(json.dumps(hwEolInventory[2103787877],indent=2))
    
def createOutput(inv):
    # Create the output file
    print('Creating CSV file...')
    # Check for Output directory
    if not os.path.exists('Output'):
        os.mkdir('Output')
    else: pass

    # Create the initial file with the timestamp for uniqueness
    filename = 'Output/{}-Hardware-EoL-{}.csv'.format(custName,datetime.now().strftime('%Y%m%d%H%M%S'))
    file = open(filename,'w')
    file.write('Parent Name,'+
               'Hostname,'+
               'IP Address,'+
               'Hardware PID,'+
               'Product Type,'+
               'Product Family,'+
               'Serial Number,'+
               'Software Type,'+
               'Software Version,'+
               'Current Hardware EoL Milestone,'+
               'Current Hardware EoL Milestone Date,'+
               'Next Hardware EoL Milestone,'+
               'Next Hardware EoL Milestone Date,'+
               'Hardware EoVulnerability Date,'+
               'Hardware LDoS Date,'+
               'Hardware Replacement PID,'+
               'Hardware EoL Link,'+
               'Reachability,'+
               'Notes'+
               '\n'
    )
    # Loop through the inventory to get the data that we need
    for hwid in inv:
        # Start with the easy ones first
        parentName = inv[hwid]['parent']['hostname']
        if inv[hwid]['hardware']['productId'] == inv[hwid]['networkElement']['productId']:
            hostname = inv[hwid]['networkElement']['hostname']
        else:
            hostname = 'N/A'
        ipAddress = inv[hwid]['networkElement']['ipAddress']
        hardwarePid = inv[hwid]['hardware']['productId']
        productType = inv[hwid]['hardware']['productType']
        productFamily = inv[hwid]['hardware']['productFamily']
        serialNumber = inv[hwid]['hardware']['serialNumber']
        softwareType = inv[hwid]['networkElement']['swType']
        softwareVersion = inv[hwid]['networkElement']['swVersion']
        reachability = inv[hwid]['networkElement']['reachabilityStatus']
        replacementPid = ''
        hwEolLink = ''
        currentHwEolMilestone = ''
        currentHwEolMilestoneDate = ''
        nextHwEolMilestone = ''
        nextHwEolMilestoneDate = ''
        hwEndOfVulnerabilityDate = ''
        hwLdosDate = ''

        # There may be some entries that have more than one in the 'hwEolData' array
        # For simplicity, I am only using the first entry, it's not the best solution, but it makes
        # generating the output pretty easy
        notes = ''
        if len(inv[hwid]['hwEolData']) > 1:
            notes = 'More than one EoL Entry'
        currentHwEolMilestone = inv[hwid]['hwEolData'][0]['currentHwEolMilestone']
        currentHwEolMilestoneDate = inv[hwid]['hwEolData'][0]['currentHwEolMilestoneDate']
        nextHwEolMilestone = inv[hwid]['hwEolData'][0]['nextHwEolMilestone']
        nextHwEolMilestoneDate = inv[hwid]['hwEolData'][0]['nextHwEolMilestoneDate']
        if 'bulletin' in inv[hwid]['hwEolData'][0].keys():
            if inv[hwid]['hwEolData'][0]['bulletin']:
                #print(json.dumps(inv[hwid]['hwEolData'][0],indent=2))
                hwEolLink = inv[hwid]['hwEolData'][0]['bulletin']['url']
                hwEndOfVulnerabilityDate = inv[hwid]['hwEolData'][0]['bulletin']['eoVulnerabilitySecuritySupport']
                hwLdosDate = inv[hwid]['hwEolData'][0]['bulletin']['lastDateOfSupport']
        elif 'EOXRecord' in inv[hwid].keys():
            hwEolLink = inv[hwid]['EOXRecord'][0]['LinkToProductBulletinURL']
            hwEndOfVulnerabilityDate = inv[hwid]['EOXRecord'][0]['EndOfSecurityVulSupportDate']['value']
            hwLdosDate = inv[hwid]['EOXRecord'][0]['LastDateOfSupport']['value']
        else:
            hwEolLink = None
            hwEndOfVulnerabilityDate = None
            hwLdosDate = None
       
        if inv[hwid]['EOXRecord']:
            #print(json.dumps(inv[hwid]['EOXRecord'][0],indent=2))
            if inv[hwid]['EOXRecord'][0]['EOXMigrationDetails']['MigrationProductId']:
                replacementPid = inv[hwid]['EOXRecord'][0]['EOXMigrationDetails']['MigrationProductId']
            elif inv[hwid]['EOXRecord'][0]['EOXMigrationDetails']['MigrationInformation']:
                replacementPid = inv[hwid]['EOXRecord'][0]['EOXMigrationDetails']['MigrationInformation']
            elif inv[hwid]['EOXRecord'][0]['EOXMigrationDetails']['MigrationProductName']:
                replacementPid = inv[hwid]['EOXRecord'][0]['EOXMigrationDetails']['MigrationProductName']
            else:
                replacementPid = 'None'
        else:
            replacementPid = 'None'

        file.write('{},{},{},{},{},{},{},{},"{}","{}",{},"{}",{},{},{},{},{},{},{}\n'.format(
            parentName,
            hostname,
            ipAddress,
            hardwarePid,
            productType,
            productFamily,
            serialNumber,
            softwareType,
            softwareVersion,
            currentHwEolMilestone,
            currentHwEolMilestoneDate,
            nextHwEolMilestone,
            nextHwEolMilestoneDate,
            hwEndOfVulnerabilityDate,
            hwLdosDate,
            replacementPid,
            hwEolLink,
            reachability,
            notes
        ))

                    
    file.close()

    print('Done!')

    # Finally open explorer or finder to easily find and open the new file quickly
    filePath = os.path.abspath(filename)
    pointToFile(filePath)


if __name__ == '__main__':
    inventory = createEolInventory()
    createOutput(inventory)