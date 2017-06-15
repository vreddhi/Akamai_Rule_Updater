'''
// Good luck with this code. This leverages akamai OPEN API.
// In case you need
// explanation contact the initiators.
Initiators: vbhat@akamai.com and aetsai@akamai.com
'''

import os
import json

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
                    else:
                        #The options value was not found, so move on
                        pass
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
            if os.stat(propertyFile).st_size != 0:
                with open(propertyFile,'r') as propertiesFileHandler:
                    propertiesContent = json.loads(propertiesFileHandler.read())
                    for everyProperty in propertiesContent:
                        #Some property names have .xml as suffix
                        if everyProperty['propertyName'].upper() == PropertyName.upper() or everyProperty['propertyName'].upper() == PropertyName + '.xml'.upper():
                            return everyProperty
                        else:
                            pass
    #Default return of empty dict
    return {}

def getRule(parentRule,ruleName):
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
    ruleContent = {}
    for eachRule in parentRule:
        if eachRule['name'] == ruleName:
            return eachRule
        else:
            #Check whether we have child rules, where in again behavior might be found
            if len(eachRule['children']) != 0:
                ruleContent = getRule(eachRule['children'],ruleName)

    #Default return of empty dict
    return ruleContent
