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
parser.add_argument("-jsonToConfig",help="Convert Json file to config file",action="store_true")
parser.add_argument("-configToJson",help="Convert config file to Json file",action="store_true")
parser.add_argument("-inputFile",help="Name of input file in samplerules directory")
parser.add_argument("-outputFile",help="Name of config file to be stored in samplerules directory")

parser.add_argument("-debug",help="DEBUG mode to generate additional logs for troubleshooting",action="store_true")

args = parser.parse_args()

if not args.jsonToConfig and not args.inputFile and not args.outputFile and not args.configToJson:
    rootLogger.info("Use -h for help options")
    exit()

if args.jsonToConfig:
    if not args.inputFile:
        rootLogger.info('Enter the input file using -inputFile.')
        exit()

    if not args.outputFile:
        rootLogger.info('Enter the output file using -inputFile.')
        exit()

    with open(os.path.join('samplerules',args.inputFile),'r') as fileContentHandler:
        fileJson = fileContentHandler.read()
        JsonRepresentation = json.loads(fileJson)
    completeRuleSet = JsonRepresentation['rules']
    outputFilename = os.path.join('samplerules',args.outputFile)
    with open(outputFilename,'w') as textFileHandler:
        helper.JsonRulesToPlainText([JsonRepresentation['rules']],outputFilename)

if args.configToJson:
    if not args.inputFile:
        rootLogger.info('Enter the input file using -inputFile.')
        exit()

    if not args.outputFile:
        rootLogger.info('Enter the output file using -inputFile.')
        exit()

    outputFilename = os.path.join('samplerules',args.outputFile)
    inputFilename = os.path.join('samplerules',args.inputFile)
    with open(outputFilename,'w') as textFileHandler:
        helper.ConfigToJsonConverter(inputFilename,outputFilename)
