import os
import time
import random
import re
import textwrap
import requests
from pyaes import AESModeOfOperationCBC
from requests import Session as req_Session

# 企业微信 webhook URL
WECHAT_WEBHOOK_URL = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key="
# 填入企业微信机器人应用的key密钥

# 随机生成用户空间链接
def randomly_gen_uspace_url() -> list:
    url_list = []
    for i in range(12):
        uid = random.randint(10000, 50000)
        url = "https://hostloc.com/space-uid-{}.html".format(str(uid))
        url_list.append(url)
    return url_list


# 使用Python实现防CC验证页面中JS写的的toNumbers函数
def toNumbers(secret: str) -> list:
    text = []
    for value in textwrap.wrap(secret, 2):
        text.append(int(value, 16))
    return text


# 不带Cookies访问论坛首页，检查是否开启了防CC机制，将开启状态、AES计算所需的参数全部放在一个字典中返回
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
        if len(aes_keys) != 3 or len(cookie_name) != 1:
            result_dict["ok"] = 0
        else:
            result_dict["ok"] = 1
            result_dict["cookie_name"] = cookie_name[0]
            result_dict["a"] = aes_keys[0]
            result_dict["b"] = aes_keys[1]
            result_dict["c"] = aes_keys[2]
    return result_dict


# 在开启了防CC机制时使用获取到的数据进行AES解密计算生成一条Cookie（未开启防CC机制时返回空Cookies）
def gen_anti_cc_cookies() -> dict:
    cookies = {}
    anti_cc_status = check_anti_cc()

    if anti_cc_status:
        if anti_cc_status["ok"] == 0:
            pass
        else:
            a = bytes(toNumbers(anti_cc_status["a"]))
            b = bytes(toNumbers(anti_cc_status["b"]))
            c = bytes(toNumbers(anti_cc_status["c"]))
            cbc_mode = AESModeOfOperationCBC(a, b)
            result = cbc_mode.decrypt(c)

            name = anti_cc_status["cookie_name"]
            cookies[name] = result.hex()
    return cookies


# 登录帐户
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


# 通过抓取用户设置页面的标题检查是否登录成功
def check_login_status(s: req_Session, number_c: int) -> bool:
    test_url = "https://hostloc.com/home.php?mod=spacecp"
    res = s.get(test_url)
    res.raise_for_status()
    res.encoding = "utf-8"
    test_title = re.findall("<title>(.*?)<\/title>", res.text)

    if len(test_title) != 0:
        if test_title[0] != "个人资料 -  全球主机交流论坛 -  Powered by Discuz!":
            return False
        else:
            return True
    else:
        return False


# 抓取并打印输出帐户当前积分
def print_current_points(s: req_Session):
    test_url = "https://hostloc.com/forum.php"
    res = s.get(test_url)
    res.raise_for_status()
    res.encoding = "utf-8"
    points = re.findall("积分: (\d+)", res.text)

    if len(points) != 0:
        return "帐户当前积分：" + points[0]
    else:
        return "无法获取帐户积分，可能页面存在错误或者未登录！"


# 依次访问随机生成的用户空间链接获取积分
def get_points(s: req_Session, number_c: int):
    if check_login_status(s, number_c):
        points_log = print_current_points(s)
        url_list = randomly_gen_uspace_url()
        for i in range(len(url_list)):
            url = url_list[i]
            try:
                res = s.get(url)
                res.raise_for_status()
            except Exception as e:
                continue
        points_log += "\n" + print_current_points(s)
        return points_log
    else:
        return "请检查你的帐户是否正确！"


# 打印输出当前ip地址
def print_my_ip():
    api_url = "http://ip-api.com/json"
    try:
        res = requests.get(url=api_url)
        res.raise_for_status()
        res.encoding = "utf-8"
        ip_info = res.json()
        if ip_info.get("status") == "fail":
            return "获取当前 ip 地址失败：" + ip_info.get("message", "未知错误")
        else:
            return "当前使用 ip 地址：" + ip_info.get('query', '无法获取 IP')
    except Exception as e:
        return "获取当前 ip 地址失败：" + str(e)


# 发送完整日志到企业微信
def send_log_to_wechat(log_msg: str):
    payload = {
        "msgtype": "text",
        "text": {
            "content": log_msg
        }
    }
    try:
        res = requests.post(WECHAT_WEBHOOK_URL, json=payload)
        res.raise_for_status()
    except Exception as e:
        print(f"发送日志到企业微信失败: {str(e)}")


# 打印日志并发送到企业微信
def log_and_send(log_msg: str):
    print(log_msg)  # 打印日志到控制台
    send_log_to_wechat(log_msg)  # 发送日志到企业微信


# 主程序
if __name__ == "__main__":
    username = ""
    password = ""
    # username&password 多账号示例
    # username = "username1,username2,username3,..."
    # password = "password1,password2,password3,..."
    user_list = username.split(",")
    passwd_list = password.split(",")

    log_messages = []

    if not username or not password:
        log_messages.append("未检测到用户名或密码，请检查环境变量是否设置正确！")
    elif len(user_list) != len(passwd_list):
        log_messages.append("用户名与密码个数不匹配，请检查环境变量设置是否错漏！")
    else:
        log_messages.append(print_my_ip())
        log_messages.append(f"共检测到 {len(user_list)} 个帐户，开始获取积分")
        log_messages.append("*" * 30)

        for i in range(len(user_list)):
            try:
                s = login(user_list[i], passwd_list[i])
                points_log = get_points(s, i + 1)
                log_messages.append(points_log)
                log_messages.append("*" * 30)
            except Exception as e:
                log_messages.append(f"程序执行异常：{str(e)}")
                log_messages.append("*" * 30)

        log_messages.append("程序执行完毕，获取积分过程结束")

    # 发送完整的日志到企业微信
    full_log = "\n".join(log_messages)
    log_and_send(full_log)
