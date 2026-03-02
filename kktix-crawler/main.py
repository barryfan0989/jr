from crawlers.kktix_crawler import get_global_events, scrape_kktix_event_detail


def main():
    # 使用標籤篩選網址 (音樂類 1, 7)
    base_url = "https://kktix.com/events?utf8=%E2%9C%93&search=&max_price=&min_price=&start_at=&end_at=&event_tag_ids_in=1%2C7"

    print("🚀 [系統] KKTIX 全自動掃蕩引擎啟動...")
    event_urls = get_global_events(base_url)

    if not event_urls:
        print("❌ [錯誤] 找不到活動網址。")
        return

    print(f"\n🎯 [系統] 偵測到 {len(event_urls)} 個音樂活動，開始深度解析...\n")

    success_count = 0
    for i, url in enumerate(event_urls, 1):
        try:
            event_data = scrape_kktix_event_detail(url)
            if event_data:
                success_count += 1
                print("=" * 70)
                print(f"📌 【活動名稱】: {event_data['event_name']}")
                print(f"   🎤 演出藝人: {event_data['artist']}")
                print(f"   📅 活動日期: {event_data['event_date']}")
                print(
                    f"   🔥 啟售時間: {event_data['sale_date']} ({event_data['sale_time_only']})")
                print(f"   📍 活動地點: {event_data['location']}")

                if event_data['tickets']:
                    print("   🎟️ 票種票價:")
                    for t in event_data['tickets']:
                        print(f"      - {t['ticket_type']}: ${t['price']}")
                print("=" * 70)
        except Exception as e:
            print(f"💥 錯誤: {e}")

    print(f"\n [完成] 共成功抓取 {success_count} 場活動！資訊已全數爬清楚。")


if __name__ == "__main__":
    main()
