# EOX Class
# This class interacts with the EOX API to pull down end of life information
# Given a product ID
# Credentials are retrieved from the creds.py file

import requests
import creds
import json
import sys
import urllib.parse

class Support:
    # Initialize the Support class and retrieve an access token for the API
    # using the getAccessToken method
    def __init__(self):
        self.token = self.getAccessToken()
        self.headers = {
            'Accept': 'application/json',
            'Authorization': 'Bearer {}'.format(self.token)
        }
    
    # Retreive an access token from the Cisco URL
    # Documentation for Authentication can be found at:
    # https://developer.cisco.com/docs/support-apis/#!authentication
    def getAccessToken(self):
        # Retrieve the client ID and secret from the creds.py file
        print('Retrieving Support API credentials...')
        clientId, clientSecret = creds.getSupportCreds()
        print('Done!')
        # Set URL for authentication along with the headers and body 
        # then send a POST, per the API documentation
        url = 'https://id.cisco.com/oauth2/default/v1/token'
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        body = 'grant_type=client_credentials&client_id={}&client_secret={}'.format(clientId, clientSecret)
        print('Retrieving access token...')
        r = requests.post(url, headers=headers, data=body)
        r.close()
        # Check to see if the status code is OK
        if r.ok:
            # If the status code is fine, get the token from the response and return it
            token = r.json()['access_token']
            print('Done!')
            return token
        # If not, print an error along with some data from the API response
        else:
            print('Error obtaining the access token')
            resp = r.json()
            for key in resp:
                print('{}: {}'.format(key,resp[key]))
            sys.exit(0)
        

    # Method to retrieve EOX data for a given PID from the API
    # We leverage a "set" type as input to avoid duplicates
    # API documentation is found at:
    # https://developer.cisco.com/docs/support-apis/#!eox/get-eox-by-product-ids
    def getEoxData(self,pidSet):
        # Create a dictionary to populate with all returned data from the API
        pidData = {}
        # Loop through all the product ID's in the PID set
        for productId in pidSet:
            uri = 'https://apix.cisco.com/supporttools/eox/rest/5/EOXByProductID/1/{}'.format(productId)
            print('Getting EOX for PID {}'.format(productId))
            r = requests.get(uri,headers=self.headers)
            r.close()
            # Check to make sure the return status is good
            if r.ok:
                # If the response length is 0, there is no EOX data for that particular PID
                if len(r.json()['EOXRecord']) == 0:
                    print('No EoX data for PID {}'.format(productId))
                # Otherwise, just add the data and send it back.  There could be more than one record in the data
                else:
                    pidData[productId] = r.json()['EOXRecord']
            else:
                print('Error collecting EOX data for PID {}'.format(productId))
                print(r)
                sys.exit(0)
        #FIND A BETTER PLACE TO DO THIS
        ## There is a potential that the replacement product ID given is also end of life
        ## Double check PID data to make sure the replacements are not also end of life
        ## within the data set that was fed into this class
        ## This may require some manual spot checking in the output file as well
        #for product in pidData:
        #    migProductId = pidData[product]['EOXMigrationDetails']['MigrationProductId']
        #    if migProductId in pidData.keys():
        #        pidData[product]['EOXMigrationDetails'] = pidData[migProductId]['EOXMigrationDetails']
        #    else:
        #        continue
        
        # Finally return the dictionary with the EOX data
        return pidData
    
    def getProductMigrationDetails(self,pidSet):
        data = self.getEoxData(pidSet)
        migInventory = {}
        for pid in data:
            migInventory[pid] = {'EOXMigrationDetails': {'MigrationInformation':'','MigrationProductId':''}}
            for entry in data[pid]:
                migInventory[pid]['EOXMigrationDetails']['MigrationInformation'] += '{} or '.format(entry['EOXMigrationDetails']['MigrationInformation'])
                migInventory[pid]['EOXMigrationDetails']['MigrationProductId'] += '{} or '.format(entry['EOXMigrationDetails']['MigrationProductId'])
            migInventory[pid]['EOXMigrationDetails']['MigrationInformation'] = migInventory[pid]['EOXMigrationDetails']['MigrationInformation'][:-4]
            migInventory[pid]['EOXMigrationDetails']['MigrationProductId'] = migInventory[pid]['EOXMigrationDetails']['MigrationProductId'][:-4]
        return migInventory



    # Method to retrieve EOX data for a given Serial from the API
    # We leverage a "set" type as input to avoid duplicates but convert to list for API call
    # API documentation is found at:
    # https://developer.cisco.com/docs/support-apis/#!eox/get-eox-by-serial-numbers
    # Work in progress
    def getEoxBySerial(self,serials):
        # Create a dictionary to populate with all returned data from the API and convert the serials set to a list
        serialData = {}
        serialList = list(serials)
        # Make the call more efficient by sending 20 serial numbers at a time (maximum per the documentation)
        bulkSerialList = []
        # Create the Bulk Serial List to send batches of 20 serial numbers at a time
        while serialList:
            if len(serialList) > 20:
                temp = ','.join(str(s) for s in serialList[:20])
                bulkSerialList.append(temp)
                serialList = serialList[20:]
            else:
                temp = ','.join(str(s) for s in serialList)
                bulkSerialList.append(temp)
                serialList = []
        # Loop through the list of serials to pull data from the API
        for serial in bulkSerialList:
            uri = 'https://apix.cisco.com/supporttools/eox/rest/5/EOXBySerialNumber/1/{}'.format(serial)
            print('Getting EOX for Serial {}'.format(serial))
            r = requests.get(uri,headers=self.headers)
            r.close()
            if r.ok:
                for record in r.json()['EOXRecord']:
                    for s in record['EOXInputValue'].split(','):
                        serialData[s] = record

            else:
                print('Error collecting EOX data for Serial {}'.format(serial))
                print(r)
                serialData[serial] = 'None'
                #sys.exit(0)
        
        return serialData
    
    # Method to retrieve Coverage data for a given Serial from the API
    # We leverage a "set" type as input to avoid duplicates
    # API documentation is found at:
    # https://developer.cisco.com/docs/support-apis/#!serial-number-to-information/get-coverage-status-by-serial-numbers
    def getCoverageSummaryBySerial(self,serials):
        # Create a dictionary to populate with all returned data from the API
        coverageData = {}
        # Make the call more efficient by sending 50 serials at a time (max for a single page return)
        bulkSerialList = []
        while serials:
            if len(serials) > 50:
                temp = ','.join(str(s) for s in serials[:50])
                bulkSerialList.append(temp)
                serials = serials[50:]
            else:
                temp = ','.join(str(s) for s in serials)
                bulkSerialList.append(temp)
                serials = []
        # Loop through the list of serials to pull data from the API
        for serials in bulkSerialList:
            uri = 'https://apix.cisco.com/sn2info/v2/coverage/summary/serial_numbers/{}'.format(serials)
            print('Getting Coverage for Serial {}'.format(serials))
            r = requests.get(uri,headers=self.headers)
            r.close()
            if r.ok:
                    print(json.dumps(r.json()['pagination_response_record'],indent=2))
                    data = r.json()['serial_numbers']
                    for item in data:
                        coverageData[item['sr_no']] = item

            else:
                print('Error collecting coverage data for Serials {}'.format(serials))
                print(r)
                
        
        return coverageData
    
    # Work in Progress
    def getSwEox(self,swSet):
        swData = {}
        for sw in swSet:
            swType = urllib.parse.quote(sw.split(',')[0])
            #swVer = urllib.parse.quote(sw.split(',')[1])
            swVer = sw.split(',')[1]
            uri = 'https://apix.cisco.com/supporttools/eox/rest/5/EOXBySWReleaseString/1?input1={},{}'.format(swVer,swType)
            r = requests.get(uri,headers=self.headers)
            r.close()
            if r.ok:
                #print(json.dumps(r.json()['EOXRecord'][0],indent=2))
                if 'EOXError' in r.json()['EOXRecord'][0]:
                    print(uri)
                    print(r.json().keys())
                    print(json.dumps(r.json(),indent=2))
                    print('Error with EOX Data')
                else:
                    swData[sw] = r.json()['EOXRecord']
        return swData

    def getSuggestedReleaseByPid(self,pidSet):
        suggestData = {}
        for pid in pidSet:
            uri = 'https://apix.cisco.com/software/suggestion/v2/suggestions/releases/productIds/{}'.format(pid)
            print('Getting software suggestion for pid {}...'.format(pid))
            r = requests.get(uri,headers=self.headers)
            r.close()
            if r.ok:
                suggestData[pid] = r.json()['productList']
            else:
                print('Error getting suggest for pid {}'.format(pid))
                print(r)
                sys.exit(0)
        return suggestData
    
    def getMdfInfoByPid(self,pidSet):
        mdfData = {}
        for pid in pidSet:
            uri = 'https://apix.cisco.com/product/v1/information/product_ids_mdf/{}'.format(pid)
            print('Getting MDF info for pid {}...'.format(pid))
            r = requests.get(uri,headers=self.headers)
            r.close()
            if r.ok:
                mdfData[pid] = r.json()['productList']
            else:
                print('Error getting suggest for pid {}'.format(pid))
                print(r)
                sys.exit(0)
        return mdfData