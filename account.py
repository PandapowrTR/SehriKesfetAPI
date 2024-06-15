import datetime
from database import *
import database, secret


def getUser(email, decrypt: bool = True):
    try:
        connection = getMySQLConnection()
        if isinstance(connection, dict):
            return connection
        cursor = connection.cursor()
        cursor.execute(f"SELECT * FROM USERS")
        user = None
        for row in cursor:
            if secret.__decrypt(row[0]) == email:
                user = {
                    "email": secret.__decrypt(row[0]) if decrypt else row[0],
                    "password": secret.__decrypt(row[1]) if decrypt else row[1],
                    "authority": secret.__decrypt(row[2]) if decrypt else row[2],
                    "tokens": row[3],
                    "maxTokens": row[4],
                    "tokenUpdate": row[5],
                    "nextTokenUpdateDays": row[6],
                }
                break
        if user is not None:
            return {"data": user}
        return MysqlErrors.userNotFoundError
    except:
        return MysqlErrors.unknownError


def login(email, password):
    try:
        connection = getMySQLConnection()
        if isinstance(connection, dict):
            return connection
        cursor = connection.cursor()
        cursor.execute(f"SELECT * FROM USERS")
        user = None
        for row in cursor:
            if (
                secret.__decrypt(row[0]) == email
                and secret.__decrypt(row[1]) == password
            ):
                user = {
                    "email": secret.__decrypt(row[0]),
                    "password": secret.__decrypt(row[1]),
                    "authority": secret.__decrypt(row[2]),
                    "tokens": row[3],
                    "maxTokens": row[4],
                    "tokenUpdate": row[5],
                    "nextTokenUpdateDays": row[6],
                    "sessionKey": secret.__decrypt(row[7]),
                }
                break
        if user is not None:
            return {"data": user}
        return MysqlErrors.userNotFoundError
    except:
        return MysqlErrors.unknownError


def loginWithSessionKey(sessionKey):
    try:
        connection = getMySQLConnection()
        cursor = connection.cursor()
        code = "SELECT * FROM USERS"
        cursor.execute(code)
        user = None
        for row in cursor:
            if secret.__decrypt(row[7]) == sessionKey:
                user = {
                    "email": secret.__decrypt(row[0]),
                    "password": secret.__decrypt(row[1]),
                    "authority": secret.__decrypt(row[2]),
                    "tokens": row[3],
                    "maxTokens": row[4],
                    "tokenUpdate": row[5],
                    "nextTokenUpdateDays": row[6],
                    "sessionKey": secret.__decrypt(row[7]),
                }
        if user is None:
            return MysqlErrors.userNotFoundError
        return {"data": user}
    except:
        pass


def register(
    email: str,
    password: str,
    authority: str,
    tokens: int,
    maxTokens: int,
    tokenUpdate: datetime,
    nextTokenUpdateDays: int,
):
    try:
        connection = getMySQLConnection()
        if isinstance(connection, dict):
            return connection
        cursor = connection.cursor()
        user = login(email, password)
        if isinstance(user, dict):
            if "data" in list(user.keys()):
                return MysqlErrors.userExists
        code = f"INSERT INTO USERS VALUES ('{database.__encrypt(email)}', '{database.__encrypt(password)}', '{database.__encrypt(authority.upper())}', {tokens}, {maxTokens}, '{tokenUpdate.strftime('%Y-%m-%d %H:%M:%S')}', {str(nextTokenUpdateDays)}, '{database.__encrypt(str(getRandomSessionKey()))}')"
        cursor.execute(code)
        connection.commit()
        user = login(email, password)
        if isinstance(user, dict):
            if "data" in list(user.keys()):
                return user
        return MysqlErrors.registerError

    except:
        return MysqlErrors.unknownError


def deleteAccount(email, password):
    try:
        connection = getMySQLConnection()
        if isinstance(connection, dict):
            return connection
        cursor = connection.cursor()
        dUser = login(email, password)
        if "error" in list(dUser.keys()):
            return MysqlErrors.userNotFoundError
        code = "SELECT EMAIL, PASSWORD, AUTHORITY FROM USERS"
        cursor.execute(code)
        user = {}
        for row in cursor:
            if (
                secret.__decrypt(row[0]) == email
                and secret.__decrypt(row[1]) == password
            ):
                user = {"email": row[0], "password": row[1], "authority": row[2]}
                break
        if user == {}:
            return MysqlErrors.userNotFoundError

        code = f"DELETE FROM USERS WHERE EMAIL = '{user['email']}' AND PASSWORD = '{user['password']}'"
        cursor.execute(code)
        connection.commit()
        if not userExist(email):
            return dUser
        return MysqlErrors.unknownError
    except:
        return MysqlErrors.unknownError


def userExist(email):
    try:
        connection = getMySQLConnection()
        if isinstance(connection, dict):
            return connection
        cursor = connection.cursor()
        cursor.execute(f"SELECT * FROM USERS")
        user = None
        for row in cursor:
            if secret.__decrypt(row[0]) == email:
                user = {
                    "email": secret.__decrypt(row[0]),
                    "password": secret.__decrypt(row[1]),
                    "authority": secret.__decrypt(row[2]),
                    "tokens": row[3],
                    "maxTokens": row[4],
                }
                break
        if user is not None:
            return True
        return False
    except:
        return False


def resetSessionKey(email, password):
    try:
        if "error" in list(login(email, password).keys()):
            return MysqlErrors.userNotFoundError
        connection = getMySQLConnection()
        cursor = connection.cursor()
        user = getUser(email, False)["data"]
        code = f"UPDATE USERS SET SESSIONKEY = '{database.__encrypt(str(getRandomSessionKey()))}' WHERE EMAIL = '{user['email']}' AND PASSWORD = '{user['password']}'"
        cursor.execute(code)
        connection.commit()
        return login(email, password)
    except:
        return MysqlErrors.unknownError


def resetPassword(email, password, newPassword):
    try:
        if "error" in list(login(email, password).keys()):
            return MysqlErrors.userNotFoundError
        connection = getMySQLConnection()
        cursor = connection.cursor()
        user = getUser(email, False)["data"]
        code = f"UPDATE USERS SET PASSWORD = '{database.__encrypt(str(newPassword))}' WHERE EMAIL = '{user['email']}' AND PASSWORD = '{user['password']}'"
        cursor.execute(code)
        connection.commit()
        resetSessionKey(email, newPassword)
        return login(email, newPassword)
    except:
        return MysqlErrors.unknownError


def checkTokens():
    try:
        connection = database.getMySQLConnection()
        if isinstance(connection, dict):
            return connection
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM USERS")
        for row in cursor:
            user = {
                "email": secret.__decrypt(row[0]),
                "password": secret.__decrypt(row[1]),
                "authority": secret.__decrypt(row[2]),
                "tokens": row[3],
                "maxTokens": row[4],
                "tokenUpdate": row[5],
                "nextTokenUpdateDays": row[6],
            }
            #datetime.datetime(2024, 6, 11, 18, 14, 12)
            if user["authority"] in ["ADMIN", "GRANDADMIN"]:
                setToken(user["email"], -1, -1, -1)
            elif (
                user["tokenUpdate"]
                + datetime.timedelta(days=user["nextTokenUpdateDays"])
                <= datetime.datetime.now()
            ):
                setToken(user["email"], user["maxTokens"], 3, 1000)

    except:
        pass


def getTokenCount(email: str):
    try:
        connection = getMySQLConnection()
        if isinstance(connection, dict):
            return connection
        cursor = connection.cursor()
        if not userExist(email):
            return MysqlErrors.userNotFoundError
        user = getUser(email, False)["data"]
        code = f"SELECT TOKENS, MAXTOKENS FROM USERS WHERE EMAIL = '{user['email']}'"
        cursor.execute(code)
        for row in cursor:
            return {"data": {"tokens": row[0], "maxTokens": row[1]}}
    except:
        return MysqlErrors.unknownError


def setToken(email: str, newTokens:int, nextTokenUpdateDays = None, newMaxTokens=None):
    try:
        if all([x is None for x in [nextTokenUpdateDays, newTokens, newMaxTokens]]):
            return MysqlErrors.valuesEmpty
        connection = getMySQLConnection()
        if isinstance(connection, dict):
            return connection
        cursor = connection.cursor()
        if not userExist(email):
            return MysqlErrors.userNotFoundError
        user = getUser(email, False)["data"]
        code = "UPDATE USERS SET "
        if nextTokenUpdateDays is not None:
            code += f"NEXTTOKENUPDATEDAYS = {str(nextTokenUpdateDays)},  TOKENUPDATE ='{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}', "
        code += f'TOKENS = {str(newTokens)}'
        if newMaxTokens is not None:
            code += f', MAXTOKENS = {str(newMaxTokens)}'
        code = code +f" WHERE EMAIL = '{user['email']}'"
        cursor.execute(code)
        connection.commit()
        return getUser(email)["data"]
    except:
        return MysqlErrors.unknownError
