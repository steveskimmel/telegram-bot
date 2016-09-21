from telegramAPI import get,post,keyb,keybHide
from resource import resource
import json
import sys
import psycopg2
import os
import urlparse
from os.path import exists
from os import makedirs

def postit(Resource): #function which sends the first resource management question

    #################################Setup Heroku Postgres#################################
    url = urlparse.urlparse(os.environ.get('DATABASE_URL'))
    db = "dbname=%s user=%s password=%s host=%s " % (url.path[1:], url.username, url.password, url.hostname)
    schema = "schema.sql"
    con = psycopg2.connect(db)
    cur = con.cursor()
    #######################################################################################

    ####################Prepare for fast sending of messages to Resources##################

    for element in Resource: #loop through all resources in RAM to handle
        if element.approved and not (element.service_line == None or element.service_line == ''):
            cur.execute("UPDATE salesforce.resource__c SET Bot_State__c = '1' WHERE telegram_user_id__c = '%s' AND SchedularBotAccess__c = 'Approved'" % (element.user_id)) #set awaiting schedule response to true for resource in Salesforce
            con.commit()
            element.state = 1
    #######################################################################################

    ########################Fast sending of messages to all resources######################
    for element in Resource: #loop through all resources in RAM
        if element.approved and not (element.service_line == None or element.service_line == ''): #if a resource is approved and has responded with their service line
            print 'polling ' + str(element.name)
            keybHide(element.user_id,"Hey! It's that time of the week again! Lets update your schedule:")
            if element.on_project == True: #if user is on a project
                keyb(element.user_id, "Are you still on %s?" % (element.engagement_name),[["Yes"],["No"]])
            else:
                keyb(element.user_id, "Are you on a billable project?",[["Yes"],["No"]])
    #######################################################################################
    con.close()
