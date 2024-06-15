from flask import Flask, send_file, request, abort
from flask_cors import CORS, cross_origin
from datetime import datetime
import os, arif, json, account, threading, database, time
from cryptography.fernet import Fernet
import myEnvironment

app = Flask(__name__)
CORS(app, methods=["POST", "GET"], origins=[myEnvironment.siteUrl])

# This is the our shared folder path. This path includes our website content.
sharedFolder = "/shared/"
# This is the our log file name
logFile = "app.log"


registeredIPAddresses = []

# This method for backup the all database.
def backupDatabaseThread():
    while True:
        try:
            time.sleep(24 * 60 * 60)
            database.backupDatabase()
        except:
            pass


threading.Thread(target=backupDatabaseThread).start()

database.backupDatabase()


# This method check users token reset time. if reset time is pased user tokens will be reset.
def checkTokens():
    while True:
        time.sleep(18000)
        # Clear IP Addresses that created account(s)
        global registeredIPAddresses
        registeredIPAddresses = []
        account.checkTokens()


threading.Thread(target=checkTokens).start()

account.checkTokens()


# This method writes a log file. Log file format is like this:
# <current time> | <IP Adress> | <http method> | <using route> | <sended values> | <extra values(optional)>
def writeLog(extra: str = None):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logMessage = (
        f"{timestamp} | {request.remote_addr} | {request.method} | {request.url_rule} | {request.values.to_dict(flat=False)}"
        + ("| extra:" + str(extra) if extra is not None else "")
    )
    # Encrypition Methods
    with open(logFile, "a", encoding="utf-8") as log:
        log.write(f"{logMessage}\n")


# This method gets data from request.
def req(arg):
    value = None
    try:
        try:
            value = request.json[arg]
            if value is not None:
                return value
        except:
            pass

        value = request.args.get(arg)
        if value is not None:
            return value

        value = request.form.get(arg)
        if value is not None:
            return value

        value = request.files.get(arg)
        if value is not None:
            return value
    except:
        return None
    return value


# This method checks user is admin. If user is not admin method will be abort the connection. Otherwise everythink will be work.
def ifAdmin():
    try:
        writeLog()
        data = req("data")
        try:
            data = json.loads(data)
        except:
            pass
        user = account.login(data.get("adminEmail"), data.get("adminPassword"))
        if "error" in list(user.keys()):
            abort(403)
        elif user["data"]["authority"] not in ["ADMIN", "GRANDADMIN"]:
            abort(403)
        else:
            return
    except:
        abort(403)


# This method sends file from shared file. If the filePath is starts with underscore(_) method will not send the file.
@app.route(sharedFolder + "<path:filePath>", methods=["GET"])
@cross_origin(origins=[myEnvironment.siteUrl])
def getFile(filePath):
    if filePath[0] == "_":
        return "Private File", 403
    filePath = os.path.join("." + sharedFolder, filePath)
    writeLog()
    if os.path.exists(filePath):
        return send_file(filePath, as_attachment=True)
    else:
        return "Cannot Find File", 404


@app.route("/loadFile", methods=["POST"])
@cross_origin(origins=[myEnvironment.siteUrl])
def loadFile():
    try:
        writeLog()
        ifAdmin()
        supportedTypes = (".mp3", ".mp4", ".png", ".jpeg", ".jpg")
        file = request.files["file"]
        data = json.loads(req("data"))
        return {"data": database.loadFile(file, data["saveTo"], supportedTypes)}
    except:
        return database.MysqlErrors.unknownError


@app.route("/deletePlace", methods=["POST"])
@cross_origin(origins=[myEnvironment.siteUrl])
def deletePlace():
    try:
        ifAdmin()
        data = req("data")
        return database.deletePlace(data["place"])
    except:
        return database.MysqlErrors.unknownError


@app.route("/createPlace", methods=["POST"])
@cross_origin(origins=[myEnvironment.siteUrl])
def createPlace():
    try:
        ifAdmin()
        data = req("data")
        file = request.files["file"]
        supportedFiles = (".png", ".jpg", ".jpeg")
        if not file.filename.lower().endswith(supportedFiles):
            return database.MysqlErrors.valueError
        data = json.loads(data)
        if not database.canCreateNewPlace(data):
            return database.MysqlErrors.valueError
        return database.createPlace(
            data["placeNames"],
            file,
            data["placeImageInfo"],
            data["placeTexts"],
            data["placeType"],
            data.get("parentCityName"),
        )
    except:
        return database.MysqlErrors.unknownError


# This method chats with chat-gpt model using open-ai's API
@app.route("/talkToArif", methods=["POST"])
@cross_origin(origins=[myEnvironment.siteUrl])
def talkToArif():
    try:
        writeLog()
        data = dict(req("data"))
        talks = data.copy()["talks"]
        del data["talks"]
        talks = talks[:-1]  # do not inculde '[arif is thinking]' part
        response = arif.talkToArif(talks, data)
        writeLog(str([talks[-1], response]))
        return response, 200
    except:
        return database.MysqlErrors.unknownError, 400


# This method plans users day using chat-gpt
@app.route("/plan", methods=["POST"])
@cross_origin(origins=[myEnvironment.siteUrl])
def plan():
    try:
        data = req("data")
        availablePlans = data.copy()["availablePlans"]
        del data["availablePlans"]
        response = arif.plan(availablePlans, data)
        writeLog(str(response))
        return response
    except:
        return database.MysqlErrors.unknownError


# This method for user login.
@app.route("/login", methods=["POST"])
@cross_origin(origins=[myEnvironment.siteUrl])
def login():
    try:
        writeLog()
        data = req("data")
        if "email" in list(data.keys()):
            return account.login(data["email"], data["password"])
        else:
            return account.loginWithSessionKey(data["sessionKey"])
    except:
        return database.MysqlErrors.unknownError, 400


# This method for user register.
@app.route("/register", methods=["POST"])
@cross_origin(origins=[myEnvironment.siteUrl])
def register():
    try:
        writeLog()
        if  registeredIPAddresses.count(request.remote_addr) >= 3:
            return database.MysqlErrors.tooManyRegisters
        data = req("data")
        authority = data.get("authority")
        if len(data["password"]) > 25 or len(data["email"]) > 50:
            return database.MysqlErrors.valueError
        if authority is None:
            authority = "USER"

        if authority != "USER":
            if data.get("adminEmail") is None or data.get("adminPassword") is None:
                return database.MysqlErrors.authorizationError

            admin = account.login(data.get("adminEmail"), data.get("adminPassword"))
            if "error" in list(admin.keys()):
                return database.MysqlErrors.authorizationError
            if admin["data"]["authority"] != "ADMIN":
                return database.MysqlErrors.authorizationError
        if account.userExist(data["email"]):
            return database.MysqlErrors.userExists
        res = account.register(
            data["email"],
            data["password"],
            authority,
            1000 if authority is None or authority == "USER" else -1,  # Tokens
            1000 if authority is None else -1,  # MaxTokens
            datetime.now(),  # TokenTime
            3,
        )
        if "data" in list(res.keys()):
            registeredIPAddresses.append(request.remote_addr)
            return res, 200
        else:
            return res, 400

    except:
        return database.MysqlErrors.unknownError, 400


# This method for delete an account
@app.route("/deleteAccount", methods=["POST"])
@cross_origin(origins=[myEnvironment.siteUrl])
def deleteAccount():
    try:
        writeLog()
        data = req("data")
        return account.deleteAccount(data["email"], data["password"])
    except:
        database.MysqlErrors.unknownError


@app.route("/resetSessionKey", methods=["POST"])
@cross_origin(origins=[myEnvironment.siteUrl])
def resetSessionKey():
    try:
        writeLog()
        data = req("data")
        email = data["email"]
        password = data["password"]
        return account.resetSessionKey(email, password)
    except:
        return database.MysqlErrors.unknownError


@app.route("/resetPassword", methods=["POST"])
@cross_origin(origins=[myEnvironment.siteUrl])
def resetPassword():
    try:
        writeLog()
        data = req("data")
        email = data["email"]
        password = data["password"]
        newPassword = data["newPassword"]
        return account.resetPassword(email, password, newPassword)
    except:
        return database.MysqlErrors.unknownError


@app.route("/checkAdmin", methods=["POST"])
@cross_origin(origins=[myEnvironment.siteUrl])
def checkAdmin():
    try:
        writeLog()
        data = req("data")
        user = account.login(data.get("email"), data.get("password"))
        if "error" in list(user.keys()):
            return {"data": False}
        elif user["data"]["authority"] not in ["ADMIN", "GRANDADMIN"]:
            return {"data": False}
        else:
            return {"data": True}
    except:
        return database.MysqlErrors.unknownError


@app.route("/getTokenCount", methods=["POST"])
@cross_origin(origins=[myEnvironment.siteUrl])
def getToken():
    try:
        writeLog()
        data = dict(req("data"))
        return account.getTokenCount(data["email"])
    except:
        return database.MysqlErrors.unknownError


# This method for only admins.
@app.route("/setToken", methods=["POST"])
@cross_origin(origins=[myEnvironment.siteUrl])
def setToken():
    try:
        writeLog()
        ifAdmin()
        data = dict(req("data"))
        return {
            "data": account.setToken(
                data.get("email"),
                "3",
                data.get("newTokens"),
                data.get("newMaxTokens"),
            )
        }
    except:
        return database.MysqlErrors.unknownError


@app.route("/savePlace", methods=["POST"])
@cross_origin(origins=[myEnvironment.siteUrl])
def savePlace():
    try:
        writeLog()
        ifAdmin()
        data = dict(req("data"))
        return {
            "data": database.savePlace(data["place"], json.loads(data["placeValues"]))
        }
    except:
        return database.MysqlErrors.unknownError



if __name__ == "__main__":
    app.run()
