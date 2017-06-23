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
import helper
import re

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
parser.add_argument("-downloadRule",help="Download a specific rule in a configuration into json format",action="store_true")
parser.add_argument("-addRule",help="Add a raw json rule to an existing configuration (before or after and existing rule)",action="store_true")
parser.add_argument("-replaceRule",help="Replace an existing json rule",action="store_true")
parser.add_argument("-getDetail",help="Retrieves the detailed information about property",action="store_true")
parser.add_argument("-listRules",help="Retrieves the detailed information about property",action="store_true")

#Additional arguments
parser.add_argument("-property",help="Property name")
parser.add_argument("-version",help="version number or the text 'LATEST' which will fetch the latest version")
parser.add_argument("-fromVersion",help="Base version number from which the relevant operation is performed")
parser.add_argument("-outputFilename",help="Filename to be used to save the rule in json format under samplerules folder")
parser.add_argument("-fromFile",help="Filename to be used to read from the rule template under samplerules folder")
parser.add_argument("-insertAfter",help="This inserts rule after the rulename specified using -ruleName",action="store_true")
parser.add_argument("-insertBefore",help="This inserts rule before the rulename specified using -ruleName",action="store_true")
parser.add_argument("-insertLast",help="This inserts rule at the end of configuration",action="store_true")
parser.add_argument("-ruleName",help="Rule Name to find")

parser.add_argument("-debug",help="DEBUG mode to generate additional logs for troubleshooting",action="store_true")

args = parser.parse_args()


if not args.downloadRule and not args.addRule and not args.replaceRule and not args.property \
    and not args.version and not args.outputFilename and not args.fromFile and not args.insertAfter \
    and not args.insertBefore and not args.insertLast and not args.ruleName and not args.getDetail \
    and not args.fromVersion and not args.listRules:
    rootLogger.info("Use -h for help options")
    exit()

if args.downloadRule:
    papiObject = PapiWrapper(access_hostname)
    if not args.property:
        rootLogger.info('Please enter property name using -property.')
        exit()
    if not args.version:
        rootLogger.info('Please enter the version using -version.')
        exit()
    if not args.ruleName:
        rootLogger.info('Please enter the rule name using -ruleName.')
        exit()

    #Find the property details (IDs)
    propertyDetails = helper.getPropertyDetailsFromLocalStore(args.property)
    #Check if it not an empty response
    if propertyDetails:
        rootLogger.info('Found Property Details: ')
        rootLogger.info('contractId: ' + propertyDetails['contractId'])
        rootLogger.info('groupId: ' + propertyDetails['groupId'] )
        rootLogger.info('propertyId: ' + propertyDetails['propertyId']+ '\n')
        pass
    else:
        rootLogger.info('Property details were not found. Try running setup again, or double check property name\n')
        exit()

    #Fetch the latest version if need be
    if args.version.upper() == 'latest'.upper():
        rootLogger.info('Fetching latest version.')
        versionResponse = papiObject.getVersion(session, property_name=args.property, activeOn=args.version.upper(), propertyId=propertyDetails['propertyId'], contractId=propertyDetails['contractId'], groupId=propertyDetails['groupId'])
        if versionResponse.status_code == 200:
            version = versionResponse.json()['versions']['items'][0]['propertyVersion']
            rootLogger.info('Latest version is: v' + str(version) + '\n')
    else:
        version = args.version
        #Validate the version number entered using -version
        rootLogger.info('Fetching version ' + args.version + ' ...')
        versionResponse = papiObject.getVersion(session, property_name=args.property, activeOn='LATEST', propertyId=propertyDetails['propertyId'], contractId=propertyDetails['contractId'], groupId=propertyDetails['groupId'])
        latestversion = versionResponse.json()['versions']['items'][0]['propertyVersion']
        if int(args.version) > int(latestversion):
            rootLogger.info('Please check the version number. The latest version is: ' + str(latestversion) + '\n')
            exit()
        else:
            rootLogger.info('Found version...\n')

    #Let us now move towards rules
    #All rules are saved in samplerules folder, filename is configurable
    rootLogger.info('Fetching property rules...')
    rootLogger.info('Searching for Rule: ' + args.ruleName + '\n')
    ruleName = args.ruleName
    if not os.path.exists(os.path.join('samplerules')):
        os.mkdir(os.path.join('samplerules'))

    #Specify the filename to store the rule set
    if args.outputFilename:
        filename = args.outputFilename
    else:
        filename = args.property + '_v' + str(version) + '_' + args.ruleName + '.json'
    #Replace special characters from filename with _, sometimes rulenames have special chars
    filename = filename.translate ({ord(c): "_" for c in " !@#$%^&*()[]{};:,/<>?\|`~-=_+"})
    propertyContent = papiObject.getPropertyRulesfromPropertyId(session, propertyDetails['propertyId'], version, propertyDetails['contractId'], propertyDetails['groupId'])
    if propertyContent.status_code == 200:
        jsonRuleAndCount = helper.getRule([propertyContent.json()['rules']], args.ruleName)
        if jsonRuleAndCount['ruleCount'] > 1:
            rootLogger.info('\nMultiple Rules named: "' + args.ruleName + '" exist, please check configuration\n')
            exit()
        elif jsonRuleAndCount['ruleCount'] == 1:
            rootLogger.info('Found rule...')
            with open(os.path.join('samplerules',filename),'w') as rulesFileHandler:
                rulesFileHandler.write(json.dumps(jsonRuleAndCount['ruleContent'], indent=4))
                rootLogger.info('Rule file is saved in: ' + os.path.join('samplerules',filename))
        else:
            rootLogger.info('Rule: ' + args.ruleName + ' is not found.')
            exit()
    else:
        rootLogger.info('Unable to fecth property rules.')
        exit()

if args.addRule or args.replaceRule:
    papiObject = PapiWrapper(access_hostname)
    if not args.property:
        rootLogger.info('\nPlease enter property name using -property.')
        exit()
    if not args.fromVersion:
        rootLogger.info('\nPlease enter the version using -fromVersion.')
        exit()
    if not args.fromFile:
        rootLogger.info('\nPlease enter the filename containing rule(s) using -fromFile.')
        exit()
    #Check for existence of file
    try:
        with open(os.path.join('samplerules',args.fromFile),'r') as rulesFileHandler:
            pass
    except FileNotFoundError:
        rootLogger.info('\nEntered filename does not exist. Ensure file is present in samplerules directory.')
        exit()

    if args.addRule:
        if not args.insertAfter and not args.insertBefore and not args.insertLast:
            rootLogger.info('Specify where to add the rule to using -insertAfter or -insertBefore or -insertLast.\n')
            exit()

        if args.insertAfter or args.insertBefore:
            if not args.ruleName:
                rootLogger.info('Please enter the ruleName using -ruleName.')
                exit()
            if args.insertAfter:
                whereTo = 'insertAfter'
                comment = 'after'
            if args.insertBefore:
                whereTo = 'insertBefore'
                comment = 'before'

        if args.insertLast:
            whereTo = 'insertLast'
            comment = 'at the end'
            args.ruleName = 'default'

    if args.replaceRule:
        whereTo = 'replace'

    version = args.fromVersion
    #Find the property details (IDs)
    propertyDetails = helper.getPropertyDetailsFromLocalStore(args.property)
    #Check if it not an empty response
    if propertyDetails:
        rootLogger.info('Found Property Details:')
        rootLogger.info('contractId: ' + propertyDetails['contractId'])
        rootLogger.info('groupId: ' + propertyDetails['groupId'] )
        rootLogger.info('propertyId: ' + propertyDetails['propertyId']+ '\n')
        pass
    else:
        rootLogger.info('Property details were not found. Try running setup again, or double check property name\n')
        exit()

    #Fetch the latest version if need be
    rootLogger.info('Fetching version ' + version + ' ...')
    if version.upper() == 'latest'.upper():
        versionResponse = papiObject.getVersion(session, property_name=args.property, activeOn=version.upper(), propertyId=propertyDetails['propertyId'], contractId=propertyDetails['contractId'], groupId=propertyDetails['groupId'])
        version = versionResponse.json()['versions']['items'][0]['propertyVersion']
    else:
        #Validate the version number entered using -fromVersion
        versionResponse = papiObject.getVersion(session, property_name=args.property, activeOn='LATEST', propertyId=propertyDetails['propertyId'], contractId=propertyDetails['contractId'], groupId=propertyDetails['groupId'])
        latestversion = versionResponse.json()['versions']['items'][0]['propertyVersion']
        if int(version) > int(latestversion):
            rootLogger.info('Please check the version number. The highest/latest version is: ' + str(latestversion) + '\n')
            exit()
        else:
            rootLogger.info('Found Version...\n')

    #Let us now move towards rules
    #All rules are saved in samplerules folder, filename is configurable
    rootLogger.info('Fetching existing property rules...')
    propertyContent = papiObject.getPropertyRulesfromPropertyId(session, propertyDetails['propertyId'], version, propertyDetails['contractId'], propertyDetails['groupId'])
    if propertyContent.status_code == 200:
        completePropertyJson = propertyContent.json()
        with open(os.path.join('samplerules',args.fromFile),'r') as rulesFileHandler:
            newRuleSet = json.loads(rulesFileHandler.read())

        rootLogger.info('\nFound rule file: ' + args.fromFile)
        updatedCompleteRuleSet = helper.insertRule([completePropertyJson['rules']], newRuleSet, args.ruleName, whereTo)
        #rootLogger.info(json.dumps(updatedCompleteRuleSet))
        #Check if we found the matching rule
        if updatedCompleteRuleSet['occurances'] > 0:
            #Check whether we found multiple rule names, if yes warn the user
            if updatedCompleteRuleSet['occurances'] == 1:
                #Overwrite the rules section with updated one
                completePropertyJson['rules'] = updatedCompleteRuleSet['completeRuleSet'][0]
                #Updating the property comments
                if args.replaceRule:
                    completePropertyJson['comments'] = 'Created from v' + str(version) + ': replacing existing rule "' + args.ruleName + '" with rule from: '+ args.fromFile
                elif comment == 'at the end':
                    completePropertyJson['comments'] = 'Created from v' + str(version) + ': adding rule ' + newRuleSet['name'] + ' ' + comment
                else:
                    completePropertyJson['comments'] = 'Created from v' + str(version) + ': adding rule ' + newRuleSet['name'] + ' '+ comment + ' ' + args.ruleName

                #Let us now create a version
                rootLogger.info('Trying to create a new version of this property based on version ' + str(version))
                versionResponse = papiObject.createVersion(session, baseVersion=version, property_name=args.property)
                if versionResponse.status_code == 201:
                    #Extract the version number
                    matchPattern = re.compile('/papi/v0/properties/prp_.*/versions/(.*)(\?.*)')
                    newVersion = matchPattern.match(versionResponse.json()['versionLink']).group(1)
                    rootLogger.info('Successfully created new property version: v' + str(newVersion))
                    #Make a call to update the rules
                    rootLogger.info('\nNow trying to upload the new ruleset...')
                    uploadRulesResponse = papiObject.uploadRules(session=session, updatedData=json.loads(json.dumps(completePropertyJson)),\
                     property_name=args.property, version=newVersion, propertyId=propertyDetails['propertyId'], contractId=propertyDetails['contractId'], groupId=propertyDetails['groupId'])
                    if uploadRulesResponse.status_code == 200:
                        rootLogger.info('Success!')
                    else:
                        rootLogger.info('Unable to update rules in property. Reason is: \n\n' + json.dumps(uploadRulesResponse.json(), indent=4))
                        exit()
                else:
                    rootLogger.info('Unable to create a new version.')
                    exit()
            else:
                rootLogger.info('\nFound ' + str(updatedCompleteRuleSet['occurances']) + ' occurences of the rule: "' + args.ruleName + '"' + '.Exiting.')
        else:
            rootLogger.info('\nUnable to find rule: "' + args.ruleName + '" in this property.')
            rootLogger.info('Check the -rulename value or run -getDetail to list existing rules for this property.')
            rootLogger.info('Exiting...')
            exit()
    else:
        rootLogger.info('Unable to fecth property rules.')
        exit()


if args.getDetail:
    papiObject = PapiWrapper(access_hostname)
    if not args.property:
        rootLogger.info('Please enter property name using -property.')
        exit()

    #Find the property details (IDs)
    propertyDetails = helper.getPropertyDetailsFromLocalStore(args.property)
    #Check if it not an empty response
    if propertyDetails:
        rootLogger.info('Found Property Details: ')
        rootLogger.info('contractId: ' + propertyDetails['contractId'])
        rootLogger.info('groupId: ' + propertyDetails['groupId'] )
        rootLogger.info('propertyId: ' + propertyDetails['propertyId']+ '\n')
        pass
    else:
        rootLogger.info('Property details were not found. Try running setup again, or double check property name\n')
        exit()

    rootLogger.info('Fetching property versions...\n')
    versionsResponse = papiObject.listVersions(session, property_name=args.property, propertyId=propertyDetails['propertyId'], contractId=propertyDetails['contractId'], groupId=propertyDetails['groupId'])
    if versionsResponse.status_code == 200:
        rootLogger.info('Current Property Details:')
        rootLogger.info('----------------------------------')
        #rootLogger.info(json.dumps(versionsResponse.json(), indent=4))
        latestVersion = 0
        stagingVersion = 0
        productionVersion = 0
        stagingNote = ''
        productionNote = ''
        latestNote = ''
        for everyVersionDetail in versionsResponse.json()['versions']['items']:
            #First update the value of latest version
            if everyVersionDetail['propertyVersion'] > latestVersion:
                latestVersion = everyVersionDetail['propertyVersion']
            if everyVersionDetail['stagingStatus'] == 'ACTIVE':
                stagingVersion = everyVersionDetail['propertyVersion']
                if 'note' in everyVersionDetail:
                    stagingNote = everyVersionDetail['note']
            if everyVersionDetail['productionStatus'] == 'ACTIVE':
                productionVersion = everyVersionDetail['propertyVersion']
                if 'note' in everyVersionDetail:
                    productionNote = everyVersionDetail['note']
        rootLogger.info('Latest version: v' + str(latestVersion))
        if stagingVersion != 0:
            rootLogger.info('Version ' + str(stagingVersion) + ' is live in staging')
        if stagingVersion == 0:
            rootLogger.info('No version is active in staging')
        if productionVersion != 0:
            rootLogger.info('Version ' + str(productionVersion) + ' is live in production')
        if productionVersion == 0:
            rootLogger.info('No version is active in production')
        #rootLogger.info('Version ' + str(latestVersion) + ' is the latest version')

        #comment this out for now? rootLogger.info('\nLast 10 versions...\n')
        rootLogger.info('\nVersion Details (Version : Description)')
        rootLogger.info('----------------------------------')

        if args.fromVersion:
            for everyVersionDetail in versionsResponse.json()['versions']['items']:
                if int(everyVersionDetail['propertyVersion']) > int(args.fromVersion):
                    if 'note' in everyVersionDetail:
                        rootLogger.info(str(everyVersionDetail['propertyVersion']) + ' ' + everyVersionDetail['note'])
                    else:
                        rootLogger.info(str(everyVersionDetail['propertyVersion']))
        else:
            for everyVersionDetail in versionsResponse.json()['versions']['items'][:10]:
                if 'note' in everyVersionDetail:
                    rootLogger.info(str(everyVersionDetail['propertyVersion']) + ' ' + everyVersionDetail['note'])
                else:
                    rootLogger.info(str(everyVersionDetail['propertyVersion']))
    else:
        rootLogger.info('Unable to fetch versions of the property')
        rootLogger.info(json.dumps(versionsResponse.json(), indent=4))
        exit()

if args.listRules:
    papiObject = PapiWrapper(access_hostname)
    if not args.property:
        rootLogger.info('\nPlease enter property name using -property.')
        exit()
    if not args.version:
        rootLogger.info('\nPlease enter the version using -version.')
        exit()

    #Find the property details (IDs)
    propertyDetails = helper.getPropertyDetailsFromLocalStore(args.property)
    #Check if it not an empty response
    if propertyDetails:
        rootLogger.info('Found Property Details: ')
        rootLogger.info('contractId: ' + propertyDetails['contractId'])
        rootLogger.info('groupId: ' + propertyDetails['groupId'] )
        rootLogger.info('propertyId: ' + propertyDetails['propertyId']+ '\n')
        pass
    else:
        rootLogger.info('Property details were not found. Try running setup again, or double check property name\n')
        exit()

    #Fetch the latest version if need be
    rootLogger.info('Fetching version ' + args.version + ' ...')
    if args.version.upper() == 'latest'.upper():
        versionResponse = papiObject.getVersion(session, property_name=args.property, activeOn=args.version.upper(), propertyId=propertyDetails['propertyId'], contractId=propertyDetails['contractId'], groupId=propertyDetails['groupId'])
        version = versionResponse.json()['versions']['items'][0]['propertyVersion']
    else:
        version = args.version
        #Validate the version number entered using -version
        versionResponse = papiObject.getVersion(session, property_name=args.property, activeOn='LATEST', propertyId=propertyDetails['propertyId'], contractId=propertyDetails['contractId'], groupId=propertyDetails['groupId'])
        latestversion = versionResponse.json()['versions']['items'][0]['propertyVersion']
        if int(args.version) > int(latestversion):
            rootLogger.info('Please check the version number. The highest/latest version is: ' + str(latestversion) + '\n')
            exit()
        else:
            rootLogger.info('Version is validated.\n')

    rootLogger.info('Fetching rules of property.\n')
    propertyContent = papiObject.getPropertyRulesfromPropertyId(session, propertyDetails['propertyId'], args.version, propertyDetails['contractId'], propertyDetails['groupId'])
    if propertyContent.status_code == 200:
        rules = helper.getAllRules([propertyContent.json()['rules']], allruleNames=[])
        rootLogger.info('Rules are:')
        rootLogger.info('---------\n')
        for eachRuleName in rules:
            rootLogger.info(eachRuleName)
    else:
        rootLogger.info('Unable to fecth rules of property.')
        exit()
