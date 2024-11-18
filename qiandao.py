import os
import time
import random
import re
import textwrap
import requests

from pyaes import AESModeOfOperationCBC
from requests import Session as req_Session


def randomly_gen_uspace_url() -> list:
    url_list = []
    for i in range(12):
        uid = random.randint(10000, 50000)
        url = "https://hostloc.com/space-uid-{}.html".format(str(uid))
        url_list.append(url)
    return url_list

def toNumbers(secret: str) -> list:
    text = []
    for value in textwrap.wrap(secret, 2):
        text.append(int(value, 16))
    return text


def check_anti_cc() -> dict:
    result_dict = {}
    headers = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36"
    }
    home_page = "https://hostloc.com/forum.php"
    res = requests.get(home_page, headers=headers)
    aes_keys = re.findall('toNumbers\("(.*?)"\)', res.text)
    cookie_name = re.findall('cookie="(.*?)="', res.text)

    if len(aes_keys) != 0:  
        print("检测到防 CC 机制开启！")
        if len(aes_keys) != 3 or len(cookie_name) != 1:  
            result_dict["ok"] = 0
        else:  
            result_dict["ok"] = 1
            result_dict["cookie_name"] = cookie_name[0]
            result_dict["a"] = aes_keys[0]
            result_dict["b"] = aes_keys[1]
            result_dict["c"] = aes_keys[2]
    else:
        pass

    return result_dict


def gen_anti_cc_cookies() -> dict:
    cookies = {}
    anti_cc_status = check_anti_cc()

    if anti_cc_status:  
        if anti_cc_status["ok"] == 0:
            print("防 CC 验证过程所需参数不符合要求，页面可能存在错误！")
        else:  
            print("自动模拟计尝试通过防 CC 验证")
            a = bytes(toNumbers(anti_cc_status["a"]))
            b = bytes(toNumbers(anti_cc_status["b"]))
            c = bytes(toNumbers(anti_cc_status["c"]))
            cbc_mode = AESModeOfOperationCBC(a, b)
            result = cbc_mode.decrypt(c)

            name = anti_cc_status["cookie_name"]
            cookies[name] = result.hex()
    else:
        pass

    return cookies


def login(username: str, password: str) -> req_Session:
    headers = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36",
        "origin": "https://hostloc.com",
        "referer": "https://hostloc.com/forum.php",
    }
    login_url = "https://hostloc.com/member.php?mod=logging&action=login&loginsubmit=yes&infloat=yes&lssubmit=yes&inajax=1"
    login_data = {
        "fastloginfield": "username",
        "username": username,
        "password": password,
        "quickforward": "yes",
        "handlekey": "ls",
    }

    s = req_Session()
    s.headers.update(headers)
    s.cookies.update(gen_anti_cc_cookies())
    res = s.post(url=login_url, data=login_data)
    res.raise_for_status()
    return s


def check_login_status(s: req_Session, number_c: int) -> bool:
    test_url = "https://hostloc.com/home.php?mod=spacecp"
    res = s.get(test_url)
    res.raise_for_status()
    res.encoding = "utf-8"
    test_title = re.findall("<title>(.*?)<\/title>", res.text)

    if len(test_title) != 0:  
        if test_title[0] != "个人资料 -  全球主机交流论坛 -  Powered by Discuz!":
            print("第", number_c, "个帐户登录失败！")
            return False
        else:
            print("第", number_c, "个帐户登录成功！")
            return True
    else:
        print("无法在用户设置页面找到标题，该页面存在错误或被防 CC 机制拦截！")
        return False


def print_current_points(s: req_Session):
    test_url = "https://hostloc.com/forum.php"
    res = s.get(test_url)
    res.raise_for_status()
    res.encoding = "utf-8"
    points = re.findall("积分: (\d+)", res.text)

    if len(points) != 0:  
        print("帐户当前积分：" + points[0])
    else:
        print("无法获取帐户积分，可能页面存在错误或者未登录！")
    time.sleep(5)


def get_points(s: req_Session, number_c: int):
    if check_login_status(s, number_c):
        print_current_points(s)  
        url_list = randomly_gen_uspace_url()
        for i in range(len(url_list)):
            url = url_list[i]
            try:
                res = s.get(url)
                res.raise_for_status()
                print("第", i + 1, "个用户空间链接访问成功")
                time.sleep(5)  
            except Exception as e:
                print("链接访问异常：" + str(e))
            continue
        print_current_points(s)  # 再次打印帐户当前积分
    else:
        print("请检查你的帐户是否正确！")


def print_my_ip():
    api_url = "http://ip-api.com/json"
    try:
        res = requests.get(url=api_url)
        res.raise_for_status()
        res.encoding = "utf-8"
        ip_info = res.json()
        if ip_info.get("status") == "fail":
            print("获取当前 ip 地址失败：" + ip_info.get("message", "未知错误"))
        else:
            print("当前使用 ip 地址：" + ip_info.get('query', '无法获取 IP'))
    except Exception as e:
        print("获取当前 ip 地址失败：" + str(e))


if __name__ == "__main__":
    username = ""
    password = ""
    # username&password demo
    # username = "username1,username2,username3,..."
    # password = "password1,password2,password3,..."



    user_list = username.split(",")
    passwd_list = password.split(",")

    if not username or not password:
        print("未检测到用户名或密码，请检查环境变量是否设置正确！")
    elif len(user_list) != len(passwd_list):
        print("用户名与密码个数不匹配，请检查环境变量设置是否错漏！")
    else:
        print_my_ip()
        print("共检测到", len(user_list), "个帐户，开始获取积分")
        print("*" * 30)

        for i in range(len(user_list)):
            try:
                s = login(user_list[i], passwd_list[i])
                get_points(s, i + 1)
                print("*" * 30)
            except Exception as e:
                print("程序执行异常：" + str(e))
                print("*" * 30)
            continue

        print("程序执行完毕，获取积分过程结束")
