import json
import secrets

import requests
from anti_useragent import UserAgent

# 以下为所需的数据，注意引号别删了
# 必填 个人微信认证id，详见README
openId = ""

def makeHeader(openid=""):
    jsonInfo = {
        'Accept': '*/*',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'zh-CN,zh-Hans;q=0.9',
        'Connection': 'close',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Cookie': 'JSESSIONID=' + secrets.token_urlsafe(40),
        'Host': 'www.jxqingtuan.cn',
        'Origin': 'http://www.jxqingtuan.cn',
        'Referer': 'http://www.jxqingtuan.cn/html?requestType=http',
        'User-Agent': UserAgent(platform="iphone").wechat
    }
    if len(openid)>0:
        jsonInfo["Referer"] = 'http://www.jxqingtuan.cn/html/?&accessToken=' + openid + '&openid=' + openid+'&requestType=http'
        jsonInfo["openid"] = openid



def getIDInfo(openid):
    url = "http://www.jxqingtuan.cn/pub/pub/vol/member/info?accessToken=" + openid
    res = json.loads(requests.get(url, headers=makeHeader()).text)
    # print(res)
    if str(res.get("code")) == '200':
        return res.get("vo").get("areaid4"),res.get("vo").get("telphone"),res.get("vo").get("username")
    else:
        print("查询个人信息未知错误：" + res)
        exit()


def getCourse():
    courseUrl = "http://www.jxqingtuan.cn/pub/pub/vol/index/index?page=1&pageSize=10"
    rankUrl = "http://www.jxqingtuan.cn/pub/pub/vol/ranks/index?type=1&page=1&pageSize=10"
    CourseidJson = requests.get(courseUrl, headers=makeHeader()).json()
    RankJson = requests.get(rankUrl, headers=makeHeader()).json()
    Course = CourseidJson.get("vo")
    try:
        print("课程名称：" + RankJson.get("title"))
        return Course.get("classId")
    except:
        print("查询课程致未知错误")
        exit()


def getStudy(course, nid, subOrg, cardNo,openid=""):
    url = "http://www.jxqingtuan.cn/pub/pub/vol/volClass/join?accessToken="+openid
    if len(subOrg) > 0:
        data = {"course": course, "subOrg": subOrg, "nid": nid, "cardNo": cardNo}
    else:
        data = {"course": course, "subOrg": None, "nid": nid, "cardNo": cardNo}
    res = json.loads(
        (requests.post(url=url, data=json.dumps(data, ensure_ascii=False).encode('utf-8'), headers=makeHeader())).text)
    if res.get("status") == 200:
        print(cardNo + "大学习成功！")
    else:
        print("提交大学习导致未知错误：" + res.text)


if __name__ == '__main__':
    pid , subOrg , cardNo = getIDInfo(openId)
    getStudy(getCourse(), pid, subOrg, cardNo, openId)