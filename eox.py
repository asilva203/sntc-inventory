import requests
import creds
import json
import sys

class EOX:

    def __init__(self):
        self.token = self.getAccessToken()
        self.headers = {
            'Accept': 'application/json',
            'Authorization': 'Bearer {}'.format(self.token)
        }
    
    def getAccessToken(self):
        clientId, clientSecret = creds.getEoxCreds()
        url = 'https://cloudsso.cisco.com/as/token.oauth2'
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        body = 'grant_type=client_credentials&client_id={}&client_secret={}'.format(clientId, clientSecret)
        r = requests.post(url, headers=headers, data=body)
        r.close()
        token = r.json()['access_token']
        return token


    def getEoxData(self,pidSet):
        pidData = {}
        print('got to eoxData call')
        for productId in pidSet:
            uri = 'https://api.cisco.com/supporttools/eox/rest/5/EOXByProductID/1/{}'.format(productId)
            print('Getting EOX for PID {}'.format(productId))
            r = requests.get(uri,headers=self.headers)
            r.close()
            if r.ok:
                if len(r.json()['EOXRecord']) > 1:
                    pidData[productId] = r.json()['EOXRecord'][0]
                    print('More than 1 EoX record for PID {}'.format(productId))
                    for entry in r.json()['EOXRecord'][1:]:
                        pidData[productId]['EOXMigrationDetails']['MigrationProductId'] += ' or {}'.format(entry['EOXMigrationDetails']['MigrationProductId'])
                        pidData[productId]['EOXMigrationDetails']['MigrationProductName'] += ' or {}'.format(entry['EOXMigrationDetails']['MigrationProductName'])
                        if pidData[productId]['EOXMigrationDetails']['MigrationProductId'] == ' or ':
                            pidData[productId]['EOXMigrationDetails']['MigrationProductId'] = ''
                        else: pass
                        if pidData[productId]['EOXMigrationDetails']['MigrationProductName'] == ' or ':
                            pidData[productId]['EOXMigrationDetails']['MigrationProductName'] = ''
                        else: pass
                        
                elif len(r.json()['EOXRecord']) == 0:
                    print('No EoX data for PID {}'.format(productId))
                elif 'EOXError' in r.json()['EOXRecord'][0].keys():
                    print('EOX Error for PID {},{}'.format(productId,r.json()['EOXRecord'][0]['EOXError']['ErrorDescription']))
                else:
                    pidData[productId] = r.json()['EOXRecord'][0]
            else:
                print('Error collecting EOX data for PID {}'.format(productId))
                print(r)
                sys.exit(0)
        
        # Double check PID data to make sure the replacements are not also end of life
        for product in pidData:
            migProductId = pidData[product]['EOXMigrationDetails']['MigrationProductId']
            if migProductId in pidData.keys():
                pidData[product]['EOXMigrationDetails'] = pidData[migProductId]['EOXMigrationDetails']
            else:
                continue
        
        return pidData
        

