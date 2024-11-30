import random
from time import localtime
from requests import get, post
from datetime import datetime, date
from zhdate import ZhDate
import sys
import os


def get_color():
    # 获取随机颜色
    get_colors = lambda n: list(map(lambda i: "#" + "%06x" % random.randint(0, 0xFFFFFF), range(n)))
    color_list = get_colors(100)
    return random.choice(color_list)


def get_access_token():
    # appId
    app_id = config["app_id"]
    # appSecret
    app_secret = config["app_secret"]
    post_url = ("https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={}&secret={}"
                .format(app_id, app_secret))
    try:
        response = get(post_url, timeout=10)
        print(f"获取access_token响应状态码: {response.status_code}")
        print(f"响应内容: {response.text}")
        
        if response.status_code != 200:
            print(f"HTTP请求失败，状态码: {response.status_code}")
            sys.exit(1)
            
        result = response.json()
        if 'access_token' in result:
            return result['access_token']
        else:
            print(f"获取access_token失败，错误信息: {result.get('errmsg', '未知错误')}")
            sys.exit(1)
            
    except Exception as e:
        print(f"请求发生异常: {str(e)}")
        sys.exit(1)


def get_weather(region):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                      'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36'
    }
    key = config["weather_key"]
    region_url = "https://geoapi.qweather.com/v2/city/lookup?location={}&key={}".format(region, key)
    response = get(region_url, headers=headers).json()
    if response["code"] == "404":
        print("推送消息失败，请检查地区名是否有误！")
        sys.exit(1)
    elif response["code"] == "401":
        print("推送消息失败，请检查和风天气key是否正确！")
        sys.exit(1)
    else:
        # 获取地区的location--id
        location_id = response["location"][0]["id"]
    weather_url = "https://devapi.qweather.com/v7/weather/now?location={}&key={}".format(location_id, key)
    response = get(weather_url, headers=headers).json()
    # 天气
    weather = response["now"]["text"]
    # 当前温度
    temp = response["now"]["temp"] + u"\N{DEGREE SIGN}" + "C"
    # 风向
    wind_dir = response["now"]["windDir"]
    # 获取逐日天气预报
    url = "https://devapi.qweather.com/v7/weather/3d?location={}&key={}".format(location_id, key)
    response = get(url, headers=headers).json()
    # 最高气温
    max_temp = response["daily"][0]["tempMax"] + u"\N{DEGREE SIGN}" + "C"
    # 最低气温
    min_temp = response["daily"][0]["tempMin"] + u"\N{DEGREE SIGN}" + "C"
    # 日出时间
    sunrise = response["daily"][0]["sunrise"]
    # 日落时间
    sunset = response["daily"][0]["sunset"]
    url = "https://devapi.qweather.com/v7/air/now?location={}&key={}".format(location_id, key)
    response = get(url, headers=headers).json()
    if response["code"] == "200":
        # 空气质量
        category = response["now"]["category"]
        # pm2.5
        pm2p5 = response["now"]["pm2p5"]
    else:
        # 国外城市获取不到数据
        category = ""
        pm2p5 = ""
    id = random.randint(1, 16)
    url = "https://devapi.qweather.com/v7/indices/1d?location={}&key={}&type={}".format(location_id, key, id)
    response = get(url, headers=headers).json()
    return weather, temp, max_temp, min_temp, wind_dir, sunrise, sunset, category, pm2p5


def get_tianhang():
    try:
        key = config["tian_api"]
        url = "http://api.tianapi.com/caihongpi/index?key={}".format(key)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                          'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36',
            'Content-type': 'application/x-www-form-urlencoded'

        }
        response = get(url, headers=headers).json()
        if response["code"] == 200:
            chp = response["newslist"][0]["content"]
        else:
            chp = ""
    except KeyError:
        print("获取access_token失败，请检查app_id和app_secret是否正确")
        sys.exit(1)
    return chp


def get_birthday(birthday, year, today):
    birthday_year = birthday.split("-")[0]
    # 判断是否为农历生日
    if birthday_year[0] == "r":
        r_mouth = int(birthday.split("-")[1])
        r_day = int(birthday.split("-")[2])
        # 获取农历生日的生日
        try:
            year_date = ZhDate(year, r_mouth, r_day).to_datetime().date()
        except TypeError:
            print("请检查生日的日子是否在今年存在")
            os.system("pause")
            sys.exit(1)

    else:
        # 获取国历生日的今年对应月和日
        birthday_month = int(birthday.split("-")[1])
        birthday_day = int(birthday.split("-")[2])
        # 今年生日
        year_date = date(year, birthday_month, birthday_day)
    # 计算生日年份，如果还没过，按当年减，如果过了需要+1
    if today > year_date:
        if birthday_year[0] == "r":
            # 获取农历明年生日的月和日
            r_last_birthday = ZhDate((year + 1), r_mouth, r_day).to_datetime().date()
            birth_date = date((year + 1), r_last_birthday.month, r_last_birthday.day)
        else:
            birth_date = date((year + 1), birthday_month, birthday_day)
        birth_day = str(birth_date.__sub__(today)).split(" ")[0]
    elif today == year_date:
        birth_day = 0
    else:
        birth_date = year_date
        birth_day = str(birth_date.__sub__(today)).split(" ")[0]
    return birth_day


def send_message(to_user, access_token, region_name, weather, temp, wind_dir, max_temp, min_temp,
                 sunrise, sunset, category, pm2p5, chp):
    url = "https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={}".format(access_token)
    
    # 打印调试信息
    print("\n准备发送的消息内容：")
    print(f"chp: {chp}")
    
    week_list = ["星期日", "星期一", "星期二", "星期三", "星期四", "星期五", "星期六"]
    year = localtime().tm_year
    month = localtime().tm_mon
    day = localtime().tm_mday
    today = datetime.date(datetime(year=year, month=month, day=day))
    week = week_list[today.isoweekday() % 7]
    
    # 获取在一起的日子的日期格式
    love_year = int(config["love_date"].split("-")[0])
    love_month = int(config["love_date"].split("-")[1])
    love_day = int(config["love_date"].split("-")[2])
    love_date = date(love_year, love_month, love_day)
    # 获取在一起的日期差
    love_days = str(today.__sub__(love_date)).split(" ")[0]
    
    # 获取生日数据并提前计算
    birthdays = {}
    birthday_data1 = ""
    birthday_data2 = ""
    
    for k, v in config.items():
        if k[0:5] == "birth":
            birthdays[k] = v
            print(f"获取到生日信息 - {k}: {v}")  # 调试信息
            
            birth_day = get_birthday(v["birthday"], year, today)
            if birth_day == 0:
                birthday_data = "今天{}生日哦，祝{}生日快乐！".format(v["name"], v["name"])
            else:
                birthday_data = "距离{}的生日还有{}天".format(v["name"], birth_day)
                
            if k == "birthday1":
                birthday_data1 = birthday_data
                print(f"设置 birthday1 数据: {birthday_data1}")  # 调试信息
            elif k == "birthday2":
                birthday_data2 = birthday_data
                print(f"设置 birthday2 数据: {birthday_data2}")  # 调试信息
    
    # 构建完整的日期信息，包含生日和彩虹屁
    date_info = "{} {}\n\n{}\n{}\n\n{}".format(
        today, 
        week,
        birthday_data1,
        birthday_data2,
        chp
    )
    
    data = {
        "touser": to_user,
        "template_id": config["template_id"],
        "url": "http://weixin.qq.com/download",
        "topcolor": "#FF0000",
        "data": {
            "date": {
                "value": date_info,  # 使用包含所有信息的日期字符串
                "color": get_color()
            },
            "region": {
                "value": region_name,
                "color": get_color()
            },
            "weather": {
                "value": weather,
                "color": get_color()
            },
            "temp": {
                "value": temp,
                "color": get_color()
            },
            "wind_dir": {
                "value": wind_dir,
                "color": get_color()
            },
            "love_day": {
                "value": love_days,
                "color": get_color()
            },
            "max_temp": {
                "value": max_temp,
                "color": get_color()
            },
            "min_temp": {
                "value": min_temp,
                "color": get_color()
            },
            "sunrise": {
                "value": sunrise,
                "color": get_color()
            },
            "sunset": {
                "value": sunset,
                "color": get_color()
            },
            "category": {
                "value": category,
                "color": get_color()
            },
            "pm2p5": {
                "value": pm2p5,
                "color": get_color()
            }
        }
    }
    
    # 打印完整的发送数据
    print("\n准备发送的完整数据：")
    print(data)
    
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                      'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36'
    }
    response = post(url, headers=headers, json=data).json()
    
    print("\n发送消息响应：")
    print(response)
    
    if response["errcode"] == 40037:
        print("推送消息失败，请检查模板id是否正确")
    elif response["errcode"] == 40036:
        print("推送消息失败，请检查模板id是否为空")
    elif response["errcode"] == 40003:
        print("推送消息失败，请检查微信号是否正确")
    elif response["errcode"] == 0:
        print("推送消息成功")
    else:
        print(f"推送消息失败，错误信息: {response}")


if __name__ == "__main__":
    try:
        with open("config.txt", encoding="utf-8") as f:
            config = eval(f.read())
            
        # 验证必要的配置项
        required_keys = ['app_id', 'app_secret', 'template_id', 'user']
        for key in required_keys:
            if key not in config:
                print(f"配置文件缺少必要的配置项: {key}")
                sys.exit(1)
                
        print("当前配置信息:")
        print(f"app_id: {config['app_id']}")
        print(f"模板ID: {config['template_id']}")
        print(f"用户列表: {config['user']}")

        # 获取accessToken
        accessToken = get_access_token()
        # 接收的用户
        users = config["user"]
        # 传入地区获取天气信息
        region = config["region"]
        weather, temp, max_temp, min_temp, wind_dir, sunrise, sunset, category, pm2p5 = get_weather(region)
        chp = get_tianhang()
        # 公众号推送消息
        for user in users:
            send_message(user, accessToken, region, weather, temp, wind_dir, max_temp, min_temp, sunrise,
                         sunset, category, pm2p5, chp)
        os.system("pause")

    except FileNotFoundError:
        print("推送消息失败，请检查config.txt文件是否与程序位于同一路径")
        os.system("pause")
        sys.exit(1)
    except SyntaxError:
        print("推送消息失败，请检查配置文件格式是否正确")
        os.system("pause")
        sys.exit(1)
