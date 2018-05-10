'''
// Good luck with this code. This leverages akamai OPEN API.
// In case you need
// explanation contact the initiators.
Initiators: vbhat@akamai.com and aetsai@akamai.com
'''

import os
import json
import configparser
import re

#-----------------------------------------------------------#
#-----Below section contains custom parsing functions-------#
#-----------------------------------------------------------#

def getChildRulesandUpdate(parentRule,behavior):
    """
    Function to fetch all childrules of given parentRule

    Parameters
    ----------
    parentRule : <List>
        Default parent rule represented as a list

    behavior: <Dictionary>
        Details of behavior to be updated

    Returns
    -------
    parentRule : Updated Rule tree
    """
    for eachRule in parentRule:
        for eachbehavior in eachRule['behaviors']:
            if eachbehavior['name'] == behavior['name']:
                for option in eachbehavior['options']:
                    if option in behavior['options']:
                        eachbehavior['options'][option] = behavior['options'][option]
                    if 'customCertificates' in behavior['options']:
                        del behavior['options']['customCertificates']
                    else:
                        #The options value was not found, so move on
                        pass
                #Update the behavior
                for option in behavior['options']:
                    eachbehavior['options'][option] = behavior['options'][option]
            else:
                #The behavior is not being updated, so move on
                pass
        #Check whether we have child rules, where in again behavior might be found
        if len(eachRule['children']) != 0:
            getChildRulesandUpdate(eachRule['children'],behavior)

    #Awesome, we are done updating behaviors, lets go back
    return parentRule

def addBehaviorToRule(parentRule,behavior,ruleName):
    """
    Function to fetch all childrules of given parentRule

    Parameters
    ----------
    parentRule : <List>
        Default parent rule represented as a list

    behavior: <Dictionary>
        Details of behavior to be updated

    Returns
    -------
    parentRule : Updated Rule tree
    """
    for eachRule in parentRule:
        if eachRule['name'] == ruleName:
            eachRule['behaviors'].append(behavior)
        #Check whether we have child rules, where in again behavior might be found
        if len(eachRule['children']) != 0:
            getChildRulesandUpdate(eachRule['children'],behavior)

    #Awesome, we are done updating behaviors, lets go back
    return parentRule

def deleteBehavior(parentRule,behavior):
    """
    Function to fetch all childrules of given parentRule

    Parameters
    ----------
    parentRule : <List>
        Default parent rule represented as a list

    behavior: <Dictionary>
        Details of behavior to be updated

    Returns
    -------
    parentRule : Updated Rule tree
    """
    for eachRule in parentRule:
        for eachbehavior in eachRule['behaviors']:
            if eachbehavior['name'] == behavior['name']:
                #Delete the behavior
                del eachbehavior
            else:
                #The behavior is not being updated, so move on
                pass
        #Check whether we have child rules, where in again behavior might be found
        if len(eachRule['children']) != 0:
            getChildRulesandUpdate(eachRule['children'],behavior)

    #Awesome, we are done updating behaviors, lets go back
    return parentRule

def getPropertyDetailsFromLocalStore(PropertyName):
    """
    Function to fetch property details from local store

    Parameters
    ----------
    PropertyName : <String>
        propertyname to find details of

    Returns
    -------
    property: <dict>
        Dictionary of property details or an empty dict if not found
    """
    for eachItem in os.listdir(os.path.join('setup','contracts')):
        if os.path.isdir(os.path.join('setup','contracts',eachItem)):
            propertyFile = os.path.join('setup','contracts',eachItem,'properties.json')
            #Empty file results in JSON read error. so check it
            try:
                if os.stat(propertyFile).st_size != 0:
                    with open(propertyFile,'r') as propertiesFileHandler:
                        propertiesContent = json.loads(propertiesFileHandler.read())
                        for everyProperty in propertiesContent:
                            #Some property names have .xml as suffix
                            if everyProperty['propertyName'].upper() == PropertyName.upper() or everyProperty['propertyName'].upper() == PropertyName + '.xml'.upper():
                                return everyProperty
                            else:
                                pass
            except FileNotFoundError:
                pass                    

    #Default return of empty dict
    return {}

def getAllRules(parentRule,allruleNames=[],isChild='optional',parentRuleName='optional'):
    """
    Function to fetch json content of rule

    Parameters
    ----------
    parentRule : <List>
        Default parent rule represented as a list

    ruleName: <String>
        Name of the rule

    Returns
    -------
    rule : Json representation of a rule
    """
    #Initialize ruleContent only if its empty
    if not len(allruleNames):
        allruleNames = []
    for eachRule in parentRule:
        if isChild != 'optional' and parentRuleName != 'default':
            allruleNames.append(' ' + parentRuleName + '  -->  ' + eachRule['name'])
        else:
            allruleNames.append('\n ' + eachRule['name'])
        #Check whether we have child rules, where in again behavior might be found
        if len(eachRule['children']) != 0:
            allruleNames = getAllRules(eachRule['children'], allruleNames, isChild='yes',parentRuleName = eachRule['name'])

    #Default return of empty dict
    return allruleNames

ruleCount = 0
def getRule(parentRule,ruleName,ruleContent={}):
    """
    Function to fetch json content of rule

    Parameters
    ----------
    parentRule : <List>
        Default parent rule represented as a list

    ruleName: <String>
        Name of the rule

    Returns
    -------
    rule : Json representation of a rule
    """
    #Initialize ruleContent only if its empty
    global ruleCount
    for eachRule in parentRule:
        if eachRule['name'].upper() == ruleName.upper():
            ruleCount += 1
            ruleContent = eachRule
        #Check whether we have child rules, where in again behavior might be found
        if len(eachRule['children']) != 0:
            ruleContent = getRule(eachRule['children'],ruleName, ruleContent)['ruleContent']
    #Default return of empty dict
    return { 'ruleContent': ruleContent, 'ruleCount': ruleCount }

occurances = 0
def insertRule(completeRuleSet,newRuleSet,ruleName='default',whereTo='insertAfter'):
    """
    Function to fetch json content of rule

    Parameters
    ----------
    parentRule : <List>
        Default parent rule represented as a list

    ruleName: <String>
        Name of the rule

    Returns
    -------
    rule : Json representation of a rule
    """
    #global variable to preserve count across recursive calls
    global occurances
    if ruleName == 'default':
        for everyRule in completeRuleSet:
            everyRule['children'].append(newRuleSet)
        occurances += 1
    else:
        positionsList = []
        for index, eachRule in enumerate(completeRuleSet):
            if eachRule['name'] == ruleName:
                if whereTo == 'insertAfter':
                    position = index + 1
                elif whereTo == 'insertBefore':
                    position = index - 1 if index > 0 else 0
                elif whereTo == 'replace':
                    position = index
                #Append the position/index. This is needed to handle multipl
                #rules with same name.
                positionsList.append(position)
                occurances += 1
            else:
                #Check whether we have child rules, where in name can be found
                if len(eachRule['children']) != 0:
                    insertRule(eachRule['children'],newRuleSet,ruleName,whereTo)

        #Recursion is fun. This code executes in reverse order from stack
        #This is the place where rule insertion happens
        if whereTo != 'replace':
            for everyPosition in positionsList:
                completeRuleSet.insert(everyPosition,newRuleSet)
        else:
            for everyPosition in positionsList:
                completeRuleSet[everyPosition] = newRuleSet

    return { 'completeRuleSet' : completeRuleSet, 'occurances' : occurances }

def JsonRulesToPlainText(completeRuleSet,fileName):
    """
    Function to fetch json content of rule

    Parameters
    ----------
    parentRule : <List>
        Default parent rule represented as a list

    ruleName: <String>
        Name of the rule

    Returns
    -------
    rule : Json representation of a rule
    """
    for eachRule in completeRuleSet:
        print('\n[Rule-' +eachRule['name'] + ']')
        with open(fileName,'a') as fileContentHandler:
            fileContentHandler.write('\n[Rule-' +eachRule['name'] + ']\n')
        if 'criteria' in eachRule:
            criteriasList = []
            criteriasOptionsList = []
            for eachCriteria in eachRule['criteria']:
                criteriasList.append(str(eachCriteria['name']))
            print('criterias = '+ str(criteriasList))
            with open(fileName,'a') as fileContentHandler:
                fileContentHandler.write('criterias = '+ str(criteriasList)+'\n')
            for eachCriteria in eachRule['criteria']:
                if 'options' in eachCriteria:
                    for eachOption in eachCriteria['options']:
                        print('criteria.' + eachCriteria['name'] + '.' + eachOption + ' = ' + str(eachCriteria['options'][eachOption]))
                        with open(fileName,'a') as fileContentHandler:
                            fileContentHandler.write('criteria.' + eachCriteria['name'] + '.' + eachOption + ' = ' + str(eachCriteria['options'][eachOption]) + '\n')
        if 'behaviors' in eachRule:
            behaviorsList = []
            behaviorsOptionsList = []
            for eachbehavior in eachRule['behaviors']:
                behaviorsList.append(eachbehavior['name'])
            print('behaviors = '+ str(behaviorsList))
            with open(fileName,'a') as fileContentHandler:
                fileContentHandler.write('behaviors = '+ str(behaviorsList) + '\n')
            for eachbehavior in eachRule['behaviors']:
                if 'options' in eachbehavior:
                    for eachOption in eachbehavior['options']:
                        print('behavior.' + eachbehavior['name'] + '.' + eachOption + ' = ' + str(eachbehavior['options'][eachOption]))
                        with open(fileName,'a') as fileContentHandler:
                            fileContentHandler.write('behavior.' + eachbehavior['name'] + '.' + eachOption + ' = ' + str(eachbehavior['options'][eachOption]) + '\n')

        #Check whether we have child rules, where in name can be found
        if len(eachRule['children']) != 0:
            childRuleList = []
            for eachChildRule in eachRule['children']:
                childRuleList.append(eachChildRule['name'])
            print('childRules = ' + str(childRuleList))
            with open(fileName,'a') as fileContentHandler:
                fileContentHandler.write('childRules = ' + str(childRuleList) + '\n')
            JsonRulesToPlainText(eachRule['children'],fileName)
        else:
            pass


def behaviorsToJson(config, ruleName):
    behaviorPattern = re.compile('behavior\.(.*)')
    if 'behaviors' in config.options(ruleName):
        behaviors = config[ruleName]['behaviors'].replace('[','').replace(']','').replace("'",'').replace(",",'').split()
        print(behaviors)
        rulebehaviorList = []
        behaviorOptionNames = list(filter(lambda x: behaviorPattern.match(x), config.options(ruleName)))
        for eachBehavior in behaviors:
            behaviorDetails = {}
            behaviorDetails['options'] = {}
            behaviorDetails['name'] = eachBehavior
            pattern = re.compile(eachBehavior)
            behaviorOptions = list(filter(lambda x: eachBehavior in x , behaviorOptionNames))
            print(eachBehavior +  ' : ' + str(behaviorOptions) + '\n\n')
            for eachOptionOfBehavior in behaviorOptions:
                behaviorDetails['options'][eachOptionOfBehavior.split('.')[2]] = config[ruleName][eachOptionOfBehavior]
            rulebehaviorList.append(behaviorDetails)

outputRule = {}
def ConfigToJsonConverter(inputFilename,outputFilename,ruleName):
    """
    Function to convert configfile to json content

    Parameters
    ----------


    Returns
    -------
    rule : Json representation of a rule
    """

    global outputRule
    config = configparser.ConfigParser()
    #Make the parser case-sensitive
    config.optionxform = str
    config.read(inputFilename)
    ruleNames = config.sections()

    #Lets start with defult rule
    behaviorPattern = re.compile('behavior\.(.*)')
    singleRule = {}
    singleRule['children'] = []
    singleRule['behaviors'] = []
    ruleName = 'Rule-' + ruleName
    if config.has_section(ruleName):
        singleRule['name'] = ruleName
        outputRule['name'] = ruleName
        isParent = {}
        isParent[ruleName] = {}
        isParent[ruleName]['children'] = []
        if 'children' not in singleRule:
            singleRule['children'] = []
        if 'childRules' in config.options(ruleName):
            isParent['name'] = ruleName
            children = config[ruleName]['childRules'].replace('[','').replace(']','').replace("'",'').split(',')
            if len(children) > 0:
                for eachChildRuleName in children:
                    childRuleName = eachChildRuleName.strip()
                    print(childRuleName)
                    ruleData = singleRule['children'].append(ConfigToJsonConverter(inputFilename, outputFilename, childRuleName))
                    print(json.dumps(singleRule, indent=4))
        if 'behaviors' in config.options(ruleName):
            behaviors = config[ruleName]['behaviors'].replace('[','').replace(']','').replace("'",'').split(',')
            #print(behaviors)
            rulebehaviorList = []
            behaviorOptionNames = list(filter(lambda x: behaviorPattern.match(x), config.options(ruleName)))
            #print(behaviorOptionNames)
            for eachBehavior in behaviors:
                behaviorDetails = {}
                behaviorDetails['options'] = {}
                behaviorDetails['name'] = eachBehavior
                behaviorOptions = list(filter(lambda x: eachBehavior.strip().lower() in x.strip().lower() , behaviorOptionNames))
                #print(str(eachBehavior) + ' : '+ str(behaviorOptionNames) + '\n')
                #print(str(behaviorOptions) + '\n\n')
                #print(eachBehavior +  ' : ' + str(behaviorOptions) + '\n\n')
                for eachOptionOfBehavior in behaviorOptions:
                    optionValue = config[ruleName][eachOptionOfBehavior]
                    if optionValue.isdigit():
                        optionValue = int(optionValue)
                    elif optionValue.lower() == 'true':
                        optionValue = bool(True)
                    elif optionValue.lower() == 'false':
                        optionValue = bool(False)
                    behaviorDetails['options'][eachOptionOfBehavior.split('.')[2]] = optionValue
                rulebehaviorList.append(behaviorDetails)
            singleRule['behaviors'] = rulebehaviorList
        #print(json.dumps(singleRule, indent=4))

        return outputRule

    else:
        print( ruleName + ' is not found. cant proceed to convert')
        exit()
