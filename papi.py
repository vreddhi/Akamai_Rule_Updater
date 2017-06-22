'''
// Good luck with this code. This leverages akamai OPEN API.
// In case you need
// explanation contact the initiators.
Initiators: vbhat@akamai.com and aetsai@akamai.com
'''

import json
from akamai.edgegrid import EdgeGridAuth
from PapiWrapper import PapiWrapper
import argparse
import configparser
import requests
import os
import logging
import re
import ast
import shutil
import helper

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
parser.add_argument("-create",help="Create a property",action="store_true")

parser.add_argument("-debug",help="DEBUG mode to generate additional logs for troubleshooting",action="store_true")

#Activate related arguments
parser.add_argument("-activate",help="Activate a given version",action="store_true")
parser.add_argument("-property",help="Enter property name")
parser.add_argument("-version",help="version number of property")
parser.add_argument("-network",help="Network to be activated on. Allowed values are staging and prod or production (case-sensitive)")
parser.add_argument("-email",help="Enter valid email addresses separated by commas")
parser.add_argument("-notes",help="Enter notes related to changes you made starting with quotes")

args = parser.parse_args()


if not args.setup and not args.create and not args.activate:
    rootLogger.info("Use -h for help options")
    exit()

#Override log level if user wants to run in debug mode
#Set Log Level to DEBUG, INFO, WARNING, ERROR, CRITICAL
if args.debug:
    rootLogger.setLevel(logging.DEBUG)

if args.setup:
    #Delete the setup folder before we start
    if os.path.exists('setup'):
        shutil.rmtree('setup')
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
    propertiesList = {}
    if contractsObject.status_code == 200:
        with open(os.path.join('setup','contracts','contracts.json'),'w') as contractsFile:
            contractsFile.write(json.dumps(contractsObject.json(), indent = 4))
        for eachContract in contractsObject.json()['contracts']['items']:
            contractsName = eachContract['contractTypeName']
            contractId = eachContract['contractId']
            propertiesList[contractId] = []
            #Create contracts folder
            contractFolder = os.path.join('setup','contracts', contractId)
            if not os.path.exists(contractFolder):
                os.makedirs(contractFolder)

            #Create groups folder
            groupsFolder = os.path.join('setup','contracts',contractId,'groups')
            if not os.path.exists(groupsFolder):
                os.makedirs(groupsFolder)

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
            with open(os.path.join('setup','contracts',contractId,'edgehostnames.json'),'w') as edgehostnameFileHandler:
                #Do Nothing
                pass

            #Create master edgehostname.json file under each contract folder
            with open(os.path.join('setup','contracts',contractId,'groups','groups.json'),'w') as GroupsFileHandler:
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
                    try:
                        #Update the master groups file
                        with open(os.path.join('setup','contracts',contractId,'groups','groups.json'),'a') as GroupsFileHandler:
                            GroupsFileHandler.write(json.dumps(everyGroup, indent = 4))
                        #Create individual groups file
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
                            #Update the propertiesList list with property details
                            propertiesList[contractId].append(everyProperty)
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
                            with open(os.path.join('setup','contracts',contractId,'edgehostnames.json'),'a') as edgehostnamesFileHandler:
                                edgehostnamesFileHandler.write(',')
                                edgehostnamesFileHandler.write(json.dumps(everyEdgeHostNameDetail, indent = 4))
                                edgehostnamesFileHandler.write(',')
                    else:
                        rootLogger.info('Unable to retrieve edgehostname details under group: ' + groupName + ' contract: ' + contractId)
                rootLogger.info('-------------- *************** --------------\n\n')
            else:
                rootLogger.info('Ignoring  Group: ' + groupName + ' as it is not associated to any Contract' )

        #Update the master propeties.json file under each contract
        for contractItem in propertiesList:
            with open(os.path.join('setup','contracts',contractItem,'properties.json'),'w') as propertiesFileHandler:
                propertiesFileHandler.write(json.dumps(propertiesList[contractItem], indent = 4))
    else:
        rootLogger.info('Unable to fetch group related information')

    #Remove the last comma in the master files
    for (dirPath, dirNames, filenames) in os.walk(os.getcwd()):
        for everyFilename in filenames:
            if everyFilename == 'properties.json' or everyFilename == 'edgehostname.json':
                with open(os.path.join('setup','contracts',contractId,everyFilename),'r+') as masterFileHandler:
                    masterFileContent = masterFileHandler.read().rstrip(',')
                    masterFileContent = masterFileHandler.read().lstrip(',')
                    masterFileHandler.write(masterFileContent)

if args.create:
    try:
        recommendedValues = configparser.ConfigParser()
        recommendedValues.read(os.path.join('config','akau4_template.txt'))
        sections = recommendedValues.sections()

        with open(os.path.join('config','iontemplate_parameters.json'),'r') as templateFileHandler:
            templateFileContent = templateFileHandler.read()

        accountId = recommendedValues['property_setup']['accountId']
        contractId = recommendedValues['property_setup']['contractId']
        groupId = recommendedValues['property_setup']['groupId']
        templateFileContent = templateFileContent.replace('|prop.accountId|',recommendedValues['property_setup']['accountId'])
        templateFileContent = templateFileContent.replace('|prop.contractId|',recommendedValues['property_setup']['contractId'])
        templateFileContent = templateFileContent.replace('|prop.groupId|',recommendedValues['property_setup']['groupId'])

        templateFileContent = templateFileContent.replace('|prop.propertyName|',recommendedValues['property_info']['propertyName'])
        templateFileContent = templateFileContent.replace('"|prop.cpcode|"',recommendedValues['property_info']['cpcode'])
        templateFileContent = templateFileContent.replace('|prop.originHostname|',recommendedValues['property_info']['originHostname'])
        templateFileContent = templateFileContent.replace('|prop.siteShieldName|',recommendedValues['property_info']['siteShieldName'])
        templateFileContent = templateFileContent.replace('|prop.sureRouteTestObjectUrl|',recommendedValues['property_info']['sureRouteTestObjectUrl'])
        templateFileContent = templateFileContent.replace('|prop.sureRouteCustomMap|',recommendedValues['property_info']['sureRouteCustomMap'])

        templateFileContentJson = json.loads(templateFileContent)

        productId = 'prd_' + recommendedValues['property_setup']['productid']
        new_property_name = recommendedValues['property_info']['propertyName']
        hostname = recommendedValues['property_hostnames']['publicHostname']
        edgeHostname = recommendedValues['property_hostnames']['useEdgehostnameId']
        papiObject = PapiWrapper(access_hostname)

        rootLogger.info('\nCreating a new property with name: ' + new_property_name)
        createResponse = papiObject.createConfig(session, new_property_name, productId,contractId=contractId, groupId=groupId)
        if createResponse.status_code == 201:
            matchPattern = re.compile('/papi/v0/properties/(.*)(\?.*)')
            propertyId = matchPattern.match(createResponse.json()['propertyLink']).group(1)
            rootLogger.info('Property created with propertyId: ' + propertyId)

            #Make a call to create a edgehostname
            rootLogger.info('\nCreating the Edgehostname: ' + hostname + '.edgesuite.net')
            createEdgeHostnameResponse = papiObject.createEdgeHostname(session, hostname, productId, contractId, groupId)
            if createEdgeHostnameResponse.status_code == 201:
                matchPattern = re.compile('/papi/v0/edgehostnames/(.*)(\?.*)')
                edgeHostnameId = matchPattern.match(createEdgeHostnameResponse.json()['edgeHostnameLink']).group(1)
                rootLogger.info('Successfully created edgehostname with Id: ' + edgeHostnameId)
            else:
                rootLogger.info('Unable to create edgehostname. Reason is: \n\n' + json.dumps(createEdgeHostnameResponse.json(), indent=4))
                exit()

            #Make a call to update the hostname in property
            rootLogger.info('\nUpdating the property with hostname: ' + hostname + ' and the Edgehostname: ' + hostname + '.edgesuite.net')
            updateHostnameRespose = papiObject.updateHostname(session, hostname, edgeHostnameId,1, propertyId, contractId, groupId)
            if updateHostnameRespose.status_code == 200:
                rootLogger.info('Successfully added hostname: '+ hostname + ' to property: ' + new_property_name)
            else:
                rootLogger.info('Unable to update hostname in property. Reason is: \n\n' + json.dumps(updateHostnameRespose.json(), indent=4))
                exit()

            #Make a call to update the rules based on template
            rootLogger.info('\nUpdating the rules based on the values from template: ' + os.path.join('config','iontemplate_parameters.json'))
            uploadRulesResponse = papiObject.uploadRules(session=session, updatedData=templateFileContentJson, property_name=new_property_name, version=1, propertyId=propertyId, contractId=contractId, groupId=groupId)
            if uploadRulesResponse.status_code == 200:
                rootLogger.info('Updated rules successfully')
            else:
                rootLogger.info('Unable to update hostname in property. Reason is: \n\n' + json.dumps(uploadRulesResponse.json(), indent=4))
                exit()

            #Lets activate on staging
            rootLogger.info('\nActivating the configuration on akamai staging')
            emailList = ['vbhat@akamai.com']
            notes = 'Test activation from PAPI'
            activateResponse = papiObject.activateConfiguration(session=session, property_name=new_property_name, version=1, network='STAGING', emailList=emailList, notes=notes, propertyId=propertyId, contractId=contractId, groupId=groupId)
            if activateResponse.status_code == 201:
                rootLogger.info('Activation successful. Please wait for ~10 minutes')
                rootLogger.info('You can track activation here: ' + activateResponse.json()['activationLink'])
            else:
                rootLogger.info('Unable to activate configuration. Reason is: \n\n' + json.dumps(activateResponse.json(), indent=4))
                exit()

        else:
            rootLogger.info('Unable to create property.Exiting. Reason is: \n\n' + json.dumps(createResponse.json(), indent=4))
            exit()
    except (NameError, AttributeError, KeyError, FileNotFoundError) as e:
        rootLogger.info(e)
        exit()

#Property Activation Code
if args.activate:
    if not os.path.exists('setup'):
        rootLogger.info('Please run -setup before activating a config')
        exit()

    if not args.property:
        rootLogger.info('Please enter property name using -propertyName option.')
        exit()
    propertyName = args.property

    if not args.version:
        rootLogger.info('Please enter property version using -version option.')
        exit()
    version = args.version

    if not args.network:
        rootLogger.info('Please enter network using -network option.')
        exit()
    network = args.network

    if not args.email:
        rootLogger.info('Please enter valid email addresses using -email option.')
        exit()
    emailList = args.email.split(',')
    #print ("Email id is",emailList)

#Making notes optional
    if args.notes:
        notes = args.notes
    else:
        notes = ''
    #print ("Notes are",notes)



    #Find the property details (IDs)
    propertyDetails = helper.getPropertyDetailsFromLocalStore(args.property)
    #Check if it not an empty response
    if propertyDetails:
        rootLogger.info('PropertyDetails are found: ')
        #rootLogger.info('Property ID: ' + propertyDetails['propertyId'])
        #rootLogger.info('Contract ID: ' + propertyDetails['contractId'])
        #rootLogger.info('Group ID: ' + propertyDetails['groupId'] + '\n')

        propertyId = propertyDetails['propertyId']
        contractId = propertyDetails['contractId']
        groupId    = propertyDetails['groupId']

        pass
    else:
        rootLogger.info('Property details were not found. Try running setup again, or doublecheck property name\n')
        exit()

     #Lets activate on staging
    
    rootLogger.info('\nActivating the configuration on akamai')
    #emailList = ['bdutia@akamai.com']
    #notes = ''  

    papiObject = PapiWrapper(access_hostname)
    activateResponse = papiObject.activateConfiguration(session=session, property_name=args.property, version=version, network=args.network, emailList=emailList, notes=notes, propertyId=propertyId, contractId=contractId, groupId=groupId)
    if activateResponse.status_code == 201:
        rootLogger.info('Activation successful. Please wait for ~10 minutes')
        rootLogger.info('You can track activation here: ' + activateResponse.json()['activationLink'])
    else:
        rootLogger.info('Unable to activate configuration. Reason is: \n\n' + json.dumps(activateResponse.json(), indent=4))
        exit()        