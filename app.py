from flask import Flask, jsonify, request
from flask_restful import Api, Resource
from pymongo import MongoClient
import bcrypt
import requests
import subprocess
import json


app = Flask(__name__)
api = Api(app)

client = MongoClient('mongodb://localhost:27017/')
db = client.ImageRecognition
users = db["Users"]


def UserExist(username):
    if users.find({"Username": username}).count() == 0:
        return False
    else:
        return True


class Register(Resource):
    def post(self):
        posteddata = request.get_json()

        username = posteddata["username"]
        password = posteddata["password"]

        if UserExist(username):
            retjson = {
                "Status code": 301,
                "Message": "User already exist !"
            }
            return jsonify(retjson)

        hashed_pw = bcrypt.hashpw(password.encode("utf8"), bcrypt.gensalt())

        users.insert({
            "Username": username,
            "Password": hashed_pw,
            "Tokens": 4
        })
        retjson = {
            "Status code": 200,
            "Message": "You are sucessfully Register to the api"
        }
        return jsonify(retjson)


def verify_pw(username, password):
    if not UserExist(username):
        return False

    hashed_pw = users.find({
        "Username": username
    })[0]['Password']

    if bcrypt.hashpw(password.encode("utf8"), hashed_pw) == hashed_pw:
        return True
    else:
        return False


def generateReturnDictionary(Status, msg):
    retjson = {
        'status code': Status,
        'message': msg
    }
    return retjson


def verifyCredincel(username, password):
    if not UserExist(username):
        return generateReturnDictionary(301, "Invalid username"), True

    correct_pw = verify_pw(username, password)
    if not correct_pw:
        return generateReturnDictionary(302, "Invalid password"), True

    return None, False


class Classify(Resource):
    def post(self):
        posteddata = request.get_json()

        username = posteddata["username"]
        password = posteddata["password"]
        url = posteddata["url"]

        retjson, error = verifyCredincel(username, password)
        if error:
            return jsonify(retjson)

        tokens = users.find({
            "Username": username
        })[0]["Tokens"]

        if tokens <= 0:
            return jsonify(generateReturnDictionary(303, "Not enough tokens!"))

        r = requests.get(url)
        retjson = {}
        with open("temp.jpg", "wb") as f:
            f.write(r.content)
            proc = subprocess.Popen(
                'python classify_image.py --model_dir=. --image_file=./temp.jpg')
            proc.communicate()[0]
            proc.wait()
            with open("text.txt") as g:
                retjson = json.load(g)
        users.update({
            "Username": username
        },
            {
            "$set": {
                "Tokens": tokens-1
            }
        })
        return retjson


class Refill(Resource):
    def post(self):
        posteddata = request.get_json()

        username = posteddata["username"]
        password = posteddata["adminpw"]
        amount = posteddata["amount"]

        if not UserExist(username):
            return jsonify(generateReturnDictionary(301, "Invalid Username"))

        correct_pw = "abc123"

        if not password == correct_pw:
            return jsonify(generateReturnDictionary(304, "Invalid administater password!"))

        users.update({
            "Username": username
        },
            {
            "$set": {
                "Tokens": amount
            }
        })
        return jsonify(generateReturnDictionary(200, "Refill Sucessfully!"))


api.add_resource(Register, '/register')
api.add_resource(Classify, '/classify')
api.add_resource(Refill, '/refill')

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)
