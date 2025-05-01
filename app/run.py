import os
import sys
import asyncio
import sqlite3
import json
import time
import urllib
import platform
import re
import pprint
from bs4 import BeautifulSoup
import zendriver as zd
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCREENSHOT_DIR = os.path.join(BASE_DIR, "screenshots")
DATA_DIR = os.path.join(BASE_DIR, "web_data")

start_index = int(os.environ.get("START_INDEX", sys.argv[1] if len(sys.argv) > 1 else 0))
output_path = os.path.join(DATA_DIR, f"output_{start_index}.json")

os.makedirs(SCREENSHOT_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

print("📂 Screenshot 저장 경로:", SCREENSHOT_DIR)
print("📂 WebData 저장 경로:", DATA_DIR)

def load_restaurant_subset(start, end):
    conn = sqlite3.connect("/app/food_data.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT 사업장명, 도로명전체주소 FROM restaurants LIMIT ? OFFSET ?",
        (end - start, start),
    )
    rows = cursor.fetchall()
    conn.close()
    return [(name, addr) for name, addr in rows if name and addr]

def make_search_query(business_name, road_address):
    # 도로명 주소 앞 3단계까지만
    parts = road_address.split()
    if len(parts) >= 3:
        filtered_address = ' '.join(parts[:3])
    else:
        filtered_address = road_address

    query = f"{business_name} {filtered_address}"
    # pprint.pprint(f"Search query: {query}")
    return query

def sanitize_filename(name):
    # 파일명에 사용할 수 없는 문자 제거 (\ / * ? : " < > |)
    name = re.sub(r'[\\/*?:"<>|]', "", name)
    # 공백을 밑줄로 변경 (선택 사항)
    name = name.replace(" ", "_")
    # 필요시 최대 길이 제한 (선택 사항)
    max_len = 100
    if len(name) > max_len:
        name = name[:max_len]
    return name

async def load_page_with_wait(browser, url):
    page = await browser.get(url)

    tmp_parser = BeautifulSoup(await page.get_content(), "lxml")
    if any(err in tmp_parser.get_text().lower() for err in [
        "500", "internal server error", "proxy error", "nginx", "html error", "bad gateway"
    ]):
        raise Exception("❌ 페이지 로드 실패: 서버 오류")
    await page.wait_for("div.place_business_list_wrapper", timeout=10)
    return page

async def load_page_with_wait(browser, url):
    page = await browser.get(url)

    tmp_parser = BeautifulSoup(await page.get_content(), "lxml")
    if any(err in tmp_parser.get_text().lower() for err in [
        "500", "internal server error", "proxy error", "nginx", "html error", "bad gateway"
    ]):
        time.sleep(3)
        raise Exception("❌ 페이지 로드 실패: 서버 오류")
    await page.wait_for("div.place_business_list_wrapper", timeout=10)
    return page


async def load_page_with_wait02(browser, url):
    page = await browser.get(url)

    tmp_parser = BeautifulSoup(await page.get_content(), "lxml")
    if any(err in tmp_parser.get_text().lower() for err in [
        "500", "internal server error", "proxy error", "nginx", "html error", "bad gateway"
    ]):
        time.sleep(3)
        raise Exception("❌ 페이지 로드 실패: 서버 오류")
    await page.wait_for("div.place_fixed_maintab", timeout=10)
    return page


async def with_retry(func, retries=5, delay=1):
    for attempt in range(retries):
        try:
            return await func()
        except Exception as e:
            print(f"⚠️ 재시도 {attempt+1}/{retries} 실패: {e}")
            await asyncio.sleep(delay)
    raise Exception("❌ 모든 재시도 실패")

async def wait_for_selector_with_retry(page, selector, timeout=10, interval=1):
    max_attempts = int(timeout / interval)
    for attempt in range(max_attempts):
        try:
            node = await page.select_all(selector)
            if node:
                return node
        except Exception:
            pass
        await asyncio.sleep(interval)
    raise TimeoutError(f"❌ '{selector}' 로딩 실패 (timeout={timeout}s)")

def extract_dynamic_place_info(soup: BeautifulSoup):
    place_info = {}
    title_block = soup.select("div.zD5Nm > div#_title")
    info_blocks = soup.select("div.PIbes > div.O8qbU")
    if title_block:
        title = title_block[0].get_text(strip=True)
        place_info["title"] = title

    for block in info_blocks:
        key_elem = block.select_one("strong > span.place_blind")
        value_block = block.select_one("div.vV_z_")
        if not key_elem or not value_block:
            continue
        key = key_elem.get_text(strip=True)
        if key == "주소":
            addr = value_block.select_one("span.LDgIH")
            place_info["주소"] = addr.text.strip() if addr else None
        elif key == "전화번호":
            phone = value_block.select_one("span.xlx7Q")
            place_info["전화번호"] = phone.text.strip() if phone else None
        elif key == "영업시간":
            status = value_block.select_one("em")
            hours = value_block.select_one("time")
            place_info["영업상태"] = status.text.strip() if status else None
            place_info["영업시간"] = hours.text.strip() if hours else None
        elif key == "홈페이지":
            links = value_block.select("a.place_bluelink")
            place_info["홈페이지들"] = [a["href"] for a in links if a.get("href")]
        else:
            place_info[key] = value_block.get_text(strip=True)
    return place_info

def append_to_json_file(data, filepath):
    # 파일이 있으면 기존 데이터 로드
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            try:
                existing = json.load(f)
            except json.JSONDecodeError:
                existing = []
    else:
        existing = []

    # 중복 방지 (title 기준)
    titles = {entry.get("title") for entry in existing}
    if data.get("title") not in titles:
        existing.append(data)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)
        print(f"📦 저장 완료: {data['title']}")
    else:
        print(f"⚠️ 중복으로 저장 건너뜀: {data['title']}")

async def crawler(start_index, end_index):
    restaurant_infos = load_restaurant_subset(start_index, end_index)
    print(f"🔍 총 {len(restaurant_infos)}건을 처리합니다. 범위: {start_index} ~ {end_index}")

    if not restaurant_infos:
        print("❌ 데이터베이스에서 가게 정보를 불러오지 못했습니다.")
        return

    print(f"ℹ️ {len(restaurant_infos)}개 가게에 대한 크롤러를 시작합니다...")
    if not os.path.exists("screenshots"):
        os.makedirs("screenshots")

    system = platform.platform()
    arch = platform.machine()
    executable = None

    print("시스템 정보 확인")
    print(f"시스템: {system}")
    print(f"아키텍처: {arch}")

    if system != "mac" and arch in ("aarch64", "arm64"):
        print("ARM64 환경 감지")
        if os.path.exists("/usr/bin/ungoogled-chromium"):
            executable = "/usr/bin/ungoogled-chromium"
        elif os.path.exists("/usr/bin/chromium"):
            executable = "/usr/bin/chromium"

    try:
        browser = await zd.start(
            browser_executable_path=executable,
            browser_args=[
                "--disable-gpu",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-software-rasterizer",
                "--disable-extensions",
                "--disable-infobars",
                "--disable-web-security",
                "--disable-background-networking",
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding",
                "--disable-setuid-sandbox",
                "--no-first-run",
                "--no-zygote",
            ],
            )
        print("✅ Zendriver 시작 완료.")
        success, fail, need_check = 0, 0, 0

        for index, (business_name, road_address) in enumerate(restaurant_infos):
            try:
                search_query = make_search_query(business_name, road_address)
                encoded_query = urllib.parse.quote(search_query)
                mob_url = f"https://m.place.naver.com/restaurant/list?query={encoded_query}&x=126&y=37"
                print(f"🔗 [{index+1}] {search_query}")
                print(f"🔗 [{index+1}] {search_query} URL: {mob_url}")

                page = await with_retry(lambda: load_page_with_wait(browser, mob_url), retries=5, delay=3)
                await with_retry(lambda: page.wait_for("div.place_business_list_wrapper", timeout=10))

                soup = BeautifulSoup(await page.get_content(), "lxml")
                if soup.select("div[class='FYvSc']") or "조건에 맞는 업체가 없습니다" in soup.get_text():
                    print(f"❌ [{index+1}] {search_query} 검색 결과 없음")
                    await page.save_screenshot(os.path.join(SCREENSHOT_DIR, f"no_store_{sanitize_filename(business_name)}.png"))
                    need_check += 1
                    continue

                a_tags = soup.select("div.place_business_list_wrapper > ul > li a[href]")
                href_list = [a['href'] for a in a_tags]
                valid_links = list(set(
                    re.match(r"^/restaurant/\d+", href).group(0)
                    for href in href_list if re.match(r"^/restaurant/\d+", href)
                ))


                if not valid_links:
                    print(f"⚠️ [{index+1}] {search_query} 링크 없음")
                    need_check += 1
                    continue

                print(f"🔗 [{index+1}] {search_query} {len(valid_links)}개 유효 링크 발견")
                print(f"🔗 [{index+1}] {search_query} {valid_links[:len(valid_links)]}")
                unique_links = list(set(valid_links))

                if len(unique_links) > 1:
                    print(f"⚠️ [{index+1}] {search_query} 1차 검색 유사도 다중 상점 발견: {unique_links}")
                    await page.save_screenshot(os.path.join(SCREENSHOT_DIR, f"multiple_stores_{sanitize_filename(business_name)}.png"))
                    need_check += 1
                    continue

                #await with_retry(lambda: page.get(f"https://m.place.naver.com{valid_links[0]}"))
                page = await with_retry(lambda: load_page_with_wait02(browser, f"https://m.place.naver.com{valid_links[0]}"), retries=5, delay=1)

                print(f"🔗 [{index+1}] {search_query} {valid_links[0]} 로딩 완료")
                print(f"🔗 [{index+1}] {search_query} 2차 URL: https://m.place.naver.com{valid_links[0]}")
                await wait_for_selector_with_retry(page, "div.place_fixed_maintab", timeout=15)

                parser = BeautifulSoup(await page.get_content(), "lxml")
                main_tab = parser.select_one('div[class="place_fixed_maintab"]')
                if main_tab:
                    href_list = [
                        a['href']
                        for a in main_tab.select('a[href]')
                        if a['href'].strip() and not a['href'].strip().startswith('#')
                    ]
                    print(f"🍽️ [{index+1}] {search_query} 유효한 링크 개수: {len(href_list)}")
                    print(f"🍽️ [{index+1}] {search_query} 링크: {href_list}")
                else:
                    print(f"❌ [{index+1}] {search_query} place_fixed_maintab not found.")

                place_info = extract_dynamic_place_info(parser)

                data = {
                    "query": search_query,
                    "title": business_name,
                    "place_info": place_info,
                    "unique_links": unique_links,
                    "tab_list": href_list,
                    "url": mob_url
                }

                append_to_json_file(data, output_path)
                success += 1
                
                if (index + 1) % 50 == 0:
                    await page.close()
                    await browser.stop()
                    print("🔄 메모리 유출 방지 브라우저 재시작 중...")
                    await browser.stop()
                    browser = await zd.start(
                        browser_executable_path=executable,
                        browser_args=[
                            "--disable-gpu",
                            "--no-sandbox",
                            "--disable-dev-shm-usage",
                            "--disable-software-rasterizer",
                            "--disable-extensions",
                            "--disable-infobars",
                            "--disable-web-security",
                            "--disable-background-networking",
                            "--disable-background-timer-throttling",
                            "--disable-backgrounding-occluded-windows",
                            "--disable-renderer-backgrounding",
                            "--disable-setuid-sandbox",
                            "--no-first-run",
                            "--no-zygote",
                        ],
                    )
                    print("✅ 메모리 유출 방지 브라우저 재시작 완료.")


            except Exception as e:
                print(f"❌ 오류: {e}")
                fail += 1
                continue

        print(f"\n✅ 완료: {success} / ❌ 실패: {fail} / ⚠️ 확인 필요: {need_check}")

    finally:
        await browser.stop()
        print("🛑 Zendriver 종료 완료")



if __name__ == "__main__":
    start = int(os.environ.get("START_INDEX", sys.argv[1] if len(sys.argv) > 1 else 0))
    end = int(os.environ.get("END_INDEX", sys.argv[2] if len(sys.argv) > 2 else 100))
    print(f"📦 현재 컨테이너는 {start} ~ {end} 범위를 담당합니다.")
    asyncio.run(crawler(start, end))
    print("🛑 크롤러가 종료되었습니다.")