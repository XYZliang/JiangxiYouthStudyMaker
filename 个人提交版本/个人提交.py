import json
import secrets

import requests
from anti_useragent import UserAgent

# 以下为所需的数据，注意引号别删了
# 必填 个人微信认证id，详见README
openId = ""
# False为否，不强制提交 True为是，强制提交，即使个人信息不完整，也继续提交
force_submit = True

def makeHeader(openid="",score=False,login=False):
    jsonInfo = {
        'requestType': 'http',
        'Accept-Language': 'zh-CN,zh-Hans;q=0.9',
        'Content-Type': 'application/json;charset=UTF-8',
        'User-Agent': UserAgent(platform="iphone").wechat,
        'Origin': 'http://www.jxqingtuan.cn',
        'Host': 'www.jxqingtuan.cn',
        'Accept-Encoding': 'gzip, deflate',
        'Authorization': '',
        'Accept': '*/*',
        'Connection': 'close',
    }
    if len(str(openid)) > 0:
        jsonInfo[
            "Referer"] = 'http://www.jxqingtuan.cn/html/?&accessToken=' + openid + '&openid=' + openid + '&requestType=http'
        jsonInfo["openid"] = openid
    if score:
        patch = {
            'Content-Type': 'application/x-www-form-urlencoded',  # 更新内容类型
        }
        # 应用补丁更新原始请求头字典
        jsonInfo.update(patch)
    return jsonInfo


def getIDInfo(openid):
    url = "http://www.jxqingtuan.cn/pub/pub/vol/member/info?accessToken=" + openid
    res = json.loads(requests.get(url, headers=makeHeader()).text)
    # print(res)
    if str(res.get("code")) == '200':
        return res.get("vo").get("areaid4"), res.get("vo").get("telphone"), res.get("vo").get("username"), res.get("vo").get("id")
    else:
        print("查询个人信息未知错误：" + res)
        exit()


def getCourse():
    courseUrl = "http://www.jxqingtuan.cn/pub/pub/vol/index/index?page=1&pageSize=10"
    rankUrl = "http://www.jxqingtuan.cn/pub/pub/vol/ranks/index?type=1&page=1&pageSize=10"
    CourseidJson = requests.get(courseUrl, headers=makeHeader(),timeout=5).json()
    RankJson = requests.get(rankUrl, headers=makeHeader(),timeout=5).json()
    Course = CourseidJson.get("vo")
    try:
        print("课程名称：" + RankJson.get("title"))
        return Course.get("classId"),RankJson.get("title"),Course.get("studyUrl")
    except:
        print("查询课程致未知错误")
        exit()


def getStudy(course, nid, subOrg, cardNo, openid=""):
    url = "http://www.jxqingtuan.cn/pub/pub/vol/volClass/join?accessToken=" + openid
    if len(subOrg) > 0:
        data = {"accessToken":openid,"course": course, "subOrg": subOrg, "nid": nid, "cardNo": cardNo}
    else:
        data = {"accessToken":openid,"course": course, "subOrg": None, "nid": nid, "cardNo": cardNo}
    res = json.loads(
        (requests.post(url=url, data=json.dumps(data, ensure_ascii=False).encode('utf-8'), headers=makeHeader())).text)
    if res.get("status") == 200:
        print(cardNo + "大学习成功！")
    else:
        print("提交大学习导致未知错误：" )
        print(res)

def getScore(openid,userId,url):
    url = "http://www.jxqingtuan.cn/pub/pub/vol/member/addScoreInfo"
    data = {"openid":openid,"userId":userId,"check":"1","title":"青年大学习","type":"3","url":"https://h5.cyol.com/special/daxuexi/flh9ab2wp5/m.html"}
    res = json.loads(
        (requests.post(url=url, data=json.dumps(data, ensure_ascii=False).encode('utf-8'), headers=makeHeader())).text)
    if res.get("status") == 200:
        print("积分添加成功！")
    else:
        print("积分添加失败：" + str(res))

def getScore(uid,openid,title="青年大学习",type="3",dataurl="https://h5.cyol.com/special/daxuexi/flh9ab2wp5/m.html",errorTime=0):
    url = "http://www.jxqingtuan.cn/pub/pub/vol/member/addScoreInfo"
    data = {"type":type,"openid":openid,"title":title,"userId":str(uid),"url":dataurl,"check":"1"}
    res = requests.post(url=url, data=data, headers=makeHeader(openid=openid,score=True),timeout=5)
    res = json.loads(res.text)
    if res.get("code") == 200:
        if res.get("success"):
            print("积分添加成功！")
        else:
            # print("提交"+openid+"分数失败，"+res)
            print("积分添加失败：" + str(res))
    elif res.get("code") == "-1":
        print("积分添加失败，可能是已经大学习过了：" + str(res))

if __name__ == '__main__':
    courseId,courseName,courseUrl = getCourse()
    pid, subOrg, cardNo, id = getIDInfo(openId)
    getStudy(courseId, id, subOrg, cardNo, openId)
    getScore(id,openId,courseUrl)
