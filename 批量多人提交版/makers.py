import random
from json import JSONDecodeError

import requests
import json
import xlrd
import time
from tqdm import tqdm

# 是否包含subOrg参数，即是否为三级团组织，详见README，默认为否，即四级团组织
need_subOrg = False
# 随机暂停提交秒数 0 为不暂停
stop = 1.0


def getCourse():
    url = "http://osscache.vol.jxmfkj.com/pub/vol/volClass/current"
    CourseJson = requests.get(url).json()
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
    if need_subOrg:
        data = {"course": course, "nid": nid, "cardNo": cardNo, "subOrg": subOrg}
    else:
        data = {"course": course, "nid": nid, "cardNo": cardNo}
    try:
        res = json.loads((requests.post(url=url, data=json.dumps(data))).text)
        if res.get("status") == 200:
            # print(cardNo + "大学习成功！")
            return
        else:
            print(cardNo + "提交大学习失败错误：" + res.text)
    except JSONDecodeError:
        print(cardNo + "提交大学习导致严重未知错误：" + res.text)


if __name__ == '__main__':
    Course = getCourse()
    data = xlrd.open_workbook(r'Data.xlsx')
    dataSheets = data.sheets()[0]
    row = dataSheets.nrows
    print("开始批量提交!")
    for i in tqdm(range(1, row)):
        rowData = dataSheets.row_values(i)
        studyData = []
        for a, b in enumerate(rowData):
            studyData.append(b)
        if need_subOrg:
            getStudy(Course, studyData[2], studyData[1], studyData[0])
        else:
            getStudy(Course, studyData[2], "", studyData[0])
        time.sleep(random.uniform(0, stop))
    print("批量提交完毕!")