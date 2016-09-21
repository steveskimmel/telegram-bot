import json

#The resource class contains a function which defines a new resource object. Each resource has a user_id, a name, a phase and a date associated with them.
#The user_id and name of the resource uniquely identifies each resource from another.
#The phase of a resource controls the flow of the conversation that resource has with the bot.
#The date of the resource controls the flow of capturing the project role off date from the resource.
#The on_project and project_name atrribute are used to temporarily store data when polling users
#The approved attribute describes whether or not a resource is approved on salesforce
#The service_line attribute stores a resource's service_line

class resource:

   def __init__(self, user_id, name, state, on_project, service_line):
         self.user_id = user_id
         self.name = name
         self.state = state
         self.date = ""
         self.date_capture_control = 0
         self.on_project = on_project
         self.engagement_name = ""
         self.approved = 1
         self.service_line = service_line
