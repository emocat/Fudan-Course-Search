import json
import requests
import time
import re


class CourseSearcher:
    def __init__(self):
        self.cookies = dict()
        self.cookies_file = "cookies.txt"
        self.search_urls = "http://yjsxk.fudan.sh.cn/yjsxkapp/sys/xsxkappfudan/xsxkCourse/loadAllCourseInfo.do"

        self.courses = [
            {
                "name": "分布式系统",
                "data": {
                    "query_keyword": "COMP620017",
                    "query_kccc": "",
                    "query_syxwlx": "",
                    "query_kkyx": "",
                    "query_xqdm1": "03",
                    "fixedAutoSubmitBug": "",
                    "query_jxsjhnkc": "0",
                    "pageIndex": "1",
                    "pageSize": "20",
                    "sortField": "",
                    "sortOrder": "",
                },
                "requirement": {},
                "request": {"bjdm": "2021202201COMP620017.01", "lx": 8},
                "status": 0,
            },
            {
                "name": "研究生综合英语",
                "data": {
                    "query_keyword": "马运怡",
                    "query_kccc": "",
                    "query_syxwlx": "",
                    "query_kkyx": "",
                    "query_xqdm1": "",
                    "fixedAutoSubmitBug": "",
                    "query_jxsjhnkc": "0",
                    "pageIndex": "1",
                    "pageSize": "20",
                    "sortField": "",
                    "sortOrder": "",
                },
                "requirement": {"PKSJ": "1-16周 星期五[3-4节]"},
                # "request": {"bjdm": "2021202201MAST611104.25", "lx": 7},
                "status": 0,
            },
            {
                "name": "神经网络与深度学习",
                "data": {
                    "query_keyword": "神经网络与深度学习",
                    "query_kccc": "",
                    "query_syxwlx": "",
                    "query_kkyx": "",
                    "query_xqdm1": "",
                    "fixedAutoSubmitBug": "",
                    "query_jxsjhnkc": "0",
                    "pageIndex": "1",
                    "pageSize": "20",
                    "sortField": "",
                    "sortOrder": "",
                },
                "requirement": {},
                "request": {"bjdm": "2021202201COMP630068.01", "lx": 8},
                "status": 1,
            },
        ]

        self.last_time = 0

    def read_cookies(self):
        with open(self.cookies_file, "r", encoding="utf-8") as f:
            cookies_txt = f.read().strip(";")
            for cookie in cookies_txt.split(";"):
                name, value = cookie.strip().split("=", 1)
                self.cookies[name] = value
        cookiesJar = requests.utils.cookiejar_from_dict(
            self.cookies, cookiejar=None, overwrite=True
        )
        return cookiesJar

    def available_hints(self, course):
        print(
            "[+] {} {} {} {}".format(
                course["KCMC"], course["RKJS"], course["XQMC"], course["PKSJ"]
            )
        )

        if time.time() - self.last_time >= 3600:
            self.last_time = time.time()
        else:
            return

        url = "https://sc.ftqq.com/******.send"
        data = {
            "title": "课程爬虫通知",
            "desp": "[+] {} {} {} {} ({} / {})".format(
                course["KCMC"],
                course["RKJS"],
                course["XQMC"],
                course["PKSJ"],
                course["DQRS"],
                course["KXRS"],
            ),
        }
        r = requests.post(url, data=data)
        print(r.text)

    def is_course_available(self, course, target):
        if course["KXRS"] == course["DQRS"]:
            return False

        if "requirement" in target:
            for attr in target["requirement"]:
                if course[attr] != target["requirement"][attr]:
                    return False
            return True

    # 刷课
    def search(self):
        self.session = requests.session()
        self.session.cookies = self.read_cookies()
        while True:
            time.sleep(1.5)
            for target in self.courses:
                if target["status"] == 0:
                    continue
                try:
                    response = self.session.post(
                        self.search_urls, data=target["data"], timeout=5
                    )
                    response = response.content.decode()
                    response = json.loads(response)

                    print("=============================================")
                    for _, course in enumerate(response["datas"]):
                        print(
                            "{} ({} / {})".format(
                                course["KCMC"], course["DQRS"], course["KXRS"]
                            )
                        )
                        if self.is_course_available(course, target):
                            self.available_hints(course)

                            # decide to request this course
                            if "request" in target:
                                res = self.single_course_request(target["request"])
                                if res:
                                    target["status"] = 0

                except Exception as e:
                    print(Exception, e)
                    continue

    # 选课
    def single_course_request(self, course):
        form_data = {"bjdm": "", "lx": "", "csrfToken": None}
        form_data["bjdm"] = course["bjdm"]
        form_data["lx"] = course["lx"]

        new_token = self._refresh_csrfToken(self.session)
        form_data["csrfToken"] = new_token

        print("抢课开始")
        print(form_data)
        response = self._request_course(self.session, form_data)
        print(response)

        if response["code"] == 0:
            print("抢课异常")
            if "过期" in response["msg"]:
                print("token过期")
            if "已满" in response["msg"]:
                print("抢课已满")
            if "选择的教学班不在您的可选范围内" in response["msg"]:
                print("已抢过课")
                return True
            return False
        else:
            print("抢课成功")
            return True

    # 抢课（捡漏）
    def frequent_course_request(self, course):
        self.session_choose = requests.session()
        self.session_choose.cookies = self.read_cookies()

        form_data = {"bjdm": "", "lx": "", "csrfToken": None}
        form_data["bjdm"] = course["bjdm"]
        form_data["lx"] = course["lx"]

        while True:
            new_token = self._refresh_csrfToken(self.session_choose)
            form_data["csrfToken"] = new_token

            while True:
                time.sleep(1.5)
                print("抢课开始")
                response = self._request_course(self.session_choose, form_data)

                if response["code"] == 0:
                    print("抢课异常")
                    if "过期" in response["msg"]:
                        break
                    if "已满" in response["msg"]:
                        print("抢课已满")
                        return
                else:
                    print("抢课成功")
                    return

    def _request_course(self, session, form_data):
        try:
            response = session.post(
                url="http://yjsxk.fudan.edu.cn/yjsxkapp/sys/xsxkappfudan/xsxkCourse/choiceCourse.do",
                data=form_data,
                timeout=5,
            )
            response = response.content.decode()
            response = json.loads(response)

            print(response)
        except:
            response = None

        return response

    def _refresh_csrfToken(self, session):
        try:
            response = session.get(
                "http://yjsxk.fudan.edu.cn/yjsxkapp/sys/xsxkappfudan/xsxkHome/gotoChooseCourse.do",
                timeout=5,
            )
            response = response.content.decode()
            new_token = re.findall(r"csrfToken\" value='(.*)'", response)[0]
        except:
            new_token = None

        return new_token


if __name__ == "__main__":
    s = CourseSearcher()
    s.search()
