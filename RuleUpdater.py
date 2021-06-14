"""
Copyright 2021 Akamai Technologies, Inc. All Rights Reserved.

 Licensed under the Apache License, Version 2.0 (the "License");
 you may not use this file except in compliance with the License.
 You may obtain a copy of the License at
    http://www.apache.org/licenses/LICENSE-2.0
 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 See the License for the specific language governing permissions and
 limitations under the License.
"""

"""
This code leverages akamai OPEN API. to control Certificates deployed in Akamai Network.
In case you need quick explanation contact the initiators.
Initiators: vbhat@akamai.com, aetsai@akamai.com, mkilmer@akamai.com
"""

import json
import sys
from akamai.edgegrid import EdgeGridAuth, EdgeRc
from PapiWrapper import PapiWrapper
import argparse
import configparser
import requests
import os
import logging
import helper
import re
import shutil


PACKAGE_VERSION = "1.0.8"

# Setup logging
if not os.path.exists('logs'):
    os.makedirs('logs')
log_file = os.path.join('logs', 'ruleupdater.log')

# Set the format of logging in console and file separately
log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_formatter = logging.Formatter("%(message)s")
root_logger = logging.getLogger()

logfile_handler = logging.FileHandler(log_file, mode='a')
logfile_handler.setFormatter(log_formatter)
root_logger.addHandler(logfile_handler)

console_handler = logging.StreamHandler()
console_handler.setFormatter(console_formatter)
root_logger.addHandler(console_handler)
# Set Log Level to DEBUG, INFO, WARNING, ERROR, CRITICAL
root_logger.setLevel(logging.INFO)


def init_config(edgerc_file, section):
    if not edgerc_file:
        if not os.getenv("AKAMAI_EDGERC"):
            edgerc_file = os.path.join(os.path.expanduser("~"), '.edgerc')
        else:
            edgerc_file = os.getenv("AKAMAI_EDGERC")

    if not os.access(edgerc_file, os.R_OK):
        root_logger.error("Unable to read edgerc file \"%s\"" % edgerc_file)
        exit(1)

    if not section:
        if not os.getenv("AKAMAI_EDGERC_SECTION"):
            section = "papi"
        else:
            section = os.getenv("AKAMAI_EDGERC_SECTION")


    try:
        edgerc = EdgeRc(edgerc_file)
        base_url = edgerc.get(section, 'host')

        session = requests.Session()
        session.auth = EdgeGridAuth.from_edgerc(edgerc, section)

        return base_url, session
    except configparser.NoSectionError:
        root_logger.error("Edgerc section \"%s\" not found" % section)
        exit(1)
    except Exception:
        root_logger.info(
            "Unknown error occurred trying to read edgerc file (%s)" %
            edgerc_file)
        exit(1)


def cli():
    prog = get_prog_name()
    if len(sys.argv) == 1:
        prog += " [command]"

    parser = argparse.ArgumentParser(
        description='Akamai CLI for RuleUpdater',
        add_help=False,
        prog=prog)
    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s ' +
                PACKAGE_VERSION)

    subparsers = parser.add_subparsers(
        title='Commands', dest="command", metavar="")

    actions = {}

    subparsers.add_parser(
        name="help",
        help="Show available help",
        add_help=False).add_argument(
        'args',
        metavar="",
        nargs=argparse.REMAINDER)

    actions["downloadRule"] = create_sub_command(
        subparsers,
        "downloadRule",
        "Download a specific rule in a configuration into json format",
        [{"name": "outputFilename", "help": "Filename to be used to save the rule in json format under samplerules folder"}],
        [{"name": "property", "help": "Property name"},
         {"name": "version", "help": "version number or the text 'LATEST/PRODUCTION/STAGING' which will fetch the latest version"},
         {"name": "ruleName", "help": "Rule Name to find"}])

    actions["addRule"] = create_sub_command(
        subparsers, "addRule", "Add a raw json rule to an existing configuration (before or after and existing rule)",
        [{"name": "insertAfter", "help": "This inserts rule after the rulename specified using -ruleName"},
         {"name": "insertBefore", "help": "This inserts rule before the rulename specified using -ruleName"},
         {"name": "insertLast", "help": "This inserts rule at the end of configuration"},
         {"name": "addVariables", "help": "This declares new variables in the configuration"},
         {"name": "variableFile", "help": "File containing variable definition. It should be a JSON file with name/value/descripton map"},
         {"name": "ruleName", "help": "Rule Name to find"}],
        [{"name": "property", "help": "Property name"},
         {"name": "fromVersion", "help": "Base version number from which the relevant operation is performed"},
         {"name": "fromFile", "help": "Filename to be used to read from the rule template under samplerules folder"},
         {"name": "comment", "help": "Version notes to be saved"}])

    actions["replaceRule"] = create_sub_command(
        subparsers, "replaceRule", "Replace an existing json rule",
        [],
        [{"name": "property", "help": "Property name"},
         {"name": "fromVersion", "help": "Base version number from which the relevant operation is performed"},
         {"name": "fromFile", "help": "Filename to be used to read from the rule template under samplerules folder"},
         {"name": "ruleName", "help": "Rule Name to find"},
         {"name": "comment", "help": "Version notes to be saved"}])

    actions["deleteRule"] = create_sub_command(
        subparsers, "deleteRule",
        "Delete an existing rule)",
        [],
        [{"name": "property", "help": "Property name"},
         {"name": "version", "help": "Please enter the version to use/create from using --version."},
         {"name": "comment", "help": "Please enter the comment/version notes using --comment."},
         {"name": "ruleName", "help": "Please enter the rule name where behavior needs to be added."},
         {"name": "checkoutNewVersion", "help": "Please enter whether to create a new version or use existing version using -checkoutNewVersion YES/NO."},])

    actions["getDetail"] = create_sub_command(
        subparsers, "getDetail",
        "Retrieves the detailed information about property ",
        [{"name": "fromVersion", "help": "Base version number from which the relevant operation is performed"}],
        [{"name": "property", "help": "Property name"}])         

    actions["listRules"] = create_sub_command(
        subparsers, "listRules", "Retrieves the detailed information about property",
        [],
        [{"name": "property", "help": "Property name"},
         {"name": "version", "help": "version number or the text LATEST"}])

    actions["addBehavior"] = create_sub_command(
        subparsers, "addBehavior",
        "Add a raw json behavior to an existing rule",
        [],
        [{"name": "property", "help": "Property name"},
         {"name": "version", "help": "Please enter the version to use/create from using --version."},
         {"name": "fromFile", "help": "Please enter the filename containing rule(s) using --fromFile."},
         {"name": "comment", "help": "Please enter the comment/version notes using --comment."},
         {"name": "ruleName", "help": "Please enter the rule name where behavior needs to be added."},
         {"name": "checkoutNewVersion", "help": "Please enter whether to create a new version or use existing version using -checkoutNewVersion YES/NO."},])

    actions["deleteBehavior"] = create_sub_command(
        subparsers, "deleteBehavior", "Delete Behavior",
        [],
        [{"name": "property", "help": "Property name"},
         {"name": "version", "help": "Please enter the version to use/create from using --version."},
         {"name": "behaviorName", "help": "Name of the behavior to be deleted."}])

    args = parser.parse_args()

    if len(sys.argv) <= 1:
        parser.print_help()
        return 0

    if args.command == "help":
        if len(args.args) > 0:
            if actions[args.args[0]]:
                actions[args.args[0]].print_help()
        else:
            parser.prog = get_prog_name() + " help [command]"
            parser.print_help()
        return 0


    # Override log level if user wants to run in debug mode
    # Set Log Level to DEBUG, INFO, WARNING, ERROR, CRITICAL
    if args.debug:
        root_logger.setLevel(logging.DEBUG)

    return getattr(sys.modules[__name__], args.command.replace("-", "_"))(args)


def create_sub_command(
        subparsers,
        name,
        help,
        optional_arguments=None,
        required_arguments=None):
    action = subparsers.add_parser(name=name, help=help, add_help=False)

    if required_arguments:
        required = action.add_argument_group("required arguments")
        for arg in required_arguments:
            name = arg["name"]
            del arg["name"]
            required.add_argument("--" + name,
                                  required=True,
                                  **arg)

    optional = action.add_argument_group("optional arguments")
    if optional_arguments:
        for arg in optional_arguments:
            name = arg["name"]
            del arg["name"]
            if name == 'insertAfter' or name == 'insertBefore' or name == 'insertLast' \
            or name == 'addVariables':
                optional.add_argument(
                    "--" + name,
                    required=False,
                    **arg,
                    action="store_true")
            else:
                optional.add_argument("--" + name,
                                      required=False,
                                      **arg)

    optional.add_argument(
        "--edgerc",
        help="Location of the credentials file [$AKAMAI_EDGERC]",
        default=os.path.join(
            os.path.expanduser("~"),
            '.edgerc'))

    optional.add_argument(
        "--section",
        help="Section of the credentials file [$AKAMAI_EDGERC_SECTION]",
        default="papi")

    optional.add_argument(
        "--debug",
        help="DEBUG mode to generate additional logs for troubleshooting",
        action="store_true")

    optional.add_argument(
        "--account-key",
        help="Account Switch Key",
        default="")

    return action


def downloadRule(args):
    access_hostname, session = init_config(args.edgerc, args.section)
    papiObject = PapiWrapper(access_hostname, args.account_key)

    #Find the property details (IDs)
    propertyResponse = papiObject.searchProperty(session,propertyName=args.property)
    if propertyResponse.status_code == 200:
        try:
            propertyDetails = propertyResponse.json()['versions']['items'][0]
        except:
            root_logger.info('Property details were not found. Double check property name\n')
            exit()                
    else:
       root_logger.info('Property details were not found. Double check property name\n')

    #Fetch the latest version if need be
    if args.version.upper() == 'latest'.upper() or args.version.upper() == 'production'.upper() or args.version.upper() == 'staging'.upper():
        root_logger.info('Fetching ' + args.version.upper() +' version.')
        versionResponse = papiObject.getVersion(session, property_name=args.property, activeOn=args.version.upper(), propertyId=propertyDetails['propertyId'], contractId=propertyDetails['contractId'], groupId=propertyDetails['groupId'])
        if versionResponse.status_code == 200:
            version = versionResponse.json()['versions']['items'][0]['propertyVersion']
            root_logger.info('Latest version is: v' + str(version) + '\n')
        else:
            root_logger.info('Unable to find the version details\n')
            root_logger.info(json.dumps(versionResponse.json(), indent=4))    
            exit()          
    else:
        version = args.version
        #Validate the version number entered using -version
        root_logger.info('Fetching version ' + args.version + ' ...')
        versionResponse = papiObject.getVersion(session, property_name=args.property, activeOn='LATEST', propertyId=propertyDetails['propertyId'], contractId=propertyDetails['contractId'], groupId=propertyDetails['groupId'])
        latestversion = versionResponse.json()['versions']['items'][0]['propertyVersion']
        if int(args.version) > int(latestversion):
            root_logger.info('Please check the version number. The latest version is: ' + str(latestversion) + '\n')
            exit()
        else:
            root_logger.info('Found version...\n')

    #Let us now move towards rules
    #All rules are saved in samplerules folder, filename is configurable
    root_logger.info('Fetching property rules...')
    root_logger.info('Searching for Rule: ' + args.ruleName + '\n')
    
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
            root_logger.info('\nMultiple Rules named: "' + args.ruleName + '" exist, please check configuration\n')
            exit()
        elif jsonRuleAndCount['ruleCount'] == 1:
            root_logger.info('Found rule...')
            with open(os.path.join('samplerules',filename),'w') as rulesFileHandler:
                rulesFileHandler.write(json.dumps(jsonRuleAndCount['ruleContent'], indent=4))
                root_logger.info('Rule file is saved in: ' + os.path.join('samplerules',filename))
        else:
            root_logger.info('Rule: ' + args.ruleName + ' is not found. Please check configuration.')
            exit()
    else:
        root_logger.info('Unable to fecth property rules.')
        exit()

def addRule(args):
    root_logger.info('Processing: ' + args.property)
    access_hostname, session = init_config(args.edgerc, args.section)
    papiObject = PapiWrapper(access_hostname, args.account_key)

    #Check for existence of file
    try:
        with open(os.path.join(args.fromFile),'r') as rulesFileHandler:
            pass
    except FileNotFoundError:
        root_logger.info('\nEntered filename does not exist. Ensure file is present in samplerules directory.')
        exit()

    if args.command == 'addRule':
        if not args.insertAfter and not args.insertBefore and not args.insertLast:
            root_logger.info('Specify where to add the rule to using -insertAfter or -insertBefore or -insertLast.\n')
            exit()

        if args.insertAfter or args.insertBefore:
            if not args.ruleName:
                root_logger.info('\nPlease enter the rule name using -ruleName.\n')
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

    if args.command == 'replaceRule':
        whereTo = 'replace'
        if not args.ruleName:
            root_logger.info('\nPlease enter the rule name to be replaced using -ruleName.\n')
            exit()

    version = args.fromVersion
    
    #Find the property details (IDs)
    propertyResponse = papiObject.searchProperty(session,propertyName=args.property)
    if propertyResponse.status_code == 200:
        try:
            propertyDetails = propertyResponse.json()['versions']['items'][0]
        except:
            root_logger.info('Property details were not found. Double check property name\n')
            exit()                
    else:
       root_logger.info('Property details were not found. Double check property name\n') 

    #Fetch the latest version if need be
    root_logger.info('Fetching version ' + version + ' ...')
    if version.upper() == 'latest'.upper() or version.upper() == 'production'.upper() or version.upper() == 'staging'.upper():
        versionResponse = papiObject.getVersion(session, property_name=args.property, activeOn=version.upper(), propertyId=propertyDetails['propertyId'], contractId=propertyDetails['contractId'], groupId=propertyDetails['groupId'])
        version = versionResponse.json()['versions']['items'][0]['propertyVersion']
        root_logger.info('Latest version is: v' + str(version) + '\n')
    else:
        #Validate the version number entered using -fromVersion
        versionResponse = papiObject.getVersion(session, property_name=args.property, activeOn='LATEST', propertyId=propertyDetails['propertyId'], contractId=propertyDetails['contractId'], groupId=propertyDetails['groupId'])
        latestversion = versionResponse.json()['versions']['items'][0]['propertyVersion']
        if int(version) > int(latestversion):
            root_logger.info('Please check the version number. The highest/latest version is: ' + str(latestversion) + '\n')
            exit()
        else:
            root_logger.info('Found Version...\n')

    #Let us now move towards rules
    #All rules are saved in samplerules folder, filename is configurable
    root_logger.info('Fetching existing property rules...')
    propertyContent = papiObject.getPropertyRulesfromPropertyId(session, propertyDetails['propertyId'], version, propertyDetails['contractId'], propertyDetails['groupId'])
    if propertyContent.status_code == 200:
        completePropertyJson = propertyContent.json()
        with open(os.path.join(args.fromFile),'r') as rulesFileHandler:
            newRuleSet = json.loads(rulesFileHandler.read())

        root_logger.info('\nFound rule file: ' + args.fromFile)


        if args.addVariables and not args.variableFile:
            root_logger.info('\n--variableFile <file with variables list> is needed to add variables \n')
            exit()
        if args.addVariables and args.variableFile:
            with open(args.variableFile,'r') as variablesFileHandler:
                newVariables = json.loads(variablesFileHandler.read())            
            newVariablesList = helper.addVariables(completePropertyJson['rules']['variables'], newVariables)        
            #Replace the variables 
            completePropertyJson['rules']['variables'] = newVariablesList

        updatedCompleteRuleSet = helper.insertRule([completePropertyJson['rules']], newRuleSet, args.ruleName, whereTo)
        #root_logger.info(json.dumps(updatedCompleteRuleSet))
        #Check if we found the matching rule
        if updatedCompleteRuleSet['occurances'] > 0:
            #Check whether we found multiple rule names, if yes warn the user
            if updatedCompleteRuleSet['occurances'] == 1:
                #Overwrite the rules section with updated one
                completePropertyJson['rules'] = updatedCompleteRuleSet['completeRuleSet'][0]
                #Updating the property comments
                if args.command == 'replaceRule':
                    finalComment = completePropertyJson['comments'] = 'Created from v' + str(version) + ': Replaced existing rule "' + args.ruleName + '" with rule from: '+ args.fromFile
                elif comment == 'at the end':
                    finalComment = completePropertyJson['comments'] = 'Created from v' + str(version) + ': Added rule ' + newRuleSet['name'] + ' ' + comment
                else:
                    finalComment = completePropertyJson['comments'] = 'Created from v' + str(version) + ': Added rule ' + newRuleSet['name'] + ' '+ comment + ' ' + args.ruleName + ' rule'

                #Let us now create a version
                root_logger.info('Trying to create a new version of this property based on version ' + str(version))
                versionResponse = papiObject.createVersion(session, baseVersion=version, property_name=args.property)
                if versionResponse.status_code == 201:
                    #Extract the version number
                    matchPattern = re.compile('/papi/v0/properties/prp_.*/versions/(.*)(\?.*)')
                    newVersion = matchPattern.match(versionResponse.json()['versionLink']).group(1)
                    root_logger.info('Successfully created new property version: v' + str(newVersion))
                    #Make a call to update the rules
                    root_logger.info('\nNow trying to upload the new ruleset...')
                    uploadRulesResponse = papiObject.uploadRules(session=session, updatedData=json.loads(json.dumps(completePropertyJson)),\
                     property_name=args.property, version=newVersion, propertyId=propertyDetails['propertyId'], contractId=propertyDetails['contractId'], groupId=propertyDetails['groupId'])
                    if uploadRulesResponse.status_code == 200:
                        root_logger.info('\nSuccess! Comments: "' + finalComment + '"\n')
                    else:
                        root_logger.info('Unable to update rules in property. Reason is: \n\n' + json.dumps(uploadRulesResponse.json(), indent=4))
                        exit()
                else:
                    root_logger.info('Unable to create a new version.')
                    exit()
            else:
                root_logger.info('\nError: Found ' + str(updatedCompleteRuleSet['occurances']) + ' occurrences of the rule: "' + args.ruleName + '"' + '. Please check configuration. Exiting...')
        else:
            root_logger.info('\nUnable to find rule: "' + args.ruleName + '" in this property.')
            root_logger.info('Check the -rulename value or run -getDetail to list existing rules for this property.')
            exit()
    else:
        root_logger.info('Unable to fetch property rules.')
        exit()    

def replaceRule(args):
    addRule(args)

def getDetail(args):
    access_hostname, session = init_config(args.edgerc, args.section)
    papiObject = PapiWrapper(access_hostname, args.account_key)

    #Find the property details (IDs)
    propertyResponse = papiObject.searchProperty(session,propertyName=args.property)
    if propertyResponse.status_code == 200:
        try:
            propertyDetails = propertyResponse.json()['versions']['items'][0]
        except:
            root_logger.info('Property details were not found. Double check property name\n')
            exit()                
    else:
       root_logger.info('Property details were not found. Double check property name\n')    

    root_logger.info('Fetching property versions...\n')
    versionsResponse = papiObject.listVersions(session, property_name=args.property, propertyId=propertyDetails['propertyId'], contractId=propertyDetails['contractId'], groupId=propertyDetails['groupId'])
    if versionsResponse.status_code == 200:
        root_logger.info('Current Property Details:')
        root_logger.info('----------------------------------')
        #root_logger.info(json.dumps(versionsResponse.json(), indent=4))
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
        root_logger.info('Version ' + str(latestVersion) + ' is latest')
        if stagingVersion != 0:
            root_logger.info('Version ' + str(stagingVersion) + ' is live in staging')
        if stagingVersion == 0:
            root_logger.info('No version is active in staging')
        if productionVersion != 0:
            root_logger.info('Version ' + str(productionVersion) + ' is live in production')
        if productionVersion == 0:
            root_logger.info('No version is active in production')
        #root_logger.info('Version ' + str(latestVersion) + ' is the latest version')

        #comment this out for now? root_logger.info('\nLast 10 versions...\n')
        root_logger.info('\nVersion Details (Version : Description)')
        root_logger.info('----------------------------------')

        if args.fromVersion:
            for everyVersionDetail in versionsResponse.json()['versions']['items']:
                if int(everyVersionDetail['propertyVersion']) >= int(args.fromVersion):
                    if 'note' in everyVersionDetail:
                        root_logger.info('v' + str(everyVersionDetail['propertyVersion']) + ' : ' + everyVersionDetail['note'])
                    else:
                        root_logger.info('v' + str(everyVersionDetail['propertyVersion']) + ' : ')
        else:
            for everyVersionDetail in versionsResponse.json()['versions']['items'][:10]:
                if 'note' in everyVersionDetail:
                    root_logger.info('v' + str(everyVersionDetail['propertyVersion']) + ' : ' + everyVersionDetail['note'])
                else:
                    root_logger.info('v' + str(everyVersionDetail['propertyVersion']) + ' : ')
    else:
        root_logger.info('Unable to fetch versions of the property')
        root_logger.info(json.dumps(versionsResponse.json(), indent=4))
        exit()        

def listRules(args):
    access_hostname, session = init_config(args.edgerc, args.section)
    papiObject = PapiWrapper(access_hostname, args.account_key)

    #Find the property details (IDs)
    propertyResponse = papiObject.searchProperty(session,propertyName=args.property)
    if propertyResponse.status_code == 200:
        try:
            propertyDetails = propertyResponse.json()['versions']['items'][0]
        except:
            root_logger.info('Property details were not found. Double check property name\n')
            exit()                
    else:
       root_logger.info('Property details were not found. Double check property name\n') 

    #Fetch the latest version if need be
    root_logger.info('Fetching version ' + args.version + ' ...')
    if args.version.upper() == 'latest'.upper():
        versionResponse = papiObject.getVersion(session, property_name=args.property, activeOn=args.version.upper(), propertyId=propertyDetails['propertyId'], contractId=propertyDetails['contractId'], groupId=propertyDetails['groupId'])
        version = versionResponse.json()['versions']['items'][0]['propertyVersion']
        root_logger.info('Latest version is: v' + str(version) + '\n')
    else:
        version = args.version
        #Validate the version number entered using -version
        versionResponse = papiObject.getVersion(session, property_name=args.property, activeOn='LATEST', propertyId=propertyDetails['propertyId'], contractId=propertyDetails['contractId'], groupId=propertyDetails['groupId'])
        latestversion = versionResponse.json()['versions']['items'][0]['propertyVersion']
        if int(args.version) > int(latestversion):
            root_logger.info('Please check the version number. The highest/latest version is: ' + str(latestversion) + '\n')
            exit()
        else:
            root_logger.info('Found version...\n')

    root_logger.info('Fetching property rules...\n')
    propertyContent = papiObject.getPropertyRulesfromPropertyId(session, propertyDetails['propertyId'], version, propertyDetails['contractId'], propertyDetails['groupId'])
    if propertyContent.status_code == 200:
        rules = helper.getAllRules([propertyContent.json()['rules']], allruleNames=[])
        root_logger.info('Rules are:')
        root_logger.info('---------')
        for eachRuleName in rules:
            root_logger.info(eachRuleName)
    else:
        root_logger.info('Unable to fecth rules of property.')
        exit()

def addBehavior(args):
    access_hostname, session = init_config(args.edgerc, args.section)
    papiObject = PapiWrapper(access_hostname, args.account_key)

    if not args.property:
        root_logger.info('\nPlease enter property name using -property.')
        exit()
    if not args.version:
        root_logger.info('\nPlease enter the version to use/create from using -version.')
        exit()
    if not args.fromFile:
        root_logger.info('\nPlease enter the filename containing rule(s) using -fromFile.')
        exit()
    if not args.comment:
        root_logger.info('\nPlease enter the comment/version notes using -comment.')
        exit()
    if not args.ruleName:
        root_logger.info('\nPlease enter the rule name where behavior needs to be added.\n')
        exit()
    if not args.checkoutNewVersion:
        root_logger.info('\nPlease enter whether to create a new version or use existing version using -checkoutNewVersion YES/NO.\n')
        exit()


    #Check for existence of file
    try:
        with open(os.path.join(args.fromFile),'r') as rulesFileHandler:
            pass
    except FileNotFoundError:
        root_logger.info('\nEntered filename does not exist. Ensure file with behavior details is present')
        exit()

    version = args.version
    
    #Find the property details (IDs)
    propertyResponse = papiObject.searchProperty(session,propertyName=args.property)
    if propertyResponse.status_code == 200:
        try:
            propertyDetails = propertyResponse.json()['versions']['items'][0]
        except:
            root_logger.info('Property details were not found. Double check property name\n')
            exit()                
    else:
       root_logger.info('Property details were not found. Double check property name\n') 


    if args.checkoutNewVersion.upper() == 'YES':
        #Checkout a version based on version number or production or staging or latest version or version number
        if args.version.upper() == 'PRODUCTION' or args.version.upper() == 'STAGING' \
        or args.version.upper() == 'LATEST':
            root_logger.info('Fetching and verifying ' + version + ' version...')
            versionResponse = papiObject.getVersion(session, property_name=args.property, activeOn=version.upper(), propertyId=propertyDetails['propertyId'], contractId=propertyDetails['contractId'], groupId=propertyDetails['groupId'])
            if versionResponse.status_code == 200:
                version = versionResponse.json()['versions']['items'][0]['propertyVersion']
                root_logger.info(args.version + ' version is: v' + str(version) + '\n')
            else:
                root_logger.info('Unable to get version details. There is some issue, contact developer')
                exit()
    else:
        #Validate the version number entered using -version
        versionResponse = papiObject.getVersion(session, property_name=args.property, activeOn='LATEST', propertyId=propertyDetails['propertyId'], contractId=propertyDetails['contractId'], groupId=propertyDetails['groupId'])
        if versionResponse.status_code == 200:
            latestversion = versionResponse.json()['versions']['items'][0]['propertyVersion']
            if int(version) > int(latestversion):
                root_logger.info('Please check the version number. The highest/latest version is: ' + str(latestversion) + '\n')
                exit()
            else:
                root_logger.info('Entered version is valid.\n')
        else:
            root_logger.info('Unable to get version details. There is some issue, contact developer')
            exit()

    #Let us now move towards rules
    #All rules are saved in samplerules folder, filename is configurable
    root_logger.info('Fetching existing property rules...')
    propertyContent = papiObject.getPropertyRulesfromPropertyId(session, propertyDetails['propertyId'], version, propertyDetails['contractId'], propertyDetails['groupId'])
    if propertyContent.status_code == 200:
        completePropertyJson = propertyContent.json()
        with open(os.path.join(args.fromFile),'r') as rulesFileHandler:
            behavior = json.loads(rulesFileHandler.read())

        root_logger.info('\nFound rule file: ' + args.fromFile)

        updatedCompleteRuleSet = helper.addBehaviorToRule([completePropertyJson['rules']], behavior, args.ruleName)

        completePropertyJson['rules'] = updatedCompleteRuleSet[0]

        #Updating the property comments
        finalComment = completePropertyJson['comments'] = args.comment

        if args.checkoutNewVersion.upper() == 'YES':
            #Let us now create a version
            root_logger.info('Trying to create a new version of this property based on version ' + str(version))
            versionResponse = papiObject.createVersion(session, baseVersion=version, property_name=args.property)
            if versionResponse.status_code == 201:
                #Extract the version number
                matchPattern = re.compile('/papi/v0/properties/prp_.*/versions/(.*)(\?.*)')
                newVersion = matchPattern.match(versionResponse.json()['versionLink']).group(1)
                root_logger.info('Successfully created new property version: v' + str(newVersion))
                #Make a call to update the rules
                root_logger.info('\nNow trying to upload the new ruleset...')
                uploadRulesResponse = papiObject.uploadRules(session=session, updatedData=json.loads(json.dumps(completePropertyJson)),\
                 property_name=args.property, version=newVersion, propertyId=propertyDetails['propertyId'], contractId=propertyDetails['contractId'], groupId=propertyDetails['groupId'])
                if uploadRulesResponse.status_code == 200:
                    root_logger.info('\nSuccess! \n')
                else:
                    root_logger.info('Unable to update rules in property. Reason is: \n\n' + json.dumps(uploadRulesResponse.json(), indent=4))
                    exit()
            else:
                root_logger.info('Unable to create a new version.')
                exit()
        else:
            #No Need to create a new version
            #Make a call to update the rules
            root_logger.info('\nNow trying to upload the new ruleset to version : ' + str(version))
            uploadRulesResponse = papiObject.uploadRules(session=session, updatedData=json.loads(json.dumps(completePropertyJson)),\
             property_name=args.property, version=version, propertyId=propertyDetails['propertyId'], contractId=propertyDetails['contractId'], groupId=propertyDetails['groupId'])
            if uploadRulesResponse.status_code == 200:
                root_logger.info('\nSuccess! \n')
            else:
                root_logger.info('Unable to update rules in property. Reason is: \n\n' + json.dumps(uploadRulesResponse.json(), indent=4))
                exit()
    else:
        root_logger.info('Unable to fetch property rules.')
        print(json.dumps(propertyContent.json(), indent=4))
        exit()    

def deleteBehavior(args):
    access_hostname, session = init_config(args.edgerc, args.section)
    papiObject = PapiWrapper(access_hostname, args.account_key)

    #Find the property details (IDs)
    propertyResponse = papiObject.searchProperty(session,propertyName=args.property)
    if propertyResponse.status_code == 200:
        try:
            propertyDetails = propertyResponse.json()['versions']['items'][0]
        except:
            root_logger.info('Property details were not found. Double check property name\n')
            exit()                
    else:
       root_logger.info('Property details were not found. Double check property name\n') 

    #Make a call to update the rules
    versionResponse = papiObject.getVersion(session, property_name=args.property, activeOn='LATEST', propertyId=propertyDetails['propertyId'], contractId=propertyDetails['contractId'], groupId=propertyDetails['groupId'])
    #print(json.dumps(versionResponse.json(), indent=4))
    latestversion = versionResponse.json()['versions']['items'][0]['propertyVersion']

    #Fetch the latest version if need be
    root_logger.info('Fetching version ' + args.version + ' ...')
    if args.version.upper() == 'latest'.upper():
        versionResponse = papiObject.getVersion(session, property_name=args.property, activeOn=args.version.upper(), propertyId=propertyDetails['propertyId'], contractId=propertyDetails['contractId'], groupId=propertyDetails['groupId'])
        version = versionResponse.json()['versions']['items'][0]['propertyVersion']
        root_logger.info('Latest version is: v' + str(version) + '\n')
    else:
        version = args.version
        #Validate the version number entered using -version
        versionResponse = papiObject.getVersion(session, property_name=args.property, activeOn='LATEST', propertyId=propertyDetails['propertyId'], contractId=propertyDetails['contractId'], groupId=propertyDetails['groupId'])
        latestversion = versionResponse.json()['versions']['items'][0]['propertyVersion']
        if int(args.version) > int(latestversion):
            root_logger.info('Please check the version number. The highest/latest version is: ' + str(latestversion) + '\n')
            exit()
        else:
            root_logger.info('Found version...\n')

    root_logger.info('Fetching property rules...\n')
    propertyContent = papiObject.getPropertyRulesfromPropertyId(session, propertyDetails['propertyId'], version, propertyDetails['contractId'], propertyDetails['groupId'])
    
    behavior = {}
    behavior['name'] = args.behaviorName


    if propertyContent.status_code == 200:
        rules = helper.deleteBehavior([propertyContent.json()['rules']], behavior)

        #Let us now create a version
        root_logger.info('Trying to create a new version of this property based on version ' + str(version))
        versionResponse = papiObject.createVersion(session, baseVersion=version, property_name=args.property)
        if versionResponse.status_code == 201:
            #Extract the version number
            matchPattern = re.compile('/papi/v0/properties/prp_.*/versions/(.*)(\?.*)')
            newVersion = matchPattern.match(versionResponse.json()['versionLink']).group(1)
            root_logger.info('Successfully created new property version: v' + str(newVersion))

            #Make a call to update the rules
            root_logger.info('\nNow trying to upload the new ruleset...')
            ruleData = {}
            ruleData['rules'] = rules[0]
            ruleData['comments'] = 'Created from v' + str(version) + '. Removing ' + args.behaviorName
            uploadRulesResponse = papiObject.uploadRules(session=session, updatedData=json.loads(json.dumps(ruleData)),\
             property_name=args.property, version=newVersion, propertyId=propertyDetails['propertyId'], contractId=propertyDetails['contractId'], groupId=propertyDetails['groupId'])
            if uploadRulesResponse.status_code == 200:
                root_logger.info('\nSuccess!n')
            else:
                root_logger.info('Unable to update rules in property. Reason is: \n\n' + json.dumps(uploadRulesResponse.json(), indent=4))
                exit()

def deleteRule(args):
    access_hostname, session = init_config(args.edgerc, args.section)
    papiObject = PapiWrapper(access_hostname, args.account_key)

    if not args.property:
        root_logger.info('\nPlease enter property name using -property.')
        exit()
    if not args.version:
        root_logger.info('\nPlease enter the version to use/create from using -version.')
        exit()
    if not args.comment:
        root_logger.info('\nPlease enter the comment/version notes using -comment.')
        exit()
    if not args.ruleName:
        root_logger.info('\nPlease enter the rule name where behavior needs to be added.\n')
        exit()
    if not args.checkoutNewVersion:
        root_logger.info('\nPlease enter whether to create a new version or use existing version using -checkoutNewVersion YES/NO.\n')
        exit()

    version = args.version
    
    #Find the property details (IDs)
    propertyResponse = papiObject.searchProperty(session,propertyName=args.property)
    if propertyResponse.status_code == 200:
        try:
            propertyDetails = propertyResponse.json()['versions']['items'][0]
        except:
            root_logger.info('Property details were not found. Double check property name\n')
            exit()                
    else:
       root_logger.info('Property details were not found. Double check property name\n') 


    if args.checkoutNewVersion.upper() == 'YES':
        #Checkout a version based on version number or production or staging or latest version or version number
        if args.version.upper() == 'PRODUCTION' or args.version.upper() == 'STAGING' \
        or args.version.upper() == 'LATEST':
            root_logger.info('Fetching and verifying ' + version + ' version...')
            versionResponse = papiObject.getVersion(session, property_name=args.property, activeOn=version.upper(), propertyId=propertyDetails['propertyId'], contractId=propertyDetails['contractId'], groupId=propertyDetails['groupId'])
            if versionResponse.status_code == 200:
                version = versionResponse.json()['versions']['items'][0]['propertyVersion']
                root_logger.info(args.version + ' version is: v' + str(version) + '\n')
            else:
                root_logger.info('Unable to get version details. There is some issue, contact developer')
                exit()
    else:
        #Validate the version number entered using -version
        versionResponse = papiObject.getVersion(session, property_name=args.property, activeOn='LATEST', propertyId=propertyDetails['propertyId'], contractId=propertyDetails['contractId'], groupId=propertyDetails['groupId'])
        if versionResponse.status_code == 200:
            latestversion = versionResponse.json()['versions']['items'][0]['propertyVersion']
            if int(version) > int(latestversion):
                root_logger.info('Please check the version number. The highest/latest version is: ' + str(latestversion) + '\n')
                exit()
            else:
                root_logger.info('Entered version is valid.\n')
        else:
            root_logger.info('Unable to get version details. There is some issue, contact developer')
            exit()

    #Let us now move towards rules
    #All rules are saved in samplerules folder, filename is configurable
    root_logger.info('Fetching existing property rules...')
    propertyContent = papiObject.getPropertyRulesfromPropertyId(session, propertyDetails['propertyId'], version, propertyDetails['contractId'], propertyDetails['groupId'])
    if propertyContent.status_code == 200:
        completePropertyJson = propertyContent.json()

        root_logger.info('Trying to delete the rule: ' + str(args.ruleName))
        updatedCompleteRuleSet = helper.deleteRules([completePropertyJson['rules']], args.ruleName)

        completePropertyJson['rules'] = updatedCompleteRuleSet[0]
        #Updating the property comments
        finalComment = completePropertyJson['comments'] = args.comment

        if args.checkoutNewVersion.upper() == 'YES':
            #Let us now create a version
            root_logger.info('Trying to create a new version of this property based on version ' + str(version))
            versionResponse = papiObject.createVersion(session, baseVersion=version, property_name=args.property)
            if versionResponse.status_code == 201:
                #Extract the version number
                matchPattern = re.compile('/papi/v0/properties/prp_.*/versions/(.*)(\?.*)')
                newVersion = matchPattern.match(versionResponse.json()['versionLink']).group(1)
                root_logger.info('Successfully created new property version: v' + str(newVersion))
                #Make a call to update the rules
                root_logger.info('\nNow trying to upload the new ruleset...')
                uploadRulesResponse = papiObject.uploadRules(session=session, updatedData=json.loads(json.dumps(completePropertyJson)),\
                 property_name=args.property, version=newVersion, propertyId=propertyDetails['propertyId'], contractId=propertyDetails['contractId'], groupId=propertyDetails['groupId'])
                if uploadRulesResponse.status_code == 200:
                    root_logger.info('\nSuccess! \n')
                else:
                    root_logger.info('Unable to update rules in property. Reason is: \n\n' + json.dumps(uploadRulesResponse.json(), indent=4))
                    exit()
            else:
                root_logger.info('Unable to create a new version.')
                exit()
        else:
            #No Need to create a new version
            #Make a call to update the rules
            root_logger.info('\nNow trying to upload the new ruleset to version : ' + str(version))
            uploadRulesResponse = papiObject.uploadRules(session=session, updatedData=json.loads(json.dumps(completePropertyJson)),\
             property_name=args.property, version=version, propertyId=propertyDetails['propertyId'], contractId=propertyDetails['contractId'], groupId=propertyDetails['groupId'])
            if uploadRulesResponse.status_code == 200:
                root_logger.info('\nSuccess! \n')
            else:
                root_logger.info('Unable to update rules in property. Reason is: \n\n' + json.dumps(uploadRulesResponse.json(), indent=4))
                exit()
    else:
        root_logger.info('Unable to fetch property rules.')
        print(json.dumps(propertyContent.json(), indent=4))
        exit()    

def get_prog_name():
    prog = os.path.basename(sys.argv[0])
    if os.getenv("AKAMAI_CLI"):
        prog = "akamai ruleupdater"
    return prog


def get_cache_dir():
    if os.getenv("AKAMAI_CLI_CACHE_DIR"):
        return os.getenv("AKAMAI_CLI_CACHE_DIR")

    return os.curdir

# Final or common Successful exit
if __name__ == '__main__':
    try:
        status = cli()
        exit(status)
    except KeyboardInterrupt:
        exit(1) 