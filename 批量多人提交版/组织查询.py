import json
import secrets

import requests
from anti_useragent import UserAgent

openid = ""

def makeHeader(openid):
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


def get_mes(pid):
    url = "http://www.jxqingtuan.cn/pub/pub/vol/config/organization?pid={pid}".format(pid=pid)
    payload = {}
    headers = {
        'Cookie': 'JSESSIONID=BUkb7Lsw0BWVR1oHYqKuBUVXme6ERuveELY4ohQA; JSESSIONID=V6Wm1rYYKt2ApKxkXkGdCGT8snY3pt-11q4sN6Mo',
        'User-Agent': 'Mozilla/5.0 (iPad; CPU OS 15_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.15(0x18000f20) NetType/WIFI Language/zh_CN',
        'X-Requested-With': 'XMLHttpRequest',
        'Host': 'osscache.vol.jxmfkj.com',
        'Content-Type': 'application/json;charset=UTF-8',
        'Referer': 'http://osscache.vol.jxmfkj.com/html/h5_index.html'
    }
    # response = requests.request("GET", url, headers=headers, data=payload)
    # print(url)
    response = json.loads((requests.get(url=url, data=json.dumps(payload), headers=makeHeader(openid))).text)
    # print(response)
    # response = json.loads(response.text)
    response = response["result"]
    response_len = len(response)
    k = {}
    num = []
    for i in response:
        tittle = i['title']
        id = i['id']
        k["{}".format(tittle)] = id
    num = list(k.values())
    return k, num


def id_getinfo():
    list_tittle = {
        "团省委机关": "N0017",
        "省直属单位团委": "N0016",
        "省属本科院校团委": "N0013",
        "非省属本科院校团委": "N0014",
        "高职专科院校团委": "N0015",
        "南昌市": "N0002",
        "九江市": "N0003",
        "景德镇市": "N0004",
        "萍乡市": "N0005",
        "新余市": "N0006",
        "鹰潭市": "N0007",
        "赣州市": "N0008",
        "宜春市": "N0009",
        "上饶市": "N0010",
        "吉安市": "N0011",
        "抚州市": "N0012"
    }
    # 第一级
    t = 0
    # 所选组织3
    organization = {
        "组织": [],
        "名称": "",
        "pid": ""
    }
    while (1):
        if t == 0:
            print("#################主菜单#################")
            organization = {
                "组织": [],
                "名称": "",
                "pid": ""
            }
            i = 0
            samp = list(list_tittle.values())
            # print("请输入相应序号！")
            for k in list_tittle:
                print(str(i + 1) + "." + str(k) + ":" + str(list_tittle[k]))
                i = i + 1
            while (1):
                t = int(input("请输入对应序号:"))
                if t < 0 or t > len(list_tittle):
                    print("序号非法，请重新填写，", end="")
                else:
                    break
            print("#################" + list(list_tittle.keys())[t - 1] + "#################")
            pid = samp[t - 1]
            organization["组织"].append(list(list_tittle.keys())[t - 1])
            organization["名称"] = list(list_tittle.keys())[t - 1]
            organization["pid"] = pid
        else:
            list1, num = get_mes(pid)
            i = 0
            if list1 == {}:
                print("查询成功,所选组织为：", end="")
                for i in organization["组织"]:
                    print(i, end="")
                    # 不是最后一个
                    if i != organization["组织"][-1]:
                        print("-->", end="")
                print("\n其pid为：" + str(organization["pid"]))
                exit()
            for k in list1:
                print(str(i + 1) + "." + str(k) + ":" + str(list1[k]))
                i = i + 1
            while (1):
                t = int(input("请输入对应序号(输入0返回主菜单):"))
                if t < 0 or t > len(list1):
                    print("序号非法，请重新填写，", end="")
                else:
                    break
            if t != 0:
                print("#################" + list(list1.keys())[t - 1] + "#################")
                pid = num[t - 1]
                organization["组织"].append(list(list1.keys())[t - 1])
                organization["名称"] = list(list1.keys())[t - 1]
                organization["pid"] = pid
            else:
                pass


if __name__ == '__main__':
    id_getinfo()
