import mysql, myEnvironment
import mysql.connector, uuid, json, shutil, os, datetime
import myEnvironment


class MysqlErrors:
    connectionError = {"error": "Connection Error"}
    unknownError = {"error": "Unknown Error"}
    userNotFoundError = {"error": "User Not Found"}
    registerError = {"error": "An Error Occurred While Creating the User"}
    userExists = {"error": "User Already Exist"}
    valuesEmpty = {"error": "All The Values Are Empty"}
    authorizationError = {"error": "Authorization Error"}
    valueError = {"error": "Value Error"}
    tokenError = {"error":"Token Error"}
    tooManyRegisters = {"error":"Too Many Register Processes"}


def getMySQLConnection(user=None, passwd=None, database=None):
    try:
        connection = mysql.connector.connect(
            host=myEnvironment.mysqlIP,
            user=myEnvironment.mysqlUser if user is None else user,
            passwd=myEnvironment.mysqlPassword if passwd is None else passwd,
            database=myEnvironment.mysqlDatabase if database is None else database,
        )
        if not connection:
            return MysqlErrors.connectionError
        return connection
    except:
        return MysqlErrors.unknownError


def backupDatabase():
    try:
        connection = getMySQLConnection()
        cursor = connection.cursor()
        cursor.execute("SHOW TABLES")

        targetConnection = getMySQLConnection(
            database=myEnvironment.mysqlBackupDatabase
        )
        targetCursor = targetConnection.cursor()
        targetCursor.execute("SHOW TABLES")
        for (table,) in targetCursor:
            targetCursor.execute(f"DROP TABLE {table}")
            targetConnection.commit()
        for (tableName,) in cursor:
            targetCursor.execute(
                f"CREATE TABLE {tableName} LIKE {myEnvironment.mysqlDatabase}.{tableName}"
            )
            targetConnection.commit()
            targetCursor.execute(
                f"INSERT INTO {tableName} SELECT * FROM {myEnvironment.mysqlDatabase}.{tableName};"
            )
            targetConnection.commit()
    except:
        pass



def getRandomSessionKey():
    return str(uuid.uuid1()) + str(uuid.uuid1()) + str(uuid.uuid1())


def loadFile(file, saveTo, supportedTypes=None):
    if supportedTypes is not None:
        if not file.filename.endswith(supportedTypes):
            return MysqlErrors.valueError
    filePath = os.path.join("shared/", saveTo, file.filename)
    file.save(filePath)
    filePath = os.path.join(myEnvironment.apiUrl, filePath)
    return filePath


def savePlace(place, placeValues):
    try:
        with open("./shared/places.json", "r+", encoding="utf-8") as jf:
            js = json.load(jf)
            if not place in list(js.keys()):
                return MysqlErrors.valueError
            js[place] = placeValues
            jf.seek(0)
            jf.truncate()
            json.dump(js, jf, indent=4, ensure_ascii=False)
            return js
    except:
        return MysqlErrors.unknownError


def deletePlace(place):
    try:
        with open("./shared/places.json", "r+", encoding="utf-8") as jf:
            js = json.load(jf)
            if not place in list(js.keys()):
                return MysqlErrors.valueError
            folder = os.path.join("./shared", js[place]["folder"])
            placeValue = {}
            placeValue[place] = js[place]
            with open(os.path.join(folder, "values.json"), "w", encoding="utf-8") as bf:
                json.dump(placeValue, bf, indent=4, ensure_ascii=False)
            zipFolder(folder, js[place]["folder"] + str(datetime.datetime.now()))
            shutil.rmtree(folder)
            del js[place]
            jf.seek(0)
            jf.truncate()
            json.dump(js, jf, indent=4, ensure_ascii=False)
            return {"data": json.dumps(js)}

    except:
        return MysqlErrors.unknownError


def canCreateNewPlace(place: dict):
    try:
        for language in myEnvironment.supportedLanguages:
            if (
                place["placeNames"][language].strip() == ""
                or place["placeTexts"][language].strip() == ""
            ):
                return False

            for field in ["titles", "texts"]:
                if (
                    not place.get("placeImageInfo", {})
                    .get(field, {})
                    .get(language, "")
                    .strip()
                ):
                    return False

        for field in ["photographerLink", "photographerName"]:
            if place["placeImageInfo"][field].strip() == "":
                return False

        if place["placeType"] == "city-area" and place["parentCityName"] is None:
            return False

        return True
    except:
        return False


def createPlace(
    placeNames: dict,
    placeImage,
    placeImageInfo: dict,
    placeTexts: dict,
    placeType: str,
    parentCityName: str = None,
):
    try:
        snakePlaceName = convertString(placeNames["en"])  # convert to snakeCase
        cammelPlaceName = convertString(
            placeNames["en"], "cammel"
        )  # convert to cammelCase
        placeFolder = convertString(
            placeNames["en"], "-$$"
        )  # $$: This is the character from loop(upper), -: This is the custom character
        if placeType != "city":
            with open("./shared/places.json", "r", encoding="utf-8") as jf:
                js = json.load(jf)
                if snakePlaceName in list(js.keys()) or parentCityName not in list(
                    js.keys()
                ):
                    return MysqlErrors.valueError

        place = {
            "active": False,
            "type": placeType,
            "names": placeNames,
            "folder": placeFolder,
            "link": (
                f"/cities/{placeFolder}"
                if placeType == "city"
                else f"/cities/{parentCityName}/{placeFolder}"
            ),
            "images": [],
            "texts": placeTexts,
        }
        if placeType != "city":
            place.update({"city": parentCityName})
        try:
            os.mkdir(os.path.join("./shared/", placeFolder))
        except:
            pass
        placeImageUrl = loadFile(placeImage, placeFolder)
        place["images"].append(
            {
                "imageUrl": placeImageUrl,
                "photographerLink": placeImageInfo["photographerLink"],
                "photographer": placeImageInfo["photographerName"],
                "titles": placeImageInfo["titles"],
                "texts": placeImageInfo["texts"],
            }
        )
        place.update({"pageContents":[]})
        with open("./shared/places.json", "r+", encoding="utf-8") as jf:
            js = json.load(jf)
            js.update({str(snakePlaceName): place})
            jf.seek(0)
            jf.truncate()
            json.dump(js, jf, indent=4, ensure_ascii=False)
            return {"data": json.dumps(js[snakePlaceName])}

    except:
        return MysqlErrors.unknownError


def convertString(text: str, convert: str = "snake", convertTR=True):
    newText = ""
    space = False
    trCharacters = {"Ğ": "G", "Ü": "U", "İ": "I", "Ş": "S", "Ö": "O", "Ç": "C"}
    for t in text:
        if t.upper() in trCharacters.keys() and convertTR:
            t = trCharacters[t]

        if space:
            newText += (
                "_" + t
                if convert == "snake"
                else (
                    t.upper()
                    if convert == "cammel"
                    else convert.replace("$$", t.upper()).replace("½½", t.lower())
                )
            )
            space = False
            continue
        if t == " ":
            space = True
            continue
        newText += t

    return newText


def zipFolder(folderPath, zipName):
    # Check if the folder path is valid
    if not os.path.isdir(folderPath):
        return

    # Parent directory of the folder
    parentDir = os.path.dirname(folderPath)

    # Name of the folder to be zipped
    folderName = os.path.basename(folderPath.rstrip("/\\"))

    # Full path to the zip file
    zipFilePath = os.path.join(parentDir, zipName)

    # Zip the folder
    shutil.make_archive(zipFilePath, "zip", parentDir, folderName)
