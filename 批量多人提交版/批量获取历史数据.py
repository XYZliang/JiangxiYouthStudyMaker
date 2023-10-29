import io
import pickle
import re
from datetime import datetime
import ddddocr
import imageio
import js2py
from PIL import Image
from anti_useragent import UserAgent
from bs4 import BeautifulSoup
from openpyxl.reader.excel import load_workbook
from tqdm import tqdm
import pandas as pd
import configparser


# 创建配置解析器并读取ini文件
config = configparser.ConfigParser()
config.read('config.ini', encoding='utf-8')

# 读取[setting]下的配置
limit = config.getint('setting', 'limit')

# 读取[management background]下的配置
username = config.get('management background', 'username')
password = config.get('management background', 'password')
# 转为字符串
password = str(password)
host = config.get('management background', 'host')
protocol = config.get('management background', 'protocol')

# 读取[encryptionKey]下的配置
max_digits = config.get('encryptionKey', 'max_digits')
public_exponent = config.get('encryptionKey', 'public_exponent')
modulus = config.get('encryptionKey', 'modulus')


headers = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
    'Cache-Control': 'no-cache',
    "Origin": protocol+"://"+host,
    "Host": host,
    'Content-type': 'application/x-www-form-urlencoded',
    'Pragma': 'no-cache',
    'Proxy-Connection': 'keep-alive',
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
    ocr = ddddocr.DdddOcr(show_ad=False)
    # 使用imageio替代cv2，从bytes读取图像得到numpy.ndarray
    try:
        img_array = imageio.imread(io.BytesIO(img))
        img_array = operate_img(img_array, 1)
        # 使用imageio将numpy.ndarray保存为bytes
        img_bytes_io = io.BytesIO()
        imageio.imwrite(img_bytes_io, img_array, format='JPEG')
        img_bytes = img_bytes_io.getvalue()
        verify_code = ocr.classification(img_bytes)
    except ValueError:
        print("验证码识别失败，可能是验证码图片损坏，即将重试")
        return 0

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
        setMaxDigits("""+max_digits+""");
        var key = new RSAKeyPair(\""""""+public_exponent+"""","",\""""+modulus+"""");
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
    base_url = protocol+"://"+host+"/pub/verify?t="
    current_time = datetime.now().time().strftime('%Y-%M-%S')
    captcha_url = base_url + current_time

    response = requests.get(captcha_url,timeout=15,headers=headers)
    if response.status_code == 200:
        captcha_result = get_verify_code(response.content, True)
        with open(f"{captcha_result}.png", "wb") as f:
            f.write(response.content)
        print(f"Captcha saved as {captcha_result}.png with result: {captcha_result}")
        return captcha_result
    else:
        print(f"Failed to fetch captcha. Status code: {response.status_code}")
        return None


def login(userCode, password, showCookie=False, errorTime=0):
    if errorTime > 5:
        print("错误次数过多，大概率是配置的host后台又崩了，请去配置换一个host或稍后再试")
        exit()

    session = requests.Session()

    #  head + 'Referer': 'http://mp.jxqingtuan.cn/pub/login?returnUrl=/',
    loginheaders = headers
    loginheaders['Referer'] = protocol+"://"+host+"/pub/login"

    # 1. 请求登录页面获取JSESSIONID和_jfinal_token
    try:
        response = session.get(protocol+"://"+host+"/pub/login",timeout=15,headers=loginheaders)
        soup = BeautifulSoup(response.text, 'html.parser')
        jfinal_token = soup.find('input', {'id': '_jfinal_token'})['value']
    except TypeError:
        print("获取登录页面失败，大概率是配置的host后台又崩了，请去配置换一个host或稍后再试")
        exit()
        return None

    # 2. 获取验证码图片
    t = datetime.now().time().strftime('%Y-%M-%S')
    response = session.get(protocol+"://"+host+f"/pub/verify?t={t}",timeout=15,headers=headers)
    verify_code = get_verify_code(response.content)

    # 3. 提交登录请求
    data = {
        "userCode": userCode,
        "password": encrypt_with_js2py(password),
        "verifyCode": verify_code,
        "_jfinal_token": jfinal_token  # 添加_jfinal_token到POST数据中
    }
    res = session.post(protocol+"://"+host+"/pub/login/submit?returnUrl=",data=data,timeout=20,headers=headers)
    # 检测是不是302重定向到登录页面，如果是则登录失败
    if "用户不存在" in res.text or "帐号或密码错误" in res.text:
        print("用户传入的账户密码有误")
        return None
    elif "验证码错误，请重新输入" in res.text:
        print("验证码错误,正在重新尝试登录")
        login(userCode, password, showCookie)
    elif "系统异常" in res.text:
        print("系统异常,正在重新尝试登录")
        login(userCode, password, showCookie)
    # 4. 验证是否登录成功
    response = session.get(protocol+"://"+host+"/",timeout=15,headers=headers)
    content = response.text
    if "网站后台管理" in content:
        print("登录成功!!!!!!!!!!!!")
        if showCookie:
            print("Cookies:", session.cookies)
            save_session_to_file(session, 'session.pkl')
        return session
    # print(content)

    else:
        print("未知错误")
    print("登录失败,正在重新尝试登录")
    return login(userCode, password, showCookie, errorTime+1)


def save_session_to_file(session, filename):
    with open(filename, 'wb') as f:
        pickle.dump(session, f)


def load_session_from_file(filename):
    # 输出session的值
    with open(filename, 'rb') as f:
        session =  pickle.load(f)
    print("Cookies:", session.cookies)
    return session

def getRoot(session):
    # 获取响应html源代码
    response = session.get(protocol+"://"+host+"/portal/vol/sysOrg",timeout=15,headers=headers)
    content = response.text
    match = re.search(r'var rootId\s*=\s*"([^"]+)"', content)
    if match:
        root_id = match.group(1)
        return root_id
    else:
        print("rootId not found")
        exit()

def getSelfInfo(session, id):
    response = session.get(protocol+"://"+host+"/portal/vol/sysOrg/findSelf?id="+id,timeout=15,headers=headers)
    content = response.text
    # 加载json
    json_data = json.loads(content)['data']
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
    response = session.get(protocol+"://"+host+"/portal/vol/sysOrg/find?id="+id,timeout=15,headers=headers)
    content = response.text
    # 加载json
    json_data = json.loads(content)['data']
    return json_data

def showMenu(session,memberCnt,orgName,parentidName,parentid,selfID):
    print("###################欢迎" + orgName + "###################")
    print("组织人数：" + str(memberCnt))
    print("上级组织：" + parentidName)
    print("###################请选择操作###################")
    print("0：退出程序")
    print("1：获取当前组织下所有人员id（推荐，默认）")
    print("2：获取当前组织的某个直接下级组织的所有人员id")
    print("请输入数字（0-2）：")
    menuID = str(input())
    needID = selfID
    # 如果输入不合法
    while menuID != '0' and menuID != '1' and menuID != '2' and menuID != '3' and menuID != '4':
        print("输入不合法，请重新输入：")
        menuID = input()
    if menuID == '0':
        exit()
    if menuID == '2':
        sonList = getSonInfoList(session, selfID)
        print("###################请选择下级组织###################")
        for i in range(len(sonList)):
            print(str(i) + "：" + sonList[i]['orgName'])
        print("请输入数字（0-" + str(len(sonList) - 1) + "）：")
        sonID = str(input())
        # 如果输入不合法
        while sonID < '0' or sonID > str(len(sonList) - 1):
            print("输入不合法，请重新输入，如果要退出请停止程序：")
            sonID = input()
        sonID = sonList[sonID]['id']
    print("###################开始获取"+needID+"的所有人员id###################")
    return needID

def getCourseList(session):
    response = session.get(protocol+"://"+host+"/portal/vol/jxgqtClassRecord/index",timeout=15,headers=headers)
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


def getOneLeanHistory(session, courseID, nid, page=1, pageSize=20,errorTime=0):
    if errorTime > 5:
        print("错误次数过多，已退出，请稍后再试！")
        exit()
    params = {
        "iclassId": courseID,
        "inid": nid,
        "pageNumber": page,
        "pageSize": pageSize
    }
    try:
        response = session.get(protocol+"://"+host+"/portal/vol/jxgqtClassRecord/list", params=params,timeout=15,headers=headers)
        json_data = json.loads(response.text)
        return json_data
    except Exception as e:
        print("发生错误，重试中"+str(e))
        return getOneLeanHistory(session, courseID, nid, page, pageSize, errorTime+1)


def getLeanHistory(session, nid, courseList,orgName="当前组织", limit=None):
    all_data = []
    time = 0
    for course in courseList:
        if limit != 1:
            courseID = courseList[course]
            if limit!=None:
                if time>=limit:
                    break
            time = time + 1
        else:
            courseID=course
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
            filename = "历史学习数据/未知.xlsx"
        else:
            filename = f"历史学习数据/{name}.xlsx"

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
        'id': 'openid(userid)'
    }
    df = df.rename(columns=new_columns_names)
    df = df.sort_values(by='四级组织(lev4)', ascending=True, na_position='last')
    df = df.dropna(subset=['score'])
    return df

if __name__ == "__main__":
    loginSession = login(username, password,True)
    # loginSession = load_session_from_file('session.pkl')
    print(loginSession)
    rootID = getRoot(loginSession)
    memberCnt,orgName,parentidName,parentid = getSelfInfo(loginSession, rootID)
    needID = showMenu(loginSession,memberCnt,orgName,parentidName,parentid,rootID)
    courseList = getCourseList(loginSession)
    datas = getLeanHistory(loginSession, needID, courseList, orgName,limit)
    datas = processDF(datas)
    save_splits_to_excel(datas)
    print("获取完毕！")