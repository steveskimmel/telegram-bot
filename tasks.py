################EXTERNAL LIBRARY IMPORTS################
from celery import Celery
import requests
from telegramAPI import get,post,keyb,keybHide
import apiai
import json
from resource import resource
from posting import postit
import schedule
import time
import signal
import sys
import psycopg2
import os
import urlparse
from os.path import exists
from os import makedirs
from Util import getUniqueElementValueFromXmlString
from salesforceAPI import describeObject
########################################################

##############Defining a celery worker app##############
app = Celery()
app.config_from_object("celery_settings")
########################################################

##############Safely handling dyno restarts#############
def handler(signum, frame):
    sys.exit(1)
########################################################

##############Defining a celery worker task#############
@app.task
def botprogram():
    ############Defining date variables to handle capturing the project roll off date user experience###############
    day_31 = [['1'],['2'],['3'],['4'],['5'],['6'],['7'],['8'],['9'],['10'],['11'],['12'],['13'],['14'],['15'],['16'],['17'],['18'],['19'],['20'],['21'],['22'],['23'],['24'],['25'],['26'],['27'],['28'],['29'],['30'],['31']]
    day_30 = [['1'],['2'],['3'],['4'],['5'],['6'],['7'],['8'],['9'],['10'],['11'],['12'],['13'],['14'],['15'],['16'],['17'],['18'],['19'],['20'],['21'],['22'],['23'],['24'],['25'],['26'],['27'],['28'],['29'],['30']]
    day_28 = [['1'],['2'],['3'],['4'],['5'],['6'],['7'],['8'],['9'],['10'],['11'],['12'],['13'],['14'],['15'],['16'],['17'],['18'],['19'],['20'],['21'],['22'],['23'],['24'],['25'],['26'],['27'],['28']]
    month = [['January'],['February'],['March'],['April'],['May'],['June'],['July'],['August'],['September'],['October'],['November'],['December']]
    year = [['2016'],['2017'],['2018'],['2019'],['2020']]
    ################################################################################################################
    #################################Dynamically assigning resource service lines###################################
    sf_version = '32.0'
    sf_instance = ""
    headers = ""
    soap_url = 'https://login.salesforce.com/services/Soap/u/32.0'
    sf_version = 32.0
    session_id = ""
    service_lines = []

    login_soap_request_body = """<?xml version="1.0" encoding="utf-8" ?>
    <env:Envelope
            xmlns:xsd="http://www.w3.org/2001/XMLSchema"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            xmlns:env="http://schemas.xmlsoap.org/soap/envelope/">
        <env:Body>
            <n1:login xmlns:n1="urn:partner.soap.sforce.com">
                <n1:username>{username}</n1:username>
                <n1:password>{password}{token}</n1:password>
            </n1:login>
        </env:Body>
    </env:Envelope>""".format(username='', password='', token='')

    login_soap_request_headers = {
        'content-type': 'text/xml',
        'charset': 'UTF-8',
        'SOAPAction': 'login'}

    response = requests.post(soap_url,
                             login_soap_request_body,
                             headers=login_soap_request_headers)

    if response.status_code<300:
        session_id = getUniqueElementValueFromXmlString(response.content, 'sessionId')
        server_url = getUniqueElementValueFromXmlString(response.content, 'serverUrl')

        sf_instance = (server_url
                                     .replace('http://', '')
                                     .replace('https://', '')
                                     .split('/')[0]
                                     .replace('-api', ''))

        sf_headers = {'Content-Type': 'application/json',
                                 'Authorization': 'Bearer ' + session_id,
                                 'X-PrettyPrint': '1'}

    for element in describeObject (sf_instance,sf_headers)["fields"]:
        if str(element["label"]) == 'Service Line':
            for picklist_values in element["picklistValues"]:
                if "-" in picklist_values["label"]:
                    service_lines.append([str(picklist_values["label"])])

    ##################################################################################################################

    telegram_result = "" #Empty variable for storing a received telegram message
    Resource = [] #Array to store all resource objects which are instantiated
    index = -1 #Variable to represent the index value of the resource within the Resource array
    offset = 0 #Variable to store the index value of the received message

    #######################API.AI setup#########################
    Resource_ACCESS_TOKEN = 'd15e157632014d57951ff2ec164ed4f1'
    ai = apiai.ApiAI(Resource_ACCESS_TOKEN)
    ############################################################

    #######################Heroku Postgres setup#########################
    url = urlparse.urlparse(os.environ.get('DATABASE_URL'))
    db = "dbname=%s user=%s password=%s host=%s " % (url.path[1:], url.username, url.password, url.hostname)
    schema = "schema.sql"
    con = psycopg2.connect(db)
    cur = con.cursor()

    ##################Assigning Deloitte Teams to Engagments###########################
    cur.execute("SELECT sfid, DeloitteTeamsInvolved__c from salesforce.opportunity")
    Opportunity_Objects = cur.fetchall()

    Global_Engagement_Names = []
    Engagement_Objects = []
    cur.execute("SELECT name, sfid, project_status__c, opportunity__c FROM salesforce.engagement__c WHERE project_status__c = 'In Progress'")
    Engagements = cur.fetchall()
    for engagement in Engagements:
        Global_Engagement_Names.append(engagement[0])
        for opportunity in Opportunity_Objects:
            if engagement[3] == opportunity[0]:
                Engagement_Objects.append([engagement[0],engagement[1],opportunity[1]]) #[name,sfid,teamsinvolved]

    #####################################################################################

    schedule.every().friday.at("08:00").do(postit,Resource) #Schedule library function to run postit function at friday at 10am (8am GMT). The Resource array is passed as a parameter to the postit function.

    cur.execute("SELECT telegram_user_id__c, name, Bot_State__c,on_project__c,ServiceLine__c, engagement__c, SchedularBotAccess__c FROM salesforce.resource__c WHERE SchedularBotAccess__c = 'Approved'") #Read resource information from Salesforce
    rows = cur.fetchall()
    for row in rows:
        Resource.append(resource(row[0],row[1],int(row[2]),row[3],row[4])) #Instantiating resource objects using the Salesforce data and appending these objects to the Resource array.
        index = len(Resource)-1
        for engagement in Engagement_Objects:
            if row[5] == engagement [1]:
                Resource[index].engagement_name = engagement[0]
        print str('adding ' + row[1] + ' to RAM')

    while True: #'Runtime infinite loop'
        while True: #'Receive message loop'
            cur.execute("SELECT telegram_user_id__c, name, Bot_State__c,on_project__c,ServiceLine__c, engagement__c, SchedularBotAccess__c FROM salesforce.resource__c WHERE SchedularBotAccess__c = 'Approved'") #Read approved resource information from Salesforce
            rows = cur.fetchall()
            for row in rows: #loop through resources from Salesforce
                found = 0
                for element in Resource: #loop through resources in the Resources array (RAM)
                    if str(element.user_id) == str(row[0]): #if resource is in both Salesforce and the Resources array, do nothing.
                        found = 1
                        if element.approved == 0: #if resource was not approved previously
                            element.approved = 1  #approve resource
                            print str (row[1] + ' has been approved on Salesforce')
                            keyb(element.user_id,"Your access to DeloitteScheduleBot has been approved. Please select your service line from the list of options below:",service_lines) #prompting the telegram user to select their service line
                            element.state = 7
                            cur.execute("UPDATE salesforce.resource__c SET Bot_State__c = '%s' WHERE telegram_user_id__c = '%s'" % (str(element.state),element.user_id))
                            con.commit()
                if found == 0: # if the resource was added on Salesforce but has not yet been added to the Resources array, add it to the Resources array.
                    Resource.append(resource(row[0],row[1],int(row[2]),row[3],row[4]))
                    index = len(Resource)-1
                    for engagement in Engagement_Objects:
                        if row[5] == engagement [1]:
                            Resource[index].engagement_name = engagement[0]
                    print str (row[1] + ' has been created and approved on Salesforce')
                    print str('adding ' + row[1] + ' to RAM')
                    keyb(Resource[index].user_id,"Your access to DeloitteScheduleBot has been approved. Please select your service line from the list of options below:",service_lines) #prompting the telegram user to select their service line
                    Resource[index].state = 7
                    cur.execute("UPDATE salesforce.resource__c SET Bot_State__c = '%s' WHERE telegram_user_id__c = '%s'" % (str(Resource[index].state),Resource[index].user_id))
                    con.commit()

            schedule.run_pending() #Check to see if it is the right day and time for the Schedule library function to run the postit function
            telegram_response = get(offset) #wait to receive telegram response

            try:
                for result in telegram_response['result']: #if the telegram response contains a 'result' component, then a message has been received.
                    telegram_result = result
                    break #break out of the 'Recieve message loop'
                if not telegram_result == "": #if the telegram_result is equal to something, then a message has been received.
                    break #break out of the 'Recieve message loop'
                #if no message has been received then loop back to the 'Recieve message loop' and wait to receive a message again.
            except KeyError:
                print "spam recieved"
                pass

        try: #check to see if the result component of the telegram_response contains an update_id
            update_id = result['update_id']
            print 'message received'
        except KeyError: #except the error so the program doesn't crash
            pass
        try: #check to see if the result component of the telegram_response contains text
            text = result['message']['text']
        except KeyError: #except the error so the program doesn't crash
            pass
        try: #check to see if the result component of the telegram_response contains a first and last name
            first_name = result['message']['from']['first_name']
            last_name = result['message']['from']['last_name']
            name = str(first_name + " " + last_name)
        except KeyError: #except the error so the program doesn't crash
            pass
        try: #check to see if the result component of the telegram_response contains a user id
            user_id = result['message']['from']['id']
        except KeyError: #except the error so the program doesn't crash
            pass
        try: #check to see if the result component of the telegram_response contains a chat id
            chat_id = result['message']['chat']['id']
        except KeyError: #except the error so the program doesn't crash
            pass

        if len(Resource) > 0: #if there are resource objects in the Resource array
            for i in range (0,len(Resource)): #loop through the Resource array
                if str(Resource[i].user_id) == str(user_id): #if the user id of the resource from the Resource array is equal to the user id of the current telegram user
                    index = i #set the index variable equal the index of the resource in the Resource array
                    print 'from old user'

        if index == -1: #if the telegram user does not have an associated resource object in the Resource array, their index is defaulted to -1
            try:
                cur.execute("SELECT telegram_user_id__c FROM salesforce.resource__c WHERE telegram_user_id__c = '%s'" % (user_id)) #check to see the telegram user is already on salesforce but hasn't been aproved yet
                query_result = cur.fetchone()
                if query_result[0] == str(user_id):
                    Resource.append(resource(user_id,name,0,False,'')) #a new resource object is created and appended to the Resource array
                    index = len(Resource)-1
                    Resource[index].approved = 0
                    print 'from user who is on Salesforce but has not been approved yet'
                    print str('adding ' + str(Resource[index].name) + ' to RAM')
            except TypeError: #user was not identified using their telegram_user_id
                try:
                    cur.execute("SELECT name FROM salesforce.resource__c WHERE name = '%s'" % (name)) #check to see if the user is on salesforce, doesn't have a telegram_id and isn't approved yet
                    query_result = cur.fetchone()
                    if query_result[0] == str(name):
                        Resource.append(resource(user_id,name,0,False,'')) #a new resource object is created and appended to the Resource array
                        index = len(Resource)-1
                        Resource[index].approved = 0
                        print 'from user who is on Salesforce but does not have a telegram_id and has not been approved yet'
                        print str('adding ' + str(Resource[index].name) + ' to RAM')
                        cur.execute("UPDATE salesforce.resource__c SET telegram_user_id__c = '%s' WHERE name = '%s'" % (user_id, name)) #update Salesforce to include the resource's telegram id on their record
                        con.commit() #commit the previous SQL query to the Postgres database
                        print 'telegram id updated in Salesforce'
                except TypeError: #if the user is not on salesforce yet..
                    Resource.append(resource(user_id,name,0,False,'')) #a new resource object is created and appended to the Resource array
                    index = len(Resource)-1 #The index variable is set to the index of the new resource in the Resourece array
                    Resource[index].approved = 0
                    cur.execute("INSERT INTO salesforce.resource__c (telegram_user_id__c,name,Employee_Status__c) VALUES ('%s', '%s','Active')" % (user_id, name)) #A new resource record is created on Salesforce
                    con.commit()
                    print 'from new user'
                    print str('adding ' + str(Resource[index].name) + ' to Salesforce')
                    print str('adding ' + str(Resource[index].name) + ' to RAM')

        if Resource[index].state == 1: #if the resource  attribute is 1
            if text in ['Yes','No']: #if the telegram_response text is yes or no
                if Resource[index].on_project == True: #if the user was on a project
                    if text == 'Yes': #if the user is still on that project
                        keybHide(Resource[index].user_id,'Thank you for your time. Keep up the good work!')
                        Resource[index].state = 0
                        cur.execute("UPDATE salesforce.resource__c SET Bot_State__c = '%s' WHERE telegram_user_id__c = '%s'" % (str(Resource[index].state),Resource[index].user_id))
                        con.commit()
                    else: #if the user is no longer on that project
                        keyb(Resource[index].user_id, "Are you on a billable project?",[["Yes"],["No"]])
                        Resource[index].engagement_name = ''
                        Resource[index].on_project = False
                        cur.execute("UPDATE salesforce.resource__c SET on_project__c = 'false', engagement_roll_off_date__c = NULL, engagement__c = '' WHERE telegram_user_id__c = '%s'" % (Resource[index].user_id)) #refresh resource object so that new scheduled data can be recorded
                        con.commit()
                else:
                    if text == 'No':
                        keybHide(Resource[index].user_id,'Thank you for your time. Hopefully you will be billable next time we speak!')
                        Resource[index].state = 0
                        Resource[index].engagement_name = ''
                        cur.execute("UPDATE salesforce.resource__c SET on_project__c = 'false', engagement_roll_off_date__c = NULL, engagement__c = '', Bot_State__c = '%s' WHERE telegram_user_id__c = '%s'" % (str(Resource[index].state),Resource[index].user_id))
                        con.commit()
                    else:
                        Resource[index].on_project = True
                        cur.execute("UPDATE salesforce.resource__c SET on_project__c = 'true' WHERE telegram_user_id__c = '%s'" % (user_id))
                        con.commit()
                        ########################Processing the list of Engagements###########################
                        Engagement_Names = []
                        for engagement in Engagement_Objects:
                            try:
                                try:
                                    if not (engagement[2]).index(Resource[index].service_line) < 0:
                                        Engagement_Names.append([engagement[0]])
                                except AttributeError:
                                    pass
                            except ValueError:
                                pass
                        Engagement_Names.append(["Other"])
                        keyb (Resource[index].user_id,"Which project are you currently on? If your project is not on the list, please select 'Other'.", Engagement_Names)
                        Resource[index].state = 2 #set the resource state attribute to 1 - next state of the conversation
                        cur.execute("UPDATE salesforce.resource__c SET Bot_State__c = '%s' WHERE telegram_user_id__c = '%s'" % (str(Resource[index].state),Resource[index].user_id))
                        con.commit()
                        ######################################################################################

            else: #if the telegram_response is not yes or no
                post (Resource[index].user_id, 'Invalid response. Try again.')

        elif Resource[index].state == 2: #if the resource state is 1
            if text in Global_Engagement_Names: #check the telegram user's response was one of the options on the list
                for element in Engagement_Objects: #loop through the engagement objects
                    if text == element[0]: #if telegram response text is = engagement name
                        Resource[index].engagement_name = element[0]
                        cur.execute("UPDATE salesforce.resource__c SET engagement__c = '%s' WHERE telegram_user_id__c = '%s'" % (str(element[1]),user_id)) #set engagement__c = engagement id of Engagment object
                        con.commit()
                keyb(chat_id,"Do you know what date you will be rolling off?",[["Yes"],["No"]])
                Resource[index].state = 3 #set the resource state attribute to 2 - next state of the conversation
                cur.execute("UPDATE salesforce.resource__c SET Bot_State__c = '%s' WHERE telegram_user_id__c = '%s'" % (str(Resource[index].state),Resource[index].user_id))
                con.commit()
            elif text == "Other":
                post (Resource[index].user_id, 'What is the name of the project you are currently on?')
                Resource[index].state = 8
                cur.execute("UPDATE salesforce.resource__c SET Bot_State__c = '%s' WHERE telegram_user_id__c = '%s'" % (str(Resource[index].state),Resource[index].user_id))
                con.commit()
            else: #if telegram user's response was not an option on the list
                post (Resource[index].user_id, 'Invalid response. Try again.')

        elif Resource[index].state == 3:
            if text in ['Yes','No']:
                if text == 'Yes':
                    Resource[index].date = ""
                    post(chat_id,"What date will you be rolling off?")
                    keyb(chat_id,"Enter the month:",month)
                    Resource[index].state = 4
                    cur.execute("UPDATE salesforce.resource__c SET Bot_State__c = '%s' WHERE telegram_user_id__c = '%s'" % (str(Resource[index].state),Resource[index].user_id))
                    con.commit()
                else:
                    keybHide(Resource[index].user_id,'Thank you for you time. Keep up the good work!')
                    Resource[index].state = 0
                    cur.execute("UPDATE salesforce.resource__c SET engagement_roll_off_date__c = NULL, Bot_State__c = '%s' WHERE telegram_user_id__c = '%s'" % (str(Resource[index].state),user_id))
                    con.commit()
            else:
                post(Resource[index].user_id,'Invalid response. Try again.')

        elif Resource[index].state == 4:
            if [text] in month:
                month_num = ['January','February','March','April','May','June','July','August','September','October','November','December'].index(text)+1
                Resource[index].date = str(month_num) +  '-'+str(Resource[index].date)
                if text in ['January','March','May','July','August','October','December']:
                    keyb(chat_id,"Enter the day:",day_31)
                    Resource[index].date_capture_control = 0
                elif text in ['April','June','September','November']:
                    keyb(chat_id,"Enter the day:",day_30)
                    Resource[index].date_capture_control = 1
                else:
                    keyb(chat_id,"Enter the day:",day_28)
                    Resource[index].date_capture_control = 2
                Resource[index].state = 5
                cur.execute("UPDATE salesforce.resource__c SET Bot_State__c = '%s' WHERE telegram_user_id__c = '%s'" % (str(Resource[index].state),Resource[index].user_id))
                con.commit()
            else:
                post(Resource[index].user_id,'Invalid response. Try again.')


        elif Resource[index].state == 5:
            if ([text] in day_31 and Resource[index].date_capture_control == 0) or ([text] in day_30 and Resource[index].date_capture_control == 1) or ([text] in day_28 and Resource[index].date_capture_control == 2):
                Resource[index].date = str(Resource[index].date) + text
                keyb(chat_id,"Enter the year:",year)
                Resource[index].state = 6
                cur.execute("UPDATE salesforce.resource__c SET Bot_State__c = '%s' WHERE telegram_user_id__c = '%s'" % (str(Resource[index].state),Resource[index].user_id))
                con.commit()
            else:
                post(Resource[index].user_id,'Invalid response. Try again.')


        elif Resource[index].state == 6:
            if [text] in year:
                Resource[index].date = text + '-'+ str(Resource[index].date)
                Resource[index].state = 0
                cur.execute("UPDATE salesforce.resource__c SET engagement_roll_off_date__c = '%s', Bot_State__c = '%s' WHERE telegram_user_id__c = '%s'" % (str(Resource[index].date),str(Resource[index].state),user_id))
                con.commit()
                keybHide(Resource[index].user_id,'Thank you for you time. Keep up the good work!')
            else:
                post(Resource[index].user_id,'Invalid response. Try again.')


        elif Resource[index].state == 7: #receiving service line response
            if [text] in service_lines:
                Resource[index].state = 0
                Resource[index].service_line = text
                cur.execute("UPDATE salesforce.resource__c SET ServiceLine__c = '%s', Bot_State__c = '%s' WHERE telegram_user_id__c = '%s'" % (text,str(Resource[index].state),user_id))
                con.commit()
                keybHide(Resource[index].user_id,'Thank you. You can now interact with the DeloitteScheduleBot!')
            else:
                post(Resource[index].user_id,'Invalid response. Try again.')


        elif Resource[index].state == 8: #receiving service line response
            Resource[index].engagement_name = text
            post(Resource[index].user_id,'What is the name of the Opportunity that this project is associated with?')
            Resource[index].state = 9
            cur.execute("UPDATE salesforce.resource__c SET Bot_State__c = '%s' WHERE telegram_user_id__c = '%s'" % (str(Resource[index].state),Resource[index].user_id))
            con.commit()


        elif Resource[index].state == 9: #receiving service line response
            cur.execute("INSERT INTO salesforce.case (Subject, Priority, OwnerId, Description) VALUES ('Request to update Engagement information for Telegram Bot user %s','3 - Normal','00Gb0000001Wl73', '%s has updated his/her schedule with an Engagement titled %s which is associated with an Opportunity titled %s. Currently this Engagement is not available for schedule update selection for %s employees. There are two possible reasons for this: 1)This Engagement does not exist on Salesforce yet or 2)This Engagement does exist on Salesforce but it exists under an Opportunity where %s is not one of the Deloitte Teams Involved.\n\nTo resolve this case, it needs to be determined whether the Engagement that %s has described does already exist on Salesforce. If this Engagement exists on Salesforce, it needs to be determined whether or not it is appropriate to add %s to the Opportunity Splits associated with that Engagement. If it is appropriate to add %s to the Opportunity Splits associated with that Engagement, this should be done and the Resource record associated with %s should be updated accordingly.\n\nAlternatively, if this engagement does not exist on Salesforce, then it needs to be determined whether or not the Engagement should be created or not. If the Engagement should be created, it needs to be created under the Opportunity %s or any other appropriate Opportunity. %s must also be part of the Opportunity Split. The Resource record associated with %s should be updated with this Engagment information which then resolves the case.\n\nIf it is determined that an Engagement should not be created, then %s should be notified of this decision and the project information that was captured on his/her Resource record should be cleared accordingly.')" % (str(Resource[index].name), str(Resource[index].name), str(Resource[index].engagement_name), str(text), str(Resource[index].service_line), str(Resource[index].service_line), str(Resource[index].name), str(Resource[index].service_line), str(Resource[index].service_line), str(Resource[index].name), str(text), str(Resource[index].service_line), str(Resource[index].name), str(Resource[index].name)))
            con.commit()
            keyb(chat_id,"Do you know what date you will be rolling off?",[["Yes"],["No"]])
            Resource[index].state = 3 #set the resource state attribute to 2 - next state of the conversation
            cur.execute("UPDATE salesforce.resource__c SET Bot_State__c = '%s' WHERE telegram_user_id__c = '%s'" % (str(Resource[index].state),Resource[index].user_id))
            con.commit()


        elif Resource[index].state == 0: #if the awaiting_schedule_response checkbox is unchecked and the state is not 5 or 6
            request = ai.text_request() #initiate Api.ai text request object
            request.query = text
            response = request.getresponse() #post text to the api.ai engine store the response a response object.
            API_AI_Response = response.read() #read the contents of the response object
            if text == "/start":
                post(Resource[index].user_id,"Welcome to the DeloitteScheduleBot!\n\n*About:*\nDeloitteScheduleBot is a project that was started by the Customer Applications team in Deloitte Digital Africa. The DeloitteScheduleBot consists of a Telegram bot front-end which is integrated with Salesforce in the back-end. The purpose of the DeloitteScheduleBot is to seamlessly gather and organise information regarding the schedules of Deloitte Employees on a weekly basis. This schedule information can then used to report on the real-time utilization status of teams indicating who is on billable projects and who is on the bench.\n\n*How to use the DeloitteScheduleBot:*\nAfter initiating a conversation with the DeloitteScheduleBot, a request will be forwarded to the DeloitteScheduleBot support team to approve you as a verified user. Until you have been approved, you will only be able to engage in small-talk with bot. Once you have been approved, you will be asked to select your Deloitte service line from a list of all Deloitte service lines. After completing this step, you can begin using the DeloitteScheduleBot. The DeloitteScheduleBot is controlled using a Natural Language Processor that helps it to identify the meaning behind user requests. The following examples demonstrate how to use the DeloitteScheduleBot, however, the commands that are described in these examples are not hard-coded, so you can also communicate with the DeloitteScheduleBot using more natural variations of these commands.\n\n*Commands:*\n1)'I want to update my schedule.'\nThis command will activate the DeloitteScheduleBot's schedule update mechanism allowing you to update your schedule. The bot will ask you if you are on a billable project or not, which project you are currently on and when you are rolling off the current project. This schedule update mechanism is also automatically triggered once a week on a Friday morning at 10am.\n\n2)'Who is on the bench?'\nThis command will activate the DeloitteScheduleBot's reporting mechanism to give you a report of all employees within your service line who are currently not on billable projects. You can also query resources in a specific service line by asking something like 'Who is on the bench in Digital - Customer Applications?' for example.\n\n3)'Who is on a project?'\nThis command will activate the DeloitteScheduleBot's reporting mechanism to give you a report of all employees within your service line who are currently on billable projects whilst also indicating which projects each employee is currenlty on. You can also query resources in a specific service line by asking something like 'Who is on a project in Digital - Advisory?' for example.\n\n4)'I need help.'\nThe DeloitteScheduleBot will respond to this command with the 'How to use the DeloitteScheduleBot' information.\n\n*Contact Us:*\nIf there are any issues or if there is any feedback that you would like to report to us, please don't hesitate to email Steven Kimmel (skimmel@deloitte.co.za) and he will get back to you as soon as possible.")
            elif '"intentName": "Help"' in API_AI_Response:
                post(Resource[index].user_id,"*How to use the DeloitteScheduleBot:*\nAfter initiating a conversation with the DeloitteScheduleBot, a request will be forwarded to the DeloitteScheduleBot support team to approve you as a verified user. Until you have been approved, you will only be able to engage in small-talk with bot. Once you have been approved, you will be asked to select your Deloitte service line from a list of all Deloitte service lines. After completing this step, you can begin using the DeloitteScheduleBot. The DeloitteScheduleBot is controlled using a Natural Language Processor that helps it to identify the meaning behind user requests. The following examples demonstrate how to use the DeloitteScheduleBot, however, the commands that are described in these examples are not hard-coded, so you can also communicate with the DeloitteScheduleBot using more natural variations of these commands.\n\n*Commands:*\n1)'I want to update my schedule.'\nThis command will activate the DeloitteScheduleBot's schedule update mechanism allowing you to update your schedule. The bot will ask you if you are on a billable project or not, which project you are currently on and when you are rolling off the current project. This schedule update mechanism is also automatically triggered once a week on a Friday morning at 10am.\n\n2)'Who is on the bench?'\nThis command will activate the DeloitteScheduleBot's reporting mechanism to give you a report of all employees within your service line who are currently not on billable projects. You can also query resources in a specific service line by asking something like 'Who is on the bench in Digital - Customer Applications?' for example.\n\n3)'Who is on a project?'\nThis command will activate the DeloitteScheduleBot's reporting mechanism to give you a report of all employees within your service line who are currently on billable projects whilst also indicating which projects each employee is currenlty on. You can also query resources in a specific service line by asking something like 'Who is on a project in Digital - Advisory?' for example.\n\n4)'I need help.'\nThe DeloitteScheduleBot will respond to this command with the 'How to use the DeloitteScheduleBot' information.\n\n*Contact Us:*\nIf there are any issues or if there is any feedback that you would like to report to us, please don't hesitate to email Steven Kimmel (skimmel@deloitte.co.za) and he will get back to you as soon as possible.")
            elif '"intentName": "Greeting"' in API_AI_Response: #if the response contains the term 'greeting'
                post(Resource[index].user_id,"Hello, I am DeloitteScheduleBot. My job is to help schedule resources. I am currently still a noob as I've still got lots to learn.")
            elif '"action": "smalltalk.' in API_AI_Response: #API.AI identified an action from the  smalltalk domain
                parsed_response = json.loads(API_AI_Response) # lets parse the response from API.AI so that
                temp_string = parsed_response['result']['fulfillment']['speech'] # we can find the speech fulfilment and
                post(Resource[index].user_id,temp_string) # reply to the user with the associated result
            elif '"intentName": "System Query"' in API_AI_Response and Resource[index].approved: #if the response contains the term 'system query'
                if '"SystemObject": "Bench"' in API_AI_Response: #if the response contains the term 'bench'
                    temp_string = "*Here's a list of " + str(Resource[index].service_line) +" employees on the bench:*\n\n"
                    cur.execute("SELECT name, on_project__c,SchedularBotAccess__c FROM salesforce.resource__c WHERE on_project__c = 'false' AND Employee_Status__c = 'Active' AND SchedularBotAccess__c = 'Approved' AND ServiceLine__c = '%s'" % (Resource[index].service_line))
                    rows = cur.fetchall()
                    for row in rows:
                        temp_string = temp_string + str(row[0]) + '\n'
                elif '"SystemObject": "Project"' in API_AI_Response: #if the response contains the term 'project'
                    temp_string = "*Here's a list of " + str(Resource[index].service_line) +" employees who are on billable projects:*\n\n"
                    cur.execute("SELECT name,engagement__c,engagement_roll_off_date__c, on_project__c,SchedularBotAccess__c FROM salesforce.resource__c WHERE on_project__c = 'true' AND Employee_Status__c = 'Active' AND SchedularBotAccess__c = 'Approved' AND ServiceLine__c = '%s'" % (Resource[index].service_line))
                    rows = cur.fetchall()
                    for row in rows:
                        for element in Engagement_Objects: #loop through the engagement objects
                            if row[1] == element[1]: #if telegram response text is an element of the an engagement object
                                temp_string = temp_string + str(row[0]) + ': ' + str(element[0]) + '\n\n'
                post(Resource[index].user_id,temp_string)
            elif '"intentName": "Update Schedule"' in API_AI_Response and Resource[index].approved: #if the response contains the term 'system query'
                Resource[index].state = 1
                if Resource[index].on_project == True: #if user is on a project
                    keyb(Resource[index].user_id, "Are you still on %s?" % (Resource[index].engagement_name),[["Yes"],["No"]])
                else:
                    keyb(Resource[index].user_id, "Are you on a billable project?",[["Yes"],["No"]])
            elif '"intentName": "Query Other Pod"' in API_AI_Response and Resource[index].approved:
                parsed_response = json.loads(API_AI_Response) # lets parse the response from API.AI so that
                DigitalPod = parsed_response['result']['parameters']['DigitalPods'] # we can find the DigitalPod
                SystemObject = parsed_response['result']['parameters']['SystemObject'] # we can find the SystemObject
                if SystemObject == "Bench":
                    temp_string = "*Here's a list of " + str(DigitalPod) +" employees on the bench:*\n\n"
                    cur.execute("SELECT name, on_project__c,SchedularBotAccess__c FROM salesforce.resource__c WHERE on_project__c = 'false' AND Employee_Status__c = 'Active' AND SchedularBotAccess__c = 'Approved' AND ServiceLine__c = '%s'" % (str(DigitalPod)))
                    rows = cur.fetchall()
                    for row in rows:
                        temp_string = temp_string + str(row[0]) + '\n'
                elif SystemObject == "Project":
                    temp_string = "*Here's a list of " + str(DigitalPod) +" employees who are on billable projects:*\n\n"
                    cur.execute("SELECT name,engagement__c,engagement_roll_off_date__c, on_project__c,SchedularBotAccess__c FROM salesforce.resource__c WHERE on_project__c = 'true' AND Employee_Status__c = 'Active' AND SchedularBotAccess__c = 'Approved' AND ServiceLine__c = '%s'" % (str(DigitalPod)))
                    rows = cur.fetchall()
                    for row in rows:
                        for element in Engagement_Objects: #loop through the engagement objects
                            if row[1] == element[1]: #if telegram response text is an element of the an engagement object
                                temp_string = temp_string + str(row[0]) + ': ' + str(element[0]) + '\n\n'
                post(Resource[index].user_id,temp_string)
            elif Resource[index].approved: #if the response does not contain any known terms and the resource was approved
                post(Resource[index].user_id,"I didn't quite understand that. I will be posting this to my database to learn from at a later stage.")
                cur.execute("INSERT INTO salesforce.new__c (New_Headline__c,News_Text__c) VALUES ('%s', '%s')" % (str('Unrecognised post by: ' + name),text.replace("'", "")))
                con.commit()
            else: #if the resource is not approved
                post(Resource[index].user_id,"Your access to the DeloitteScheduleBot is waiting for approval. Once approved, you will be able to interact with this bot. For now, you can enjoy some small talk with this bot.")

        offset = update_id + 1 #increment the offset variable to receive the next message
        telegram_result = "" #refresh the telegram_result variable
        index = -1 #refresh the index variable
########################################################
