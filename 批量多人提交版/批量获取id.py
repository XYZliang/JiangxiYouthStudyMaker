import io
import json
import pickle
import re
from datetime import datetime

import ddddocr
import imageio
import js2py
from PIL import Image
from anti_useragent import UserAgent
from bs4 import BeautifulSoup
from tqdm import tqdm
import pandas as pd
from openpyxl import load_workbook

# 账号
username = ""
# 密码
password = ""
# 需要获取的所有人员所在的组织id
nid = ""
# 从近多少期大学习中查询id
limit = 10
# 加密秘钥
public_exponent = "10001"
modulus = "dff46645b6337855b0c1f9812a1a943904f2abd5f2f339f0f3b7f81cdb169eab00da0321a0075ef1d9e12d2af4d168b16d0f3ded064f8bcb97ca2af891eb73a0b55a2990b62fffc0cee0e61efcf5ec6247c8eb4a1f4df6d2ac42d930407c52c6e8cd07f6babf109c50428c3d8f1a64a66950178197136ee19b04b2bdf6dcb3df"

headers = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Encoding": "gzip, deflate",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
    "Cache-Control": "max-age=0",
    "Content-Type": "application/x-www-form-urlencoded",
    "Host": "106.225.141.143:8103",
    "Origin": "http://106.225.141.143:8103",
    "Referer": "http://106.225.141.143:8103",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": UserAgent(platform="windows").chrome
}

# 计算邻域非白色个数
def calculate_noise_count(img_obj, w, h):
    """
    计算邻域非白色的个数
    Args:
        img_obj: img obj
        w: width
        h: height
    Returns:
        count (int)
    """
    count = 0
    width, height, s = img_obj.shape
    for _w_ in [w - 1, w, w + 1]:
        for _h_ in [h - 1, h, h + 1]:
            if _w_ > width - 1:
                continue
            if _h_ > height - 1:
                continue
            if _w_ == w and _h_ == h:
                continue
            if (img_obj[_w_, _h_, 0] < 233) or (img_obj[_w_, _h_, 1] < 233) or (img_obj[_w_, _h_, 2] < 233):
                count += 1
    return count


# k邻域降噪
def operate_img(img, k):
    w, h, s = img.shape
    # 从高度开始遍历
    for _w in range(w):
        # 遍历宽度
        for _h in range(h):
            if _h != 0 and _w != 0 and _w < w - 1 and _h < h - 1:
                if calculate_noise_count(img, _w, _h) < k:
                    img.itemset((_w, _h, 0), 255)
                    img.itemset((_w, _h, 1), 255)
                    img.itemset((_w, _h, 2), 255)
    return img


# 将 bytes 转为 Image
def bytes_to_image(img_bytes):
    return Image.open(io.BytesIO(img_bytes))


# 将 Image 转为 bytes
def image_to_bytes(img, format='JPEG'):
    with io.BytesIO() as output:
        img.save(output, format=format)
        return output.getvalue()


# 识别verify.jpg验证码中的文字
def get_verify_code(img, return_ocr_result=False):
    print("识别验证码中")
    ocr = ddddocr.DdddOcr()
    # 使用imageio替代cv2，从bytes读取图像得到numpy.ndarray
    img_array = imageio.imread(io.BytesIO(img))
    img_array = operate_img(img_array, 1)
    # 使用imageio将numpy.ndarray保存为bytes
    img_bytes_io = io.BytesIO()
    imageio.imwrite(img_bytes_io, img_array, format='JPEG')
    img_bytes = img_bytes_io.getvalue()
    verify_code = ocr.classification(img_bytes)

    # 检测verify_code是否包含大于等于3个数字
    numbers = re.findall(r'\d', verify_code)
    if len(numbers) >= 3:
        result = str(int(numbers[0]) - int(numbers[2]))
        verify_code = str(int(numbers[0])) + "-" + str(int(numbers[2]))

    # 检测verify_code是否只有1个数字
    elif len(numbers) == 1:
        result = numbers[0]
        verify_code = numbers[0]

    else:
        verify_code3 = verify_code[:3]

        # 取verify_code的前三位字符为verify_code3，检测其是否只有1个数字
        numbers3 = re.findall(r'\d', verify_code3)
        if len(numbers3) == 1:
            result = numbers3[0]
            verify_code = numbers3[0]

        # 对于verify_code3，是否只有3个数字
        elif len(numbers3) == 3:
            result = str(int(numbers3[0]) - int(numbers3[2]))
            verify_code = str(int(numbers3[0])) + "-" + str(int(numbers3[2]))

        # 检测verify_code3是否包含x或者+
        elif 'x' in verify_code3 or '+' in verify_code3:
            result = str(sum(map(int, numbers3)))
            verify_code = str(int(numbers3[0])) + "+" + str(int(numbers3[1]))

        # 检测verify_code3是否包含-
        elif '-' in verify_code3:
            result = str(int(numbers3[0]) - int(numbers3[1]))
            verify_code = str(int(numbers3[0])) + "-" + str(int(numbers3[1]))


        # 对于verify_code3，是否只有2个数字
        elif len(numbers3) == 2:
            result = str(int(numbers3[0]) - int(numbers3[1]))
            verify_code = str(int(numbers3[0])) + "-" + str(int(numbers3[1]))

        # 其他情况
        else:
            result = '0'
            verify_code = 'error,try 0'

    print(f"验证码识别结果为：{verify_code}={result}")
    if return_ocr_result:
        return f"{verify_code}={result}"
    else:
        return result


def encrypt_with_js2py(password):
    print("使用js2py执行加密，这可能需要几秒钟")
    # 加载外部的JavaScript文件
    with open("rsa/Barrett.js", "r") as f:
        barrett_js = f.read()

    with open("rsa/BigInt.js", "r") as f:
        bigint_js = f.read()

    with open("rsa/RSA_Stripped.js", "r") as f:
        rsa_js = f.read()

    # 定义RSA加密的JavaScript代码
    encrypt_js = """
    function encrypt(password) {
        setMaxDigits(130);
        var key = new RSAKeyPair("10001", "", "dff46645b6337855b0c1f9812a1a943904f2abd5f2f339f0f3b7f81cdb169eab00da0321a0075ef1d9e12d2af4d168b16d0f3ded064f8bcb97ca2af891eb73a0b55a2990b62fffc0cee0e61efcf5ec6247c8eb4a1f4df6d2ac42d930407c52c6e8cd07f6babf109c50428c3d8f1a64a66950178197136ee19b04b2bdf6dcb3df");
        return encryptedString(key, encodeURIComponent(password));
    }
    """

    # 使用js2py执行JavaScript代码
    context = js2py.EvalJs()
    context.execute(barrett_js + bigint_js + rsa_js + encrypt_js)

    # 使用JavaScript函数进行加密
    encrypted_password = context.encrypt(password)
    return encrypted_password


def test_fetch_and_save_captcha():
    base_url = "http://106.225.141.143:8103/pub/verify?t="
    current_time = datetime.now().time().strftime('%Y-%M-%S')
    captcha_url = base_url + current_time

    response = requests.get(captcha_url)
    if response.status_code == 200:
        captcha_result = get_verify_code(response.content, True)
        with open(f"{captcha_result}.png", "wb") as f:
            f.write(response.content)
        print(f"Captcha saved as {captcha_result}.png with result: {captcha_result}")
        return captcha_result
    else:
        print(f"Failed to fetch captcha. Status code: {response.status_code}")
        return None


def login(userCode, password, showCookie=False):
    session = requests.Session()

    # 1. 请求登录页面获取JSESSIONID和_jfinal_token
    response = session.get("http://106.225.141.143:8103/pub/login", headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    jfinal_token = soup.find('input', {'id': '_jfinal_token'})['value']

    for _ in range(1):  # 尝试3次
        # 2. 获取验证码图片
        t = datetime.now().time().strftime('%Y-%M-%S')
        response = session.get(f"http://106.225.141.143:8103/pub/verify?t={t}", headers=headers)
        verify_code = get_verify_code(response.content)

        # 3. 提交登录请求
        data = {
            "userCode": userCode,
            "password": encrypt_with_js2py(password),
            "verifyCode": verify_code,
            "_jfinal_token": jfinal_token  # 添加_jfinal_token到POST数据中
        }
        session.post("http://106.225.141.143:8103/pub/login/submit?returnUrl=", data=data, headers=headers)

        # 4. 验证是否登录成功
        response = session.get("http://106.225.141.143:8103/")
        content = response.text
        # print(content)
        if "用户不存在" in content or "帐号或密码错误" in content:
            print("用户传入的账户密码有误")
            return None
        elif "验证码错误，请重新输入" in content:
            continue
        elif "网站后台管理" in content:
            print("登录成功!!!!!!!!!!!!")
            if showCookie:
                print("Cookies:", session.cookies)
                save_session_to_file(session, 'session.pkl')
            return session
    print("登录失败")
    return None


def save_session_to_file(session, filename):
    with open(filename, 'wb') as f:
        pickle.dump(session, f)


def load_session_from_file(filename):
    with open(filename, 'rb') as f:
        return pickle.load(f)

def getRoot(session):
    # 获取响应html源代码
    response = session.get("http://106.225.141.143:8103/portal/vol/sysOrg",headers=headers)
    content = response.text
    match = re.search(r'var rootId\s*=\s*"([^"]+)"', content)
    if match:
        root_id = match.group(1)
        return root_id
    else:
        print("rootId not found")
        exit()

def getSelfInfo(session, id):
    response = session.get("http://106.225.141.143:8103/portal/vol/sysOrg/findSelf?id="+id,headers=headers)
    content = response.text
    # 加载json
    json_data = json.loads(content)['data']
    # "chief": "N001300041012",
    #             "descript": "DE4AB8BA-383C-48DC-B962-9A04531FC831",
    #             "id": "N001300041012",
    #             "isstop": 1,
    #             "lev": 4,
    #             "memberCnt": 2398,
    #             "orgCode": "N001300041012",
    #             "orgName": "软件与物联网工程学院团委",
    #             "parentid": "N00130004",
    #             "parentidName": "江西财经大学团委"
    if (len(json_data)==1):
        json_data = json_data[0]
        memberCnt = json_data['memberCnt']
        orgName = json_data['orgName']
        parentidName = json_data['parentidName']
        parentid = json_data['parentid']
        return memberCnt,orgName,parentidName,parentid
    else:
        return json_data

def getSonInfoList(session, id):
    response = session.get("http://106.225.141.143:8103/portal/vol/sysOrg/find?id="+id,headers=headers)
    content = response.text
    # 加载json
    json_data = json.loads(content)['data']
    return json_data

def showMenu(session,memberCnt,orgName,parentidName,parentid,selfID):
    print("###################欢迎" + orgName + "###################")
    print("组织人数：" + str(memberCnt))
    print("上级组织：" + parentidName)
    print("###################请选择操作###################")
    print("0.退出程序")
    print("1.获取当前组织下所有人员id（推荐，默认）")
    print("2.获取当前组织的某个直接下级组织的所有人员id")
    print("3.获取当前组织的直接上级组织的所有人员id并保存到文件（谨慎）")
    print("4.自定义获取某个组织的所有人员id（谨慎）")
    print("请输入数字（0-4）：")
    menuID = str(input())
    needID = selfID
    # 如果输入不合法
    while menuID != '0' and menuID != '1' and menuID != '2' and menuID != '3':
        print("输入不合法，请重新输入：")
        menuID = input()
    if menuID == '0':
        exit()
    if menuID == '2':
        sonList = getSonInfoList(session, selfID)
        print("###################请选择下级组织###################")
        for i in range(len(sonList)):
            print(str(i) + "." + sonList[i]['orgName'])
        print("请输入数字（0-" + str(len(sonList) - 1) + "）：")
        sonID = str(input())
        # 如果输入不合法
        while sonID < '0' or sonID > str(len(sonList) - 1):
            print("输入不合法，请重新输入：")
            sonID = input()
        sonID = sonList[sonID]['id']
    elif menuID == '3':
        needID = parentid
    elif menuID == '4':
        print("请输入组织id，包含开头的字符N：")
        needID = input()
    print("###################开始获取"+needID+"的所有人员id###################")
    return needID

def getCourseList(session):
    response = session.get("http://106.225.141.143:8103/portal/vol/jxgqtClassRecord/index",headers=headers)
    content = response.text
    soup = BeautifulSoup(content, 'html.parser')
    # 找到ID为'classId'的select元素
    select_elem = soup.find('select', id='classId')
    # 提取所有option元素
    options = select_elem.find_all('option')
    # 构建字典，将option的文本作为key，value属性作为值
    result_dict = {option.text: option['value'] for option in options}
    return result_dict


import requests
import json
import math


def getOneLeanHistory(session, courseID, nid, page=1, pageSize=20):
    params = {
        "iclassId": courseID,
        "inid": nid,
        "pageNumber": page,
        "pageSize": pageSize
    }
    response = session.get("http://106.225.141.143:8103/portal/vol/jxgqtClassRecord/list", params=params)
    json_data = json.loads(response.text)
    return json_data


def getLeanHistory(session,orgName, nid, courseList, limit=None):
    all_data = []
    time = 0
    for course in courseList:
        courseID = courseList[course]
        if limit!=None:
            if time>=limit:
                break
        time = time + 1
        # 首先使用默认的参数
        initial_data = getOneLeanHistory(session, courseID, nid)
        total_count = initial_data.get('totalCount', 0)

        # 根据总数计算请求次数
        total_pages = math.ceil(total_count / 90)

        # 如果总数大于20，我们需要更多的请求，从page=1开始，因为我们已经有了第一页的数据
        if total_count > 20:
            # all_data.extend(initial_data.get('list', []))
            for page in tqdm(range(1, total_pages + 1),desc="正在获取"+str(orgName)+"的"+str(course)+"课程的"+str(total_count)+"条历史学习记录"):
                page_data = getOneLeanHistory(session, courseID, nid, page=page, pageSize=90)
                all_data.extend(page_data.get('list', []))
        else:
            print("正在获取"+str(orgName)+"的"+str(course)+"课程的"+str(total_count)+"条历史学习记录")
            all_data.extend(initial_data.get('list', []))

    return all_data

def save_to_excel(data, filename="output.xlsx"):
    # 如果不是pd
    if type(data) != pd.DataFrame:
        data = pd.DataFrame(data)
    data.to_excel(filename, index=False)


# 假设 df 是已经处理过的 DataFrame
def save_splits_to_excel(df, col_width=30):
    # 使用 groupby 对四级组织(lev4) 进行拆分
    grouped = df.groupby('四级组织(lev4)', dropna=False)

    for name, group in grouped:
        # 如果name是NaN（表示此列为空），则设置为"未知"
        if pd.isna(name):
            filename = "./id数据/未知.xlsx"
        else:
            filename = f"./id数据/{name}.xlsx"

        # 使用pandas保存DataFrame到Excel
        group.to_excel(filename, index=False, engine='openpyxl')

        # 使用openpyxl加载Excel文件
        book = load_workbook(filename)
        worksheet = book.active

        for column in worksheet.columns:
            max_length = 0
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(cell.value)
                except:
                    pass
            adjusted_width = (max_length + 2)
            worksheet.column_dimensions[cell.column_letter].width = adjusted_width

        book.save(filename)


def processDF(data):
    df = pd.DataFrame(data)
    # 根据addtime排序，确保最新的时间在前
    df = df.sort_values(by="addtime", ascending=False)
    # 仅考虑'username'和'subOrg'字段，保留第一个（最新的）重复项
    df = df.drop_duplicates(subset=['username'], keep='first')
    # 丢弃'score'和'id'列
    df = df.drop(columns=['score', 'id'])
    # 根据指定的顺序对列进行排序
    columns_order = ['username', 'subOrg', 'addtime', 'lev1', 'nid1', 'lev2', 'nid2', 'lev3', 'nid3', 'lev4', 'nid',
                     'classId', 'userid']
    df = df[columns_order]
    # 重命名列
    new_columns_names = {
        'username': '姓名(username)',
        'subOrg': '所属组织(subOrg)',
        'addtime': '记录时间(addtime)',
        'lev1': '一级组织(lev1)',
        'nid1': '一级组织号(nid1)',
        'lev2': '二级组织(lev2)',
        'nid2': '二级组织号(nid2)',
        'lev3': '三级组织(lev3)',
        'nid3': '三级组织号(nid3)',
        'lev4': '四级组织(lev4)',
        'nid': '四级组织号(nid)',
        'classId': '记录课程(classId)',
        'userid': 'openid(userid)'
    }
    df = df.rename(columns=new_columns_names)
    df = df.sort_values(by='四级组织(lev4)', ascending=True, na_position='last')
    df = df.dropna(subset=['openid(userid)'])
    return df

if __name__ == "__main__":
    # loginSession = login(username, password,True)
    loginSession = load_session_from_file('session.pkl')
    rootID = getRoot(loginSession)
    memberCnt,orgName,parentidName,parentid = getSelfInfo(loginSession, rootID)
    needID = showMenu(loginSession,memberCnt,orgName,parentidName,parentid,rootID)
    courseList = getCourseList(loginSession)
    datas = getLeanHistory(loginSession,orgName, needID, courseList,limit)
    datas = processDF(datas)
    save_splits_to_excel(datas)