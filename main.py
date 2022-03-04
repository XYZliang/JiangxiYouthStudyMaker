import requests
import json
# 以下为所需的数据，注意引号别删了
# 必填 团委组织ID号，详见README
nid = "N00"
# 非必填，社区（村）/班级/单位（部门），详见README
subOrg = ""
# 必填 姓名/学号/工号
cardNo = ""


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
    url = "http://osscache.vol.jxmfkj.com/pub/vol/config/organization?pid=" + nid
    res = json.loads(requests.get(url).text)
    if res.get("status") == 200:
        return res.get("result")
    else:
        print("查询组织导致未知错误：" + res.text)
        exit()


def getCourse():
    url = "http://osscache.vol.jxmfkj.com/html/assets/js/course_data.js"
    # res = requests.get(url).text
    ress = 'var course_data = {"result":{"id":"1","title":"第十三季第四期","uri":"http://h5.cyol.com/special/daxuexi/cq2hkv2t8d/index.html"},"status":200}'
    CourseInfo = ress[18:]
    CourseJson = json.loads(CourseInfo)
    Course = CourseJson.get("result")
    try:
        if json.dumps(Course).count("id") == 1:
            return Course.get("id")
        else:
            return Course[-1].get("id")
    except:
        print("查询课程致未知错误")
        exit()


def getStudy(course, nid, subOrg, cardNo):
    url = "http://osscache.vol.jxmfkj.com/pub/vol/volClass/join?accessToken="
    if len(subOrg) > 0:
        data = {"course": course, "nid": nid, "cardNo": cardNo, "subOrg": subOrg}
    else:
        data = {"course": course, "nid": nid, "cardNo": cardNo}
    res = json.loads((requests.post(url=url, data=json.dumps(data))).text)
    if res.get("status") == 200:
        print(cardNo+"大学习成功！")
    else:
        print("提交大学习导致未知错误：" + res.text)


if __name__ == '__main__':
    checkConfig()
    getStudy(getCourse(), nid, subOrg, cardNo)
