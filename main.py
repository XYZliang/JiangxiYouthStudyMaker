import json
import secrets
import requests
from anti_useragent import UserAgent

# 以下为所需的数据，注意引号别删了
# 必填 团委组织ID号，详见README
nid = "N00...."
# 非必填，社区（村）/班级/单位（部门），详见README
subOrg = ""
# 必填 姓名/学号/工号
cardNo = "...."
# 非必填 如果你会抓包,那就填上你的openid保险
openId = ""


def makeHeader(openid=openId):
    return {
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'zh-CN,zh-Hans;q=0.9',
        'Connection': 'close',
        'Content-Type': 'application/json;charset=UTF-8',
        'Cookie': 'JSESSIONID=' + secrets.token_urlsafe(40),
        'Host': 'www.jxqingtuan.cn',
        'Origin': 'http://www.jxqingtuan.cn',
        'Referer': 'http://www.jxqingtuan.cn/html/h5_index.html?&accessToken=' + openid,
        'User-Agent': UserAgent(platform="iphone").wechat,
        'X-Requested-With': 'XMLHttpRequest'
    }


def checkConfig():
    if len(cardNo) == 0:
        print("cardNo对应第五行数据，不可为空")
        exit()
    if len(nid) == 0:
        print("cardNo是团委组织ID，不可为空")
        exit()
    # info = json.dumps(getIDInfo())
    res = getIDInfo()
    if len(res) != 0:
        print("团委组织id异常，您似乎获取错了")


def getIDInfo():
    url = "http://www.jxqingtuan.cn/pub/vol/config/organization?pid=" + nid
    res = json.loads(requests.get(url, headers=makeHeader()).text)
    if res.get("status") == 200:
        return res.get("result")
    else:
        print("查询组织导致未知错误：" + res.text)
        exit()


def getCourse():
    url = "http://www.jxqingtuan.cn/pub/vol/volClass/current"
    CourseJson = requests.get(url, headers=makeHeader()).json()
    Course = CourseJson.get("result")
    try:
        print("课程id：" + Course.get("id"))
        print("课程名称：" + Course.get("title"))
        return Course.get("id")
    except:
        print("查询课程致未知错误")
        exit()


def getStudy(course, nid, subOrg, cardNo):
    url = "http://www.jxqingtuan.cn/pub/vol/volClass/join?accessToken="
    if len(subOrg) > 0:
        data = {"course": course, "nid": nid, "cardNo": cardNo, "subOrg": subOrg}
    else:
        data = {"course": course, "nid": nid, "cardNo": cardNo}
    res = json.loads((requests.post(url=url, data=json.dumps(data), headers=makeHeader())).text)
    if res.get("status") == 200:
        print(cardNo + "大学习成功！")
    else:
        print("提交大学习导致未知错误：" + res.text)


if __name__ == '__main__':
    checkConfig()
    getStudy(getCourse(), nid, subOrg, cardNo)
