import os
import sys
import json

import requests
import diagnose
import facebook
from flask import Flask, request

app = Flask(__name__)


@app.route('/', methods=['GET'])
def verify():
    # when the endpoint is registered as a webhook, it must echo back
    # the 'hub.challenge' value it receives in the query arguments
    if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.challenge"):
        if not request.args.get("hub.verify_token") == os.environ["VERIFY_TOKEN"]:
            return "Verification token mismatch", 403
        return request.args["hub.challenge"], 200

    return "Hello world", 200


@app.route('/', methods=['POST'])
def webhook():

    # endpoint for processing incoming messaging events
    data = request.get_json()
    log(data)  # you may not want to log every incoming message in production, but it's good for testing

    if data["object"] == "page":

        for entry in data["entry"]:
            for messaging_event in entry["messaging"]:

                if messaging_event.get("message"):  # someone sent us a message

                    sender_id = messaging_event["sender"]["id"]        # the facebook ID of the person sending you the message
                    recipient_id = messaging_event["recipient"]["id"]  # the recipient's ID, which should be your page's facebook ID

                    # sort different types of messages
                    response = None
                    message = messaging_event["message"]
                    if message.get("text"): # get message
                        message = message["text"]
                    elif message.get("attachments"):    # get attachment
                        attach = message["attachments"][0]  # loop over attachments?
                        if attach["type"] == "location":
                            latitude = attach["payload"]["coordinates"]["lat"]
                            longitude = attach["payload"]["coordinates"]["long"] 
                            message = "Location: " + str(latitude) + ", " + str(longitude)  
                        elif attach["type"] == "image":
                            image_url = attach["payload"]["url"]
                            message = "Image url: " + image_url
                    response = diagnose.get_response(message)
                    if response is not None:
                        log(response)
                        if response == "Hi":
                            init_buttom_template(sender_id, last_name)
                        else:
                            send_message(sender_id, response)

                if messaging_event.get("delivery"):  # delivery confirmation
                    pass

                if messaging_event.get("optin"):  # optin confirmation
                    pass

                if messaging_event.get("postback"):  # user clicked/tapped "postback" button in earlier message
                    sender_id = messaging_event["sender"]["id"]        # the facebook ID of the person sending you the message
                    recipient_id = messaging_event["recipient"]["id"]
                    message = messaging_event["postback"]["payload"]
                    send_message(sender_id, message)
                    # send_message(sender_id, "What symptoms do you have?")

    return "ok", 200


def send_message(recipient_id, message_text):

    # get user info
    r = requests.get('https://graph.facebook.com/v2.6/'+recipient_id+
        '?fields=first_name,last_name,profile_pic,locale,timezone,gender&access_token='
        +os.environ["PAGE_ACCESS_TOKEN"])
    first_name = str(r.json()["first_name"])
    last_name = str(r.json()["last_name"])
    gender = str(r.json()["gender"])
    profile_pic = str(r.json()["profile_pic"])

    log("sending message to {recipient}: {text}".format(recipient=recipient_id, text=message_text))

    params = {
        "access_token": os.environ["PAGE_ACCESS_TOKEN"]
    }
    headers = {
        "Content-Type": "application/json"
    }
    data = json.dumps({
        "recipient": {
            "id": recipient_id
        },
        "message": {
            "text": message_text
        }
    })
    r = requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers, data=data)
    if r.status_code != 200:
        log(r.status_code)
        log(r.text)


def init_buttom_template(recipient_id, last_name):

    # get user info
    r = requests.get('https://graph.facebook.com/v2.6/'+recipient_id+
        '?fields=first_name,last_name,profile_pic,locale,timezone,gender&access_token='
        +os.environ["PAGE_ACCESS_TOKEN"])
    try:
        first_name = str(r.json()["first_name"])
    except:
        first_name = None
    try:
        last_name = str(r.json()["last_name"])
    except:
        last_name = None
    try:
        gender = str(r.json()["gender"])
    except:
        gender = None
    try:
        profile_pic = str(r.json()["profile_pic"])
    except:
        profile_pic = None

    welcome_message = "Hello! How may I help you?"
    if gender is not None:
        if gender == 'male':
            welcome_message = "Hello Mr."+" "+first_name+" "+last_name + "! How may I help you?"
        else:
            welcome_message = "Hello Ms."+" "+first_name+" "+last_name + "! How may I help you?"
    else:
        welcome_message = "Hello "+first_name+" "+last_name + "! How may I help you?" 

    log("Sending button template to {recipient}.".format(recipient=recipient_id))

    params = {
        "access_token": os.environ["PAGE_ACCESS_TOKEN"]
    }
    headers = {
        "Content-Type": "application/json"
    }
    data = json.dumps({
        "recipient": {
            "id": recipient_id
        },
        "message":{
            "attachment":{
                "type":"template",
                "payload":{
                    "template_type":"button",
                    "text": welcome_message,
                    "buttons":[
                        {
                        'type': 'postback',
                        'title': 'Symptom checker',
                        'payload': 'What symptoms do you have?'
                        },
                        {
                        'type': 'postback',
                        'title': 'Health alerts',
                        'payload': 'Which diseases and/or symptoms would you like to check in your local area?'
                        }
                        # ,
                        # {
                        # 'type': 'web_url',
                        # 'title': 'Get medical info',
                        # 'url': 'www.google.com'
                        # }
                    ]
                }
            }
        }
    })
    r = requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers, data=data)
    # if r.status_code != 200:
    #     log(r.status_code)
    #     log(r.text)

    # log(r.text)


def log(message):  # simple wrapper for logging to stdout on heroku
    print str(message)
    sys.stdout.flush()


if __name__ == '__main__':
    app.run(debug=True)
