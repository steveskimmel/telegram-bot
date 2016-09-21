import requests
import json

bot_api_token = '250322015:AAEXNmjBtOdUVCzUTYZotgaJoLkfTtvzppo' #telegram bot api token

def post(chat_id,text): #Function to post a text message to a specific chat_id
    requests.request("post","https://api.telegram.org/bot{0}/sendMessage".format(bot_api_token),params ={'chat_id':chat_id,'text':text, 'parse_mode': 'markdown'})

def keyb(chat_id,text,keyboard): #Function to post a text message and display a keyboard array of options to a specific chat_id
    requests.request("post","https://api.telegram.org/bot{0}/sendMessage".format(bot_api_token),params ={'chat_id':chat_id,'text': text,'reply_markup':json.dumps({'keyboard':keyboard,'one_time_keyboard':True,'selective':True})})

def keybHide(chat_id,text): #Function to post a text message and hide a previously displayed keyboard array of options to a specific chat_id
    requests.request("post","https://api.telegram.org/bot{0}/sendMessage".format(bot_api_token),params ={'chat_id':chat_id,'text': text,'reply_markup':json.dumps({'hide_keyboard':True,'selective':False})})

def get (offset): #Function to wait for the next message from the bot's incoming messages queue and then return the message in a json object
  result = requests.request("get", "https://api.telegram.org/bot{0}/getUpdates".format(bot_api_token),params={'offset':offset,'limit':'1','timeout':'60'})
  return result.json()
