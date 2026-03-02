from curl_cffi import requests
from bs4 import BeautifulSoup


def test_single_url():
    # 拿微樂客之前的一場活動來當測試標靶
    url = "https://willmusic.kktix.cc/events/5ac88777"

    print(f"🎯 準備狙擊網址: {url}")
    print("⏳ 正在與 Cloudflare 防火牆交涉中 (請稍候)...\n")

    try:
        # 🌟 升級偽裝兵器：從 chrome110 升級到 chrome120
        response = requests.get(url, impersonate="chrome120", timeout=15)

        print(f"📡 伺服器回傳狀態碼: {response.status_code}")

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            header = soup.find("h1")

            if header:
                print(f"🎉 成功穿透！抓到網頁標題: {header.text.strip()}")
            else:
                print("⚠️ 狀態碼是 200，但找不到標題！你可能被導向了「請驗證您是人類」的畫面。")
                print("以下是伺服器回傳的部分內容：")
                print(response.text[:500])
        else:
            print("❌ 被防火牆無情阻擋了。")

    except Exception as e:
        print("\n💥 發生底層網路崩潰錯誤！凶手在這裡：")
        print(e)


if __name__ == "__main__":
    test_single_url()
