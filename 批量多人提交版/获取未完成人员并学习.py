import configparser
import random
import time

import pandas as pd
from pathlib import Path
import datetime
import json
import secrets

import requests
from anti_useragent import UserAgent
import requests
from tqdm import tqdm

from 批量获取历史数据 import getLeanHistory, login, load_session_from_file

# 创建配置解析器并读取ini文件
config = configparser.ConfigParser()
config.read('config.ini', encoding='utf-8')

# 读取[setting]下的配置
nid = config.get('setting', 'nid')
export_unlearned = config.getboolean('setting', 'export_unlearned')
delay = config.getint('setting', 'delay')
max_retry = config.getint('setting', 'max_retry')
force_submit = config.getboolean('setting', 'force_submit')
only_unlearned = config.getboolean('setting', 'only_unlearned')

# 读取[management background]下的配置
username = config.get('management background', 'username')
password = config.get('management background', 'password')
# 转为字符串
password = str(password)
host = config.get('management background', 'host')
protocol = config.get('management background', 'protocol')

requests.adapters.DEFAULT_RETRIES = max_retry

# 个人信息
infoJsonList = []

def read_excel_files(directory,his=False):
    folder_path = Path(directory)
    if not folder_path.exists():
        raise FileNotFoundError(f"没有找到'{directory}'目录")

    excel_files = list(folder_path.glob('*.xlsx'))

    if not excel_files:
        raise FileNotFoundError("没有找到任何Excel文件")

    dfs = []
    for file in excel_files:
        df = pd.read_excel(file,engine='openpyxl')
        required_columns = ['姓名', '团支部']
        if his:
            required_columns = ['姓名(username)', '四级组织(lev4)']
        if not all(column in df.columns for column in required_columns):
            raise ValueError(f"文件：{file}缺少必要的列：{required_columns}")
        df['source_file'] = file  # 保存文件名，以便之后跟踪
        df.reset_index(inplace=True)  # 创建新的索引列
        dfs.append(df)

    return dfs


def combine_dfs(dfs, required_columns=['姓名', '团支部']):
    combined_df = pd.concat(dfs, ignore_index=True)
    reduced_df = combined_df[required_columns + ['source_file', 'index']]  # 保留原文件名和索引以便跟踪
    return reduced_df


def check_lev4_existence(study_df, history_df):
    if not set(study_df['团支部']).issubset(set(history_df['四级组织(lev4)'])):
        missing = set(study_df['团支部']) - set(history_df['四级组织(lev4)'])
        raise ValueError(f"以下团支部不存在于历史记录中: {missing}")


def find_unstudied_students(study_df, last_data_df, history_df):
    merged_df = pd.merge(study_df, last_data_df, left_on='姓名', right_on='username', how='left')
    no_study_df = merged_df[merged_df['username'].isnull()]
    return no_study_df[['姓名', '团支部']]

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
    if len(openid) > 0:
        jsonInfo[
            "Referer"] = 'http://www.jxqingtuan.cn/html/?&accessToken=' + openid + '&openid=' + openid + '&requestType=http'
        jsonInfo["openid"] = openid
    if score:
        patch = {
            'Content-Type': 'application/x-www-form-urlencoded',  # 更新内容类型
        }
        # 应用补丁更新原始请求头字典
        jsonInfo.update(patch)
    # if login:
    #     jsonInfo["Referer"] = protocol + "://" + host + "/html/h5_index.html"
    #     jsonInfo["Origin"] =  protocol + "://" + host
    #     jsonInfo["Host"] = host
    #     jsonInfo["Accept"] = 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7'
    #     jsonInfo["Accept-Language"] = 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6'
    #     jsonInfo["Content-Type"] = 'application/x-www-form-urlencoded'
    #     jsonInfo["Upgrade-Insecure-Requests"] = '1'
    #     jsonInfo["User-Agent"] = UserAgent(platform="windows")
    return jsonInfo

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

def getLastLeanHistory(course):
    print("尝试登录后台....")
    loginSession = login(username, password, False)
    # loginSession = load_session_from_file('session.pkl')
    lastJsonData = getLeanHistory(loginSession,nid,[course],limit=1)
    # print(lastJsonData)
    # 转为df
    lastJsonData = pd.DataFrame(lastJsonData)
    return lastJsonData

def getPeopleInfo(openid,save=True,errorTime=0):
    if errorTime > max_retry:
        print("查询"+openid+"个人信息失败次数过多,暂时跳过")
        return "系统多次获取错误"
    try:
        url = "http://www.jxqingtuan.cn/pub/pub/vol/member/info?accessToken=" + openid
        res = json.loads(requests.get(url, headers=makeHeader(),timeout=5).text)
        if str(res.get("code")) == '200' and res.get("state") == 'ok':
            if save:
                # 写入infoJsonList
                infoJsonList.append(res.get("vo"))
            return res.get("vo")
        elif str(res.get("code")) == '-1' and res.get("error") == True:
            return res.get("msg")
        else:
            return getPeopleInfo(openid,save,errorTime+1)
    except Exception as e:
        return getPeopleInfo(openid,save,errorTime+1)

def getStudy(course, nid, subOrg, cardNo, openid="",errorTime=0):
    if errorTime > max_retry:
        print("提交"+cardNo+"大学习失败次数过多,暂时跳过")
        return False
    try:
        url = "http://www.jxqingtuan.cn/pub/pub/vol/volClass/join?accessToken=" + openid
        if not subOrg:
            data = {"accessToken":openid,"course": course, "subOrg": subOrg, "nid": nid, "cardNo": cardNo}
        else:
            data = {"accessToken":openid,"course": course, "subOrg": None, "nid": nid, "cardNo": cardNo}
        res = json.loads(
            (requests.post(url=url, data=json.dumps(data, ensure_ascii=False).encode('utf-8'), headers=makeHeader(openid=openid),timeout=5)).text)
        if res.get("status") != 200:
            getStudy(course, nid, subOrg, cardNo, openid, errorTime + 1)
        if  res.get("result") == cardNo:
            return True
        else:
            return False
    except:
        return getStudy(course, nid, subOrg, cardNo, openid,errorTime+1)

def getScore(uid,openid,title="青年大学习",type="3",dataurl="https://h5.cyol.com/special/daxuexi/flh9ab2wp5/m.html",errorTime=0):
    if errorTime > max_retry:
        print("提交"+openid+"分数失败次数过多,暂时跳过")
        return False
    url = "http://www.jxqingtuan.cn/pub/pub/vol/member/addScoreInfo"
    data = {"type":type,"openid":openid,"title":title,"userId":str(uid),"url":dataurl,"check":"1"}
    # print(data)
    try:
        res = json.loads(
            (requests.post(url=url, data=data, headers=makeHeader(openid=openid,score=True),timeout=5)).text)
        # print(res)
    except:
        return getScore(uid,openid,title,type,url,errorTime+1)
    if res.get("code") == 200:
        if res.get("success"):
            return True
        else:
            # print("提交"+openid+"分数失败，"+res)
            return res
    elif res.get("code") == -1:
        return getScore(uid,openid,title,type,url,errorTime+1)

def makeDelay(delay):
    if delay > 0:
        delayTime = random.uniform(0, delay)
        time.sleep(delayTime)

def getStudys(course,courseUrl,infoList):
    if course == None:
        print("获取课程失败")
        exit()
    pbar = tqdm(range(len(infoList)))
    pbar.desc = "正在开始提交大学习"
    for infoid in pbar:
        openid = infoList[infoid]['openid']
        pbar.desc = "正在获取" + openid + "信息"
        info = getPeopleInfo(openid)
        # 检查是否是词典
        if not isinstance(info,dict):
            # 写入infoList完成情况和错误信息（如果有）
            infoList[infoid]['完成情况'] = "失败"
            infoList[infoid]['错误信息'] = "获取用户资料未知错误："+str(info)
            # print("ERROR1查询" + str(openid) + "失败，" + str(info) + "跳过")
            continue
        if "username" in info.keys():
            try:
                pbar.desc = "正在为"+info.get("username")+"提交大学习"
                nnid = info.get("areaid4")
                if nnid == None or len(nnid) == 0:
                    nnid = info.get("areaid3")
            except:
                nnid = info.get("areaid3")
            # print(course, nnid, info.get("telphone"), info.get("username"), openid)
            studyStatus = getStudy(course, nnid, info.get("telphone"), info.get("username"), openid)
            scoreStatus = getScore(info.get("id"),openid,dataurl=courseUrl)
            if studyStatus is True:
                infoList[infoid]['完成情况'] = "成功"
                infoList[infoid]['错误信息'] = ""
            else:
                infoList[infoid]['完成情况'] = "失败"
                infoList[infoid]['错误信息'] = "大学习发生未知错误："+str(scoreStatus)
            # scoreStatus = getScore()
        else:
            pbar.desc = "正在为" + info.get("id") + "提交大学习"
            if force_submit:
                studyStatus = getStudy(course, infoList[infoid]["nid"], None,infoList[infoid]["name"], openid)
                scoreStatus = getScore(info.get("id"), openid,dataurl=courseUrl)
                if studyStatus is True:
                    infoList[infoid]['完成情况'] = "成功"
                    infoList[infoid]['错误信息'] = "注意：用户个人资料不全，已强制提交"
                else:
                    infoList[infoid]['完成情况'] = "失败"
                    infoList[infoid]['错误信息'] = "用户个人资料不全，已强制提交，但大学习发生未知错误：" + str(scoreStatus)
            else:
                infoList[infoid]['完成情况'] = "失败"
                infoList[infoid]['错误信息'] = "用户个人资料不全："+str(info)
            # print("ERROR2查询" + str(openid) + "失败，" + str(info) + "跳过")
        makeDelay(delay)
    return infoList

def main():
    print("开始检查数据...")
    # 步骤1和2
    study_dfs = read_excel_files('./需要学习的名单')
    study_list_df = combine_dfs(study_dfs)

    # 步骤3
    history_dfs = read_excel_files('./历史学习数据',True)
    historical_data_df = pd.concat(history_dfs, ignore_index=True)

    # 步骤4
    check_lev4_existence(study_list_df, historical_data_df)
    # 步骤5
    print("开始获取课程...")
    course,courseName,courseUrl = getCourse()
    # 步骤6
    result_list = []
    if only_unlearned:
        print("开始获取未完成名单...")
        last_data_df = getLastLeanHistory(course)
        file_name = f"./本期已学习情况/{courseName}大学习完成名单-{datetime.datetime.now().strftime('%Y-%m-%d %H-%M-%S')}.xlsx"
        last_data_df.to_excel(file_name, index=False)
        # debug
        # 读取文件到df
        # file_name = "./本期已学习情况/2023年第19期大学习完成名单-2023-10-29 20:28:32.xlsx"
        # last_data_df = pd.read_excel(file_name,engine='openpyxl')
        no_study_df = find_unstudied_students(study_list_df, last_data_df, historical_data_df)
        file_name = f"./未完成情况/{courseName}大学习未完成名单-{datetime.datetime.now().strftime('%Y-%m-%d %H-%M-%S')}.xlsx"
        if export_unlearned:
            no_study_df.to_excel(file_name, index=False)

        # 遍历没有学习记录的DataFrame
        for _, row in no_study_df.iterrows():
            # 查找历史数据中匹配的记录
            matching_records = historical_data_df.loc[
                (historical_data_df['姓名(username)'] == row['姓名']) &
                (historical_data_df['四级组织(lev4)'] == row['团支部'])
                ]

            # 对于找到的每条记录，提取所需信息并构建一个字典
            for _, record in matching_records.iterrows():
                user_data = {
                    'openid': record['openid(userid)'],
                    'name': record['姓名(username)'],
                    'nid': record['四级组织号(nid)'],
                }

                # 打印或进行其他处理，以便验证
                # print(user_data)

                # 将构建的字典添加到结果列表中
                result_list.append(user_data)
    else:
    # history_dfs 仅保留'openid(userid)' '四级组织(lev4)' '姓名(username)' '四级组织号(nid)'
        result_list = [df[['openid(userid)', '姓名(username)', '四级组织号(nid)']] for df in history_dfs]
    # 重命名列
        result_list = [df.rename(columns={'openid(userid)': 'openid', '姓名(username)': 'name', '四级组织号(nid)': 'nid'}) for df in result_list]
    # 合并df
        result_list = pd.concat(result_list, ignore_index=True)
    # 转为list
        result_list = result_list.to_dict('records')

    # 打乱result_list
    random.shuffle(result_list)

    # # 取前15条测试
    # result_list = result_list[:15]

    if result_list:
        result_list = getStudys(course,courseUrl,result_list)

    # 导出自动学习情况 result_list
    # 删除openid列
    for i in result_list:
        i.pop('openid')
    file_name = f"./自动学习情况/{courseName}大学习自动学习名单-{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.xlsx"
    pd.DataFrame(result_list).to_excel(file_name, index=False)

    print(f"输出文件已保存为 {file_name}")


# 确保您安装了所需的库，比如 pandas，然后运行脚本
if __name__ == "__main__":
    main()
