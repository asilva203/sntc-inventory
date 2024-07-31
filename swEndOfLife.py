from datetime import datetime
from classes.sntc import SNTC
from classes.support import Support
import json
import os
import platform
import subprocess

# Fix data for things already LDoS so that we have dates for everything
def correctAlreadyLdos(eolData):
    for item in eolData:
        # First we search for anything that is already LDoS
        if item['currentSwEolMilestone'] == 'LDoS':
            # If the Software is LDoS, we simply need to update the next milestone and milestone date
            item['nextSwEolMilestone'] = 'Already LDoS'
            item['nextSwEolMilestoneDate'] = item['currentSwEolMilestoneDate']
        else: pass
        # Fix a second issue where I have at least one instance where there is a comma at the end of the software version
        if item['swVersion'].endswith(','):
            item['swVersion'] = item['swVersion'].rstrip(',')
        else: pass

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

# Find the EoL Instance ID bullet for a version/software type
def findSwBulletin(swType,swVersion):
    pass

# Open either finder or explorer and "select" the file to easily open after creation
def pointToFile(filename):
    if platform.system() == 'Darwin':
        subprocess.call(['open', '-R', filename])
    elif platform.system() == 'Windows':
        subprocess.Popen(r'explorer /select,"{}"'.format(filename))
    else:
        pass
    return

# Grab the filter.  In general, I should almost always use LATEST
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

# Main function
def createSwEolInventory():
    sntcObject = SNTC()
    global custName
    custName = sntcObject.customerName
    # If there is an issue with returning everything
    # Try limiting the scope by adding "'hwType':'Chassis'" to the filter
    filter = getFilter()
    print('Gathering EoL Software Bulletins...')
    eolSwBulletins = sntcObject.getSwEolBulletins()
    print('Done!')
    print('Gathering EoL Software...')
    eolSoftware = sntcObject.getSwEol(filter)
    print('Done!')
    print('{} objects found'.format(len(eolSoftware)))
    
    # First thing to do is fix the issue of LDoS software not showing Next Milestone/Date
    # Dictionary input, the original dictionary will update because of referencing
    correctAlreadyLdos(eolSoftware)

    # Similarly, fix the bulletins not having End of Vulnerability Support dates
    correctMissingEoVuln(eolSwBulletins)
    
    # Create an inventory of the bulletin using the swEolInstanceId as the key
    swEolBulletinInventory = createInventory(eolSwBulletins,'swEolInstanceId')
    
    swEolInventory = {}
    # Create a "database" using the swEolInventory dictionary
    # Using the "neInstanceId" as the key
    for item in eolSoftware:
        # First we need to see if the "neInstanceId" is already a key in the inventory
        if item['neInstanceId'] in swEolInventory.keys():
            # If it exists, there is apparently more than one EoL item for that Instance ID.
            # Not really sure why this is the case because the Instance ID should be unique and only have one
            # entitry associated with it.
            # Before we add it, let's make sure it is not exactly the same as the other elements in the swEolInventory for that key
            # Also iterate over a copy (using [:]) so that it doesn't iterate through the recently added item
            for swEol in swEolInventory[item['neInstanceId']]['eolSwData'][:]:
                if item == swEol:
                    # Print a statment in case I need to troubleshoot this later
                    print('Duplicate software EoL data found for instance {}'.format(item['neInstanceId']))
                else:
                    # If not, we will then need to add this second (or more) set of data to the list
                    copy = item.copy()
                    bulletinId = copy['swEolInstanceId']
                    copy['bulletin'] = swEolBulletinInventory[bulletinId].copy()
                    swEolInventory[item['neInstanceId']]['eolSwData'].append(copy.copy())
        
        # The data is simply converted from a dictionary to a list, just in case we have more
        # (which we do) than one set of data for a given neInstanceId
        else:
            # We also need to ensure that we copy in order to avoid reference issues here
            swEolInventory[item['neInstanceId']] = {'eolSwData': [item.copy()]}
            bulletinId = swEolInventory[item['neInstanceId']]['eolSwData'][0]['swEolInstanceId']
            swEolInventory[item['neInstanceId']]['eolSwData'][0]['bulletin'] = swEolBulletinInventory[bulletinId].copy()

    # Next we need to collect all of the Network Elements (these have the software/hostname/IP/etc., but not the Serial numbers)
    print('Gathering Network Elements...')
    ne = sntcObject.getElements()
    print('Done!')
    print('{} Network Element objects found'.format(len(ne)))

    # Then we perform a similar conversion to use the neInstanceID as the key
    neInv = createInventory(ne,'neInstanceId')
   
    # Print the number of items for comparison with the total number of network elements
    # If it doesn't match, I need to troubleshoot later
    print('{} objects in the converted inventory'.format(len(neInv)))
    if len(neInv) == len(ne):
        print('Number of objects match.  Everything is unique.')
    else:
        print('Object number mismatch.  NE Instance IDs are not unique.')

    # Now we can go through the Software EoL inventory to add more data to it
    print('Adding Network Element data to EoL Inventory...')
    for neid in swEolInventory.copy():
        # If the neInstance ID in the EoL inventory is also found in the Network Element inventory
        if neid in neInv.keys():
            # Update the software inventory with the data from the Network Element inventory
            swEolInventory[neid].update(neInv[neid].copy())
        # Otherwise print an error message to troubleshoot later
        else:
            print('ID {} not found in the Network Element Inventory.  Removing from inventory'.format(neid))
            swEolInventory.pop(neid)
    print('Done!')

    # Clean up the extra entries in the software EoL data
    for neid in swEolInventory:
        # Check to see if there is more than one entry in the data
        if len(swEolInventory[neid]['eolSwData']) > 1:
            # I will be popping unneeded data, so I need to use the [:] notation
            for e in swEolInventory[neid]['eolSwData'][:]:
                # Check if the software type and version are the same between the instance ID and the EoL Data
                if (swEolInventory[neid]['swType'] == e['swType']) and (swEolInventory[neid]['swVersion'] == e['swVersion']):
                    # If they are the same, I don't need to do anything
                    continue
                else:
                    # If they are different, pop out the bad data
                    swEolInventory[neid]['eolSwData'].pop(swEolInventory[neid]['eolSwData'].index(e))
            # Ensure I actually have something left over in the list
            if swEolInventory[neid]['eolSwData']:
                continue
            else:
                # If I end up seeing this, I will need to troubleshoot my code and find a proper piece of EoL Data
                print('No matching data left for Instance ID {}'.format(neid))

        # Just make sure I am good with all the rest
        # I need to figure out how to handle version mismatches in the final data
        #else:
        #    if (swEolInventory[neid]['swType'] == swEolInventory[neid]['eolSwData'][0]['swType']) and (swEolInventory[neid]['swVersion'] == swEolInventory[neid]['eolSwData'][0]['swVersion']):
        #        continue
        #    else:
        #        swType = swEolInventory[neid]['swType']
        #        swVersion = swEolInventory[neid]['swVersion']
        #        bulletinId = findSwBulletin(swType,swVersion)
        #        print(neid,swEolInventory[neid]['swType'],swEolInventory[neid]['eolSwData'][0]['swType'],swEolInventory[neid]['swVersion'],swEolInventory[neid]['eolSwData'][0]['swVersion'])
        else: continue
    
    #============================
    # Data set is built at this point.  Can print out one item to find the keys
    # needed to extract the data if needed
    #print(json.dumps(swEolInventory[<neInstanceID>],indent=2))
    #print(json.dumps(swEolInventory[2331303285],indent=2))
    return swEolInventory

def createOutput(swEolInventory):
    print('Creating CSV file...')
    # Check for Output directory
    if not os.path.exists('Output'):
        os.mkdir('Output')
    else: pass

    # Create the initial file with the timestamp for uniqueness
    filename = 'Output/{}-Software-EoL-{}.csv'.format(custName,datetime.now().strftime('%Y%m%d%H%M%S'))
    file = open(filename,'w')
    # Write the initial header for the CSV file
    file.write('Parent,'+
               'IP Address,'+
               'Product ID,'+
               'Product Type,'+
               'Product Family,'+
               'Software Type,'+
               'Software Version,'+
               'EoL Software Type,'+
               'EoL Software Version,'+
               'Current Software EoL Milestone,'+
               'Current Software EoL Milestone Date,'+
               'Next Software EoL Milestone,'+
               'Next Software EoL Milestone Date,'+
               'Software End of Vulnerability Date,'+
               'Software Last Day of Support Date,'+
               'Sofware EoL Bulletin Link'+
               '\n')
    
    # Run through the inventory and fill out all the fields
    for neid in swEolInventory:
        #print('New')
        #print(json.dumps(swEolInventory[neid],indent=2))
        file.write('{},{},{},{},{},{},"{}",{},{},{},{},{},{},{},{},{}\n'.format(
            swEolInventory[neid]['hostname'],
            swEolInventory[neid]['ipAddress'],
            swEolInventory[neid]['productId'],
            swEolInventory[neid]['productType'],
            swEolInventory[neid]['productFamily'],
            swEolInventory[neid]['swType'],
            swEolInventory[neid]['swVersion'],
            swEolInventory[neid]['eolSwData'][0]['swType'],
            swEolInventory[neid]['eolSwData'][0]['swVersion'],
            swEolInventory[neid]['eolSwData'][0]['currentSwEolMilestone'],
            swEolInventory[neid]['eolSwData'][0]['currentSwEolMilestoneDate'],
            swEolInventory[neid]['eolSwData'][0]['nextSwEolMilestone'],
            swEolInventory[neid]['eolSwData'][0]['nextSwEolMilestoneDate'],
            swEolInventory[neid]['eolSwData'][0]['bulletin']['eoVulnerabilitySecuritySupport'],
            swEolInventory[neid]['eolSwData'][0]['bulletin']['lastDateOfSupport'],
            swEolInventory[neid]['eolSwData'][0]['bulletin']['url']
        ))
    file.close()

    print('Done!')

    # Finally open explorer or finder to easily find and open the new file quickly
    filePath = os.path.abspath(filename)
    pointToFile(filePath)

if __name__ == '__main__':
    inventory = createSwEolInventory()
    createOutput(inventory)