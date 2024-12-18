import random
from time import localtime
from requests import get, post
from datetime import datetime, date
from zhdate import ZhDate
import sys
import os


def get_access_token():
    # appId
    app_id = config["app_id"]
    # appSecret
    app_secret = config["app_secret"]
    post_url = ("https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={}&secret={}"
                .format(app_id, app_secret))
    try:
        response = get(post_url, timeout=10)
        if response.status_code != 200:
            sys.exit(1)
            
        result = response.json()
        if 'access_token' in result:
            return result['access_token']
        else:
            sys.exit(1)
            
    except Exception as e:
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


def get_birthday(birthday, year, today):
    birthday_year = birthday[0]  # 获取第一个字符，判断是否为 'r'
    # 判断是否为农历生日
    if birthday_year == "r":
        r_mouth = int(birthday.split("-")[1])
        r_day = int(birthday.split("-")[2])
        # 获取农历生日的生日
        try:
            year_date = ZhDate(year, r_mouth, r_day).to_datetime().date()
        except TypeError:
            print("请检查生日的日子是否在今年存在")
            sys.exit(1)
    else:
        # 获取国历生日的今年对应月和日
        birthday_month = int(birthday.split("-")[1])
        birthday_day = int(birthday.split("-")[2])
        # 今年生日
        year_date = date(year, birthday_month, birthday_day)
        
    # 计算生日年份，如果还没过，按当年减，如果过了需要+1
    if today > year_date:
        if birthday_year == "r":
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
                 sunrise, sunset, category, pm2p5):
    url = "https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={}".format(access_token)
    
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
    birth_day1 = get_birthday(config["birthday1"], year, today)
    birth_day2 = get_birthday(config["birthday2"], year, today)
    
    # 构建完整的日期信息
    date_info = "{} {}".format(today, week)
    
    data = {
        "touser": to_user,
        "template_id": config["template_id"],
        "url": "http://weixin.qq.com/download",
        "data": {
            "date": {"value": date_info},
            "region": {"value": region_name},
            "weather": {"value": weather},
            "temp": {"value": temp},
            "wind_dir": {"value": wind_dir},
            "love_day": {"value": love_days},
            "max_temp": {"value": max_temp},
            "min_temp": {"value": min_temp},
            "sunrise": {"value": sunrise},
            "sunset": {"value": sunset},
            "category": {"value": category},
            "birthday1": {"value": birth_day1},
            "birthday2": {"value": birth_day2},
            "pm2p5": {"value": pm2p5}
        }
    }
    
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                      'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36'
    }
    response = post(url, headers=headers, json=data).json()
    
    if response["errcode"] != 0:
        sys.exit(1)


if __name__ == "__main__":
    try:
        with open("config.txt", encoding="utf-8") as f:
            config = eval(f.read())
            
        # 验证必要的配置项
        required_keys = ['app_id', 'app_secret', 'template_id', 'user']
        for key in required_keys:
            if key not in config:
                sys.exit(1)

        # 获取accessToken
        accessToken = get_access_token()
        # 接收的用户
        users = config["user"]
        # 传入地区获取天气信息
        region = config["region"]
        weather, temp, max_temp, min_temp, wind_dir, sunrise, sunset, category, pm2p5 = get_weather(region)
        # 公众号推送消息
        for user in users:
            send_message(user, accessToken, region, weather, temp, wind_dir, max_temp, min_temp, sunrise,
                         sunset, category, pm2p5)

    except (FileNotFoundError, SyntaxError):
        sys.exit(1)
