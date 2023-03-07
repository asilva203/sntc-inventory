# script to make calls to the SNTC API and get stuff back
import creds
import requests
import json
import sys

class SNTC:
    # SNTC Class to perform basic functions from the SNTC API and to do various things
    
    # Initial constructor
    # I want the SNTC object to contain the access token, headers, and select the
    # customer and inventory name right off the bat
    def __init__(self):
        self.token = self.getAccessToken()
        self.headers = {
        'Accept': 'application/json',
        'Authorization': 'Bearer {}'.format(self.token)
        }
        self.customerId,self.customerName = self.setCustomer()
        self.inventory = self.setInventory()
        
    # Function for getting the access token from the OAUTH URL
    def getAccessToken(self):
        print('Retrieving SNTC credentials...')
        clientId, clientSecret = creds.getSntcCreds()
        print('Done!')
        url = 'https://cloudsso.cisco.com/as/token.oauth2'
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        body = 'grant_type=client_credentials&client_id={}&client_secret={}'.format(clientId, clientSecret)
        print('Retreiving access token...')
        r = requests.post(url, headers=headers, data=body)
        r.close()
        if r.ok:
            token = r.json()['access_token']
            print('Done!')
            return token
        else:
            print('Error obtaining the access token')
            resp = r.json()
            for key in resp:
                print('{}: {}'.format(key,resp[key]))
            sys.exit(0)

    # List my SNTC customers in a list
    def listCustomers(self,customers):
        i = 1
        for customer in customers:
            if customer['selection'] == i:
                # Testing a few outputs
                #print('{}: {} - {}'.format(i, customer['customerId'], customer['customerName']))
                print('{}: {}'.format(i, customer['customerName']))
                i+=1
        return

    # Call to get customer information back
    def getCustomers(self):
        url = 'https://apx.cisco.com/cs/api/v1/customer-info/customer-details'
        r = requests.get(url, headers=self.headers)
        r.close()
        if r.ok:
            customers = r.json()['data']
            i = 1
            for customer in customers:
                customer['selection'] = i
                i+=1
            self.listCustomers(customers)
            return customers
        else:
            print('Error getting customers')
            print('HTTP Response:')
            print(r.text)
            sys.exit(0)

    # Call to select a specific customer
    def setCustomer(self):
        custId = ''
        custName = ''
        customers = self.getCustomers()
        custSelection = input('Customer to use: ')
        try:
            int(custSelection)
        except:
            print('Invalid Entry\n')
            return self.setCustomer()
        
        for cust in customers:
            if cust['selection'] == int(custSelection):
                custId = cust['customerId']
                custName = cust['customerName']
            else: continue
        if custId and custName:
            return custId, custName
        else:
            print('Invalid Customer Selection\n')
            return self.setCustomer()

    # List customer inventories in a list
    def listInventories(self,inventories):
        i = 1
        for inv in inventories:
            if inv['selection'] == i:
                print('{}: {}'.format(i, inv['inventoryName']))
                i+=1
        return

    # Call to get customer inventories
    def getInventories(self):
        url = 'https://apx.cisco.com/cs/api/v1/customer-info/inventory-groups?customerId={}'.format(self.customerId)
        r = requests.get(url, headers=self.headers)
        r.close()
        if r.ok:
            inventories = r.json()['data']
            i = 1
            for inv in inventories:
                inv['selection'] = i
                i+=1
            self.listInventories(inventories)
            return inventories
        else:
            print('Error getting inventories')
            print('HTTP Response:')
            print(r.text)
            sys.exit(0)

    # Call to select a specific inventory
    def setInventory(self):
        invName = ''
        inventories = self.getInventories()
        if len(inventories) == 1:
            invName = inventories[0]['inventoryName']
            print('Only one inventory, selecting the default')
            return invName
        
        invSelection = input('Inventory to use: ')
        try:
            int(invSelection)
        except:
            print('Invalid Entry\n')
            return self.setInventory()
        
        for inv in inventories:
            if inv['selection'] == int(invSelection):
                invName = inv['inventoryName']
            else: continue
        if invName:
            return invName
        else:
            print('Invalid Inventory Selection\n')
            return self.setInventory()

    # Call to get hardware inventory
    def getHardware(self, params=None):
        url = 'https://apx.cisco.com/cs/api/v1/inventory/hardware'
        queryString = '?customerId={}&inventoryName={}'.format(self.customerId,self.inventory)
        url += queryString
        if params:
            for param in params:
                url += '&{}={}'.format(param, params[param])
        r = requests.get(url, headers=self.headers)
        r.close()
        if r.ok:
            hardware = r.json()['data']
            return hardware
        else:
            print(r)
            sys.exit(0)

    # Call to get elements of hardware
    def getElements(self, params=None):
        url = 'https://apx.cisco.com/cs/api/v1/inventory/network-elements'
        queryString = '?customerId={}&inventoryName={}'.format(self.customerId,self.inventory)
        url += queryString
        if params:
            for param in params:
                url += '&{}={}'.format(param, params[param])
        r = requests.get(url, headers=self.headers)
        r.close()
        if r.ok:
            elements = r.json()['data']
            return elements
        else:
            print(r)
            sys.exit(0)
        

    def getHardwareEol(self, params=None):
        url = 'https://apx.cisco.com/cs/api/v1/product-alerts/hardware-eol'
        queryString = '?customerId={}&inventoryName={}'.format(self.customerId,self.inventory)
        url += queryString
        if params:
            for param in params:
                url += '&{}={}'.format(param, params[param])
        r = requests.get(url, headers=self.headers)
        r.close()
        if r.ok:
            eolHw = r.json()['data']
            return eolHw
        else:
            print(r)
            sys.exit(0)
    
    def getHardwareEolMilestones(self, params=None):
        url = 'https://apx.cisco.com/cs/api/v1/product-alerts/hardware-eol-milestones-by-product-family'
        queryString = '?customerId={}'.format(self.customerId)
        url += queryString
        if params:
            for param in params:
                url += '&{}={}'.format(param, params[param])
        r = requests.get(url, headers=self.headers)
        print(r.text)
        r.close()
        if r.ok:
            eolHwMilestones = r.json()['data']
            return eolHwMilestones
        else:
            print(r)
            sys.exit(0)
    
    def getCoverage(self, params=None):
        url = 'https://apx.cisco.com/cs/api/v1/contracts/coverage'
        queryString = '?customerId={}&inventoryName={}'.format(self.customerId,self.inventory)
        url += queryString
        if params:
            for param in params:
                url += '&{}={}'.format(param, params[param])
        r = requests.get(url, headers=self.headers)
        r.close()
        coverage = r.json()['data']
        return coverage

    def getNotCovered(self, params=None):
        url = 'https://apx.cisco.com/cs/api/v1/contracts/not-covered'
        queryString = '?customerId={}&inventoryName={}'.format(self.customerId,self.inventory)
        url += queryString
        if params:
            for param in params:
                url += '&{}={}'.format(param, params[param])
        r = requests.get(url, headers=self.headers)
        r.close()
        notCovered = r.json()['data']
        return notCovered
    
    def getContracts(self, params=None):
        url = 'https://apx.cisco.com/cs/api/v1/contracts/contract-details'
        queryString = '?customerId={}&inventoryName={}'.format(self.customerId,self.inventory)
        url += queryString
        if params:
            for param in params:
                url += '&{}={}'.format(param, params[param])
        r = requests.get(url, headers=self.headers)
        r.close()
        contracts = r.json()['data']
        return contracts

    def getBetaEol(self, params=None):
        url = 'https://apx.cisco.com/cs/api/v1.0beta/product-alerts/hardware-eol'
        queryString = '?customerId={}&inventoryName={}'.format(self.customerId,self.inventory)
        url += queryString
        if params:
            for param in params:
                url += '&{}={}'.format(param, params[param])
        r = requests.get(url, headers=self.headers)
        r.close()
        print(r.text)
        contracts = r.json()['data']
        return contracts