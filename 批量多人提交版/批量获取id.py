import json
import pickle
import re
from datetime import datetime

import cv2
import ddddocr
import numpy as np
import requests
from bs4 import BeautifulSoup

# 账号
username = ""
# 密码
password = ""
# 加密秘钥
public_exponent = "10001"
modulus = "dff46645b6337855b0c1f9812a1a943904f2abd5f2f339f0f3b7f81cdb169eab00da0321a0075ef1d9e12d2af4d168b16d0f3ded064f8bcb97ca2af891eb73a0b55a2990b62fffc0cee0e61efcf5ec6247c8eb4a1f4df6d2ac42d930407c52c6e8cd07f6babf109c50428c3d8f1a64a66950178197136ee19b04b2bdf6dcb3df"


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


# 识别verify.jpg验证码中的文字
def get_verify_code(img, return_ocr_result=False):
    print("识别验证码中")
    ocr = ddddocr.DdddOcr()
    img = cv2.imdecode(np.frombuffer(img, np.uint8), cv2.IMREAD_COLOR)
    img = operate_img(img, 1)
    cv2.imwrite("verify1.jpg", img)
    img_bytes = cv2.imencode('.jpg', img)[1].tobytes()
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


import js2py


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


def login(userCode, password, showCookie=True):
    session = requests.Session()

    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        "Cache-Control": "max-age=0",
        "Content-Type": "application/x-www-form-urlencoded",
        "Host": "106.225.141.143:8103",
        "Origin": "http://106.225.141.143:8103",
        "Referer": "http://106.225.141.143:8103/pub/login",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": ""
    }

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


if __name__ == "__main__":
    loginSession = login(username, password)
