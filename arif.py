from openai import OpenAI
import account, database
import myEnvironment, json


def talkToArif(talks, userData, model="gpt-3.5-turbo"):
    try:
        feePerChat = 10
        if not account.userExist(userData["email"]):
            return database.MysqlErrors.userNotFoundError
        user = account.login(userData["email"], userData["password"])
        if ["error"] in list(user.keys()):
            return database.MysqlErrors.userNotFoundError
        user = user["data"]
        if user["tokens"] == 0:
            return database.MysqlErrors.tokenError

        client = OpenAI(api_key=myEnvironment.apiKey)
        systemContent = ""
        with open("arifChat.txt", "r", encoding="utf-8") as f:
            systemContent = f.read()
        token = user["tokens"]
        messages = [
            {
                "role": "system",
                "content": systemContent + "\n Users Current point is: "+ str(token) + ", Amount of points deducted per message: "+str(feePerChat) + "Don't tell the user about points unless necessary",
            }
        ] + talks
        response = client.chat.completions.create(
            model=model,
            messages=messages,
        )
        if user["authority"] not in ["ADMIN", "GRANDADMIN"]:
            newToken = token - feePerChat
            newToken = 0 if newToken < 0 else newToken
            account.setToken(user["email"], newToken, None)
        return {"role": "assistant", "content": response.choices[0].message.content}
    except:
        return database.MysqlErrors.unknownError


def plan(availablePlans,userData, model="gpt-3.5-turbo"):
    try:
        feePerPlan = 50
        if not account.userExist(userData["email"]):
            return database.MysqlErrors.userNotFoundError
        user = account.login(userData["email"], userData["password"])
        if ["error"] in list(user.keys()):
            return database.MysqlErrors.userNotFoundError
        user = user["data"]
        if user["tokens"] == 0:
            return database.MysqlErrors.tokenError
        
        token = user["tokens"]
        availablePlansForAI = []
        for p in availablePlans:
            availablePlansForAI.append(
                {
                    "title": p["title"]["en"],
                    "subtitle": p["subtitle"]["en"],
                }
            )
        availablePlansForAI = str(availablePlansForAI)
        client = OpenAI(api_key=myEnvironment.apiKey)
        systemContent = ""
        with open("arifPlan.txt", "r", encoding="utf-8") as f:
            systemContent = f.read()
        messages = [
            {
                "role": "system",
                "content": systemContent,
            },
            {"role": "user", "content": availablePlansForAI},
        ]
        response = client.chat.completions.create(
            model=model,
            messages=messages,
        )
        patience = 0
        j = {"error": "Unknown error"}
        while patience <= 3:
            try:
                c = response.choices[patience].message.content.replace("\n", "")
                js = json.loads(c)
                if type(js) == dict:
                    j = js[list(js.keys())[0]]
                else:
                    j = js
                del js
            except:
                pass
            finally:
                patience += 1
            break
        if j == {"error": "Unknown error"}:
            return j
        for p in availablePlans:
            for i, aiP in enumerate(j.copy()):
                try:
                    if (
                        p["subtitle"]["en"] == aiP["subtitle"]
                        and p["title"]["en"] == aiP["title"]
                    ):
                        j[i]["subtitle"] = p["subtitle"]
                        j[i]["title"] = p["title"]
                        j[i]["imageUrl"] = p["imageUrl"]
                except KeyError:
                    pass
        if user["authority"] not in ["ADMIN", "GRANDADMIN"]:
            newToken = token - feePerPlan
            newToken = 0 if newToken < 0 else newToken
            account.setToken(user["email"], None, newToken)
        return j
    except:
        return {"error": "Unknown error"}
