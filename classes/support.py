# EOX Class
# This class interacts with the EOX API to pull down end of life information
# Given a product ID
# Credentials are retrieved from the creds.py file

import requests
import creds
import json
import sys

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
                # If return status is good, check to see if we have more than one record in the response
                if len(r.json()['EOXRecord']) > 1:
                    # Populate the data dictionary with the first entry
                    pidData[productId] = r.json()['EOXRecord'][0]
                    print('More than 1 EoX record for PID {}'.format(productId))
                    # Check the remaining entries in order to add any additonal details around
                    # potential migration product ID's or names
                    for entry in r.json()['EOXRecord'][1:]:
                        pidData[productId]['EOXMigrationDetails']['MigrationProductId'] += ' or {}'.format(entry['EOXMigrationDetails']['MigrationProductId'])
                        pidData[productId]['EOXMigrationDetails']['MigrationProductName'] += ' or {}'.format(entry['EOXMigrationDetails']['MigrationProductName'])
                        # If there is nothing the Migration Product ID details, simply erase it
                        if pidData[productId]['EOXMigrationDetails']['MigrationProductId'] == ' or ':
                            pidData[productId]['EOXMigrationDetails']['MigrationProductId'] = ''
                        else: pass
                        # If there is nothing in the Migration Product Name details, simply erase it
                        if pidData[productId]['EOXMigrationDetails']['MigrationProductName'] == ' or ':
                            pidData[productId]['EOXMigrationDetails']['MigrationProductName'] = ''
                        else: pass
                # If the response length is 0, there is no EOX data for that particular PID
                elif len(r.json()['EOXRecord']) == 0:
                    print('No EoX data for PID {}'.format(productId))
                # If there is an Error record within the response, print it out
                # There's probably a better place to check for this
                elif 'EOXError' in r.json()['EOXRecord'][0].keys():
                    print('EOX Error for PID {},{}'.format(productId,r.json()['EOXRecord'][0]['EOXError']['ErrorDescription']))
                # If there is only one record and there are no errors, populate the
                # data dictionary that will be returned
                else:
                    pidData[productId] = r.json()['EOXRecord'][0]
            # If there is an issue with the reponse data, print an error, along with the PID
            # and response details, and exit the program
            else:
                print('Error collecting EOX data for PID {}'.format(productId))
                print(r)
                sys.exit(0)
        
        # There is a potential that the replacement product ID given is also end of life
        # Double check PID data to make sure the replacements are not also end of life
        # within the data set that was fed into this class
        # This may require some manual spot checking in the output file as well
        for product in pidData:
            migProductId = pidData[product]['EOXMigrationDetails']['MigrationProductId']
            if migProductId in pidData.keys():
                pidData[product]['EOXMigrationDetails'] = pidData[migProductId]['EOXMigrationDetails']
            else:
                continue
        
        # Finally return the dictionary with the EOX data
        return pidData
    
    # Method to retrieve EOX data for a given Serial from the API
    # We leverage a "set" type as input to avoid duplicates
    # API documentation is found at:
    # https://developer.cisco.com/docs/support-apis/#!eox/get-eox-by-serial-numbers
    def getEoxBySerial(self,serials):
        # Create a dictionary to populate with all returned data from the API
        serialData = {}
        # Loop through the list of serials to pull data from the API
        for serial in serials:
            uri = 'https://apix.cisco.com/supporttools/eox/rest/5/EOXBySerialNumber/1/{}'.format(serial)
            print('Getting EOX for Serial {}'.format(serial))
            r = requests.get(uri,headers=self.headers)
            r.close()
            if r.ok:
                if len(r.json()['EOXRecord']) > 1:
                    print('Serial {} has more than one EOX record')
                else:
                    serialData[serial] = r.json()['EOXRecord'][0]

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
        # Loop through the list of serials to pull data from the API
        for serial in serials:
            uri = 'https://apix.cisco.com/sn2info/v2/coverage/summary/serial_numbers/{}'.format(serial)
            print('Getting Coverage for Serial {}'.format(serial))
            r = requests.get(uri,headers=self.headers)
            r.close()
            if r.ok:
                    coverageData[serial] = r.json()['serial_numbers'][0]

            else:
                print('Error collecting coverage data for Serial {}'.format(serial))
                print(r)
                coverageData[serial] = 'None'
        
        return coverageData