'''
// Good luck with this code. Do praise if its good.
// And dont curse if its bad :)
Author: Vreddhi Bhat
Contact: vbhat@akamai.com
'''

import json
from akamai.edgegrid import EdgeGridAuth
from PapiWrapper import PapiWrapper
import argparse
import configparser
import requests
import os
import logging

#Setup logging
if not os.path.exists('logs'):
    os.makedirs('logs')
logFile = os.path.join('logs', 'akamaiconfigkit_log.log')

#Set the format of logging in console and file seperately
logFormatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
consoleFormatter = logging.Formatter("%(message)s")
rootLogger = logging.getLogger()


logfileHandler = logging.FileHandler(logFile, mode='w')
logfileHandler.setFormatter(logFormatter)
rootLogger.addHandler(logfileHandler)

consoleHandler = logging.StreamHandler()
consoleHandler.setFormatter(consoleFormatter)
rootLogger.addHandler(consoleHandler)
#Set Log Level to DEBUG, INFO, WARNING, ERROR, CRITICAL
rootLogger.setLevel(logging.INFO)

try:
    config = configparser.ConfigParser()
    config.read(os.path.join(os.path.expanduser("~"),'.edgerc'))
    client_token = config['papi']['client_token']
    client_secret = config['papi']['client_secret']
    access_token = config['papi']['access_token']
    access_hostname = config['papi']['hostname']
    session = requests.Session()
    session.auth = EdgeGridAuth(
    			client_token = client_token,
    			client_secret = client_secret,
    			access_token = access_token
                )
except (NameError, AttributeError, KeyError):
    rootLogger.info('\nLooks like ' + os.path.join(os.path.expanduser("~"),'.edgerc') + ' is missing or has invalid entries\n')
    exit()

#Main arguments
parser = argparse.ArgumentParser()
parser.add_argument("-help",help="Use -h for detailed help options",action="store_true")
parser.add_argument("-setup",help="Setup a local repository of group and property details",action="store_true")

parser.add_argument("-debug",help="DEBUG mode to generate additional logs for troubleshooting",action="store_true")

args = parser.parse_args()


if not args.setup:
    rootLogger.info("Use -h for help options")
    exit()

#Override log level if user wants to run in debug mode
#Set Log Level to DEBUG, INFO, WARNING, ERROR, CRITICAL
if args.debug:
    rootLogger.setLevel(logging.DEBUG)


if args.setup:
    #Create setup folder if it does not exist
    if not os.path.exists('setup'):
        os.makedirs('setup')
    #Create setup/contracts folder if it does not exist
    contractsFolder = os.path.join('setup','contracts')
    if not os.path.exists(contractsFolder):
        os.makedirs(contractsFolder)
    papiObject = PapiWrapper(access_hostname)
    rootLogger.info('Setting up pre-requisites')
    contractsObject = papiObject.getContracts(session)
    if contractsObject.status_code == 200:
        with open(os.path.join('setup','contracts','contracts.json'),'w') as contractsFile:
            contractsFile.write(json.dumps(contractsObject.json(), indent = 4))
        for eachContract in contractsObject.json()['contracts']['items']:
            contractsName = eachContract['contractTypeName']
            contractId = eachContract['contractId']
            contractFolder = os.path.join('setup','contracts', contractId)
            if not os.path.exists(contractFolder):
                os.makedirs(contractFolder)

            #Let us find out the products in this contract now
            productsObject = papiObject.listProducts(session, contractId=contractId)
            if productsObject.status_code == 200:
                with open(os.path.join('setup','contracts',contractId,'products.json'),'w') as productsFile:
                    productsFile.write(json.dumps(productsObject.json(), indent = 4))
            else:
                rootLogger.info('WARNING: Unable to fetch products for contract ' + contractId)

            #Create master properties.json file under each contract folder
            with open(os.path.join('setup','contracts',contractId,'properties.json'),'w') as propertiesFileHandler:
                #Do Nothing
                pass

            #Create master edgehostname.json file under each contract folder
            with open(os.path.join('setup','contracts',contractId,'edgehostname.json'),'w') as edgehostnameFileHandler:
                #Do Nothing
                pass
    else:
        rootLogger.info('Unable to fetch Contract related info, use -debug option to know more')
        rootLogger.debug(json.dumps(contractsObject.json(), indent = 4))

    #Lets now move towards groups
    #Groups API call does not take contractId, so some advanced logic to parse response
    groupsObject = papiObject.getGroups(session)
    if groupsObject.status_code == 200:
        #rootLogger.info(json.dumps(groupsObject.json(), indent = 4))
        for everyGroup in groupsObject.json()['groups']['items']:
            groupName = everyGroup['groupName']
            groupId = everyGroup['groupId']
            rootLogger.info('-------------- *************** --------------')
            rootLogger.info('Processing group: ' + groupName)
            if 'contractIds' in everyGroup:
                for everyContract in everyGroup['contractIds']:
                    #Logic to extract group info and move it to right contract folder
                    contractId = everyContract
                    groupsFolder = os.path.join('setup','contracts',contractId,'groups')
                    if not os.path.exists(groupsFolder):
                        os.makedirs(groupsFolder)
                    try:
                        groupFile = groupName + '.json'
                        with open(os.path.join(groupsFolder,groupFile), 'w') as groupFileHandler:
                            groupFileHandler.write(json.dumps(everyGroup, indent = 4))
                    except FileNotFoundError:
                        rootLogger.info('Unable to write file ' + groupName + '.json')

                    #Lets now move to create properties folder
                    #Logic to extract properties info and move it to right contract folder
                    propertiesFolder = os.path.join('setup','contracts',contractId,'properties')
                    if not os.path.exists(propertiesFolder):
                        os.makedirs(propertiesFolder)
                    rootLogger.info('Fetching Properties info of group: ' + groupName)
                    propertiesObject = papiObject.getAllProperties(session, contractId, groupId)
                    if propertiesObject.status_code == 200:
                        #Remove the unwanted data
                        for everyProperty in propertiesObject.json()['properties']['items']:
                            if 'accountId' in everyProperty: del everyProperty['accountId']
                            if 'latestVersion' in everyProperty: del everyProperty['latestVersion']
                            if 'stagingVersion' in everyProperty: del everyProperty['stagingVersion']
                            if 'productionVersion' in everyProperty: del everyProperty['productionVersion']
                            if 'note' in everyProperty: del everyProperty['note']

                            propertyName = everyProperty['propertyName']
                            propertyFile = everyProperty['propertyName'] + '.json'
                            try:
                                with open(os.path.join(propertiesFolder,propertyFile), 'w') as propertyFileHandler:
                                    propertyFileHandler.write(json.dumps(everyProperty, indent = 4))
                            except FileNotFoundError:
                                rootLogger.info('Unable to write file ' + propertyName + '.json')
                            #Update the master propeties.json file under each contract
                            with open(os.path.join('setup','contracts',contractId,'properties.json'),'a') as propertiesFileHandler:
                                propertiesFileHandler.write(json.dumps(everyProperty, indent = 4))
                                propertiesFileHandler.write(',')
                    else:
                        rootLogger.info('Unable to fetch properties info for group: ' + groupId + ' contract: ' + contractId)

                    #Let us now focus on edgehostnames
                    edgehostnamesFolder = os.path.join('setup','contracts',contractId,'edgehostnames')
                    if not os.path.exists(edgehostnamesFolder):
                        os.makedirs(edgehostnamesFolder)
                    rootLogger.info('Fetching EdgeHostname details under group: ' + groupName)
                    edgehostnameObject = papiObject.listEdgeHostnames(session, contractId=contractId, groupId=groupId)
                    if edgehostnameObject.status_code == 200:
                        for everyEdgeHostNameDetail in edgehostnameObject.json()['edgeHostnames']['items']:
                            edgeHostnameDomain = everyEdgeHostNameDetail['edgeHostnameDomain']
                            edgehostnameFile = everyEdgeHostNameDetail['edgeHostnameDomain'] + '.json'
                            try:
                                edgehostnamesFile = groupName + '.json'
                                with open(os.path.join(edgehostnamesFolder,edgehostnameFile), 'w') as edgehostnameFileHandler:
                                    edgehostnameFileHandler.write(json.dumps(everyEdgeHostNameDetail, indent = 4))
                            except FileNotFoundError:
                                rootLogger.info('Unable to write file ' + edgeHostnameDomain + '.json')
                            #Update the master edgehostname.json file under each contract
                            with open(os.path.join('setup','contracts',contractId,'edgehostname.json'),'a') as edgehostnamesFileHandler:
                                edgehostnamesFileHandler.write(json.dumps(everyEdgeHostNameDetail, indent = 4))
                                edgehostnamesFileHandler.write(',')
                    else:
                        rootLogger.info('Unable to retrieve edgehostname details under group: ' + groupName + ' contract: ' + contractId)
                rootLogger.info('-------------- *************** --------------\n\n')
            else:
                rootLogger.info('Ignoring  Group: ' + groupName + ' as it is not associated to any Contract' )
    else:
        rootLogger.info('Unable to fetch group related information')

    #Remove the last comma in the master files
    for (dirPath, dirNames, filenames) in os.walk(os.getcwd()):
        for everyFilename in filenames:
            if everyFilename == 'properties.json' or everyFilename == 'edgehostname.json':
                with open(os.path.join('setup','contracts',contractId,everyFilename),'r+') as masterFileHandler:
                    masterFileContent = masterFileHandler.read().rstrip(',')
                    masterFileHandler.write(masterFileContent)
