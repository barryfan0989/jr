import pandas as pd
from crawlers.kktix_crawler import get_global_events, scrape_kktix_event_detail


def main():
    base_url = "https://kktix.com/events?utf8=%E2%9C%93&search=&max_price=&min_price=&start_at=&end_at=&event_tag_ids_in=1%2C7"

    print(" [系統] KKTIX 爬蟲啟動...")
    event_urls = get_global_events(base_url)

    if not event_urls:
        print(" [錯誤] 找不到活動網址。")
        return

    #  建立一個清單來儲存所有抓到的資料
    all_data = []

    print(f"\n [系統] 偵測到 {len(event_urls)} 個活動，開始解析並準備轉存 Excel...\n")

    for i, url in enumerate(event_urls, 1):
        try:
            event_data = scrape_kktix_event_detail(url)
            if event_data:
                # 處理票種與票價合併字串
                ticket_types = ", ".join(
                    [t['ticket_type'] for t in event_data['tickets']]) if event_data['tickets'] else "未取得"
                ticket_prices = ", ".join(
                    [str(t['price']) for t in event_data['tickets']]) if event_data['tickets'] else "未取得"

                #  整理成 Excel 的一列 (Row)
                row = {
                    "活動名稱": event_data['event_name'],
                    "演出藝人": event_data['artist'],
                    "活動日期": event_data['event_date'],
                    "啟售日期": event_data['sale_date'],
                    "啟售時間": event_data['sale_time_only'],
                    "活動地點": event_data['location'],
                    "活動地址": event_data.get('address', '未取得'),
                    "票種": ticket_types,
                    "票價": ticket_prices,
                    "活動連結": event_data['original_url']
                }
                all_data.append(row)
                print(
                    f" 已處理 ({i}/{len(event_urls)}): {event_data['event_name']}")

        except Exception as e:
            print(f"錯誤: {e}")

        #  產出 Excel 檔案並自動調整欄寬
    if all_data:
        df = pd.DataFrame(all_data)
        file_name = "kktix_events_report.xlsx"
        
        # 使用 ExcelWriter 來進行細部設定
        with pd.ExcelWriter(file_name, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Events')
            worksheet = writer.sheets['Events']
            
            # 遍歷每一欄，計算最長內容並設定欄寬
            for i, col in enumerate(df.columns):
                # 取得該欄位名稱的長度與內容中最長的長度
                column_len = df[col].astype(str).str.len().max()
                column_len = max(column_len, len(col)) + 4  # 額外加 4 格留白比較好看
                
                # 設定 Excel 的欄位寬度 (A 為 1, B 為 2...)
                worksheet.column_dimensions[chr(65 + i)].width = column_len
                
        print(f"\n [成功] Excel 報表已產出 (已自動優化欄寬)：{file_name}")
    else:
        print("\n查無資料，未產出檔案。")


if __name__ == "__main__":
    main()
