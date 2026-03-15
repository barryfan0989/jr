"""
台灣演唱會售票網站爬蟲優先順序清單
生成 Excel 檔案，列出各售票網站及其爬蟲優先等級
"""

import pandas as pd
from datetime import datetime

# 定義售票網站資料
ticket_sites = [
    # 等級 1 (最優先) - 主流大型售票平台
    {
        "網站名稱": "拓元售票系統",
        "網址": "https://tixcraft.com",
        "等級": 1,
        "市占率": "極高",
        "特色": "台灣最大售票平台，涵蓋演唱會、音樂會、展覽等",
        "技術難度": "中高",
        "備註": "有反爬蟲機制，需處理驗證碼和排隊系統",
        "建議爬取頻率": "每小時"
    },
    {
        "網站名稱": "KKTIX",
        "網址": "https://kktix.com",
        "等級": 1,
        "市占率": "高",
        "特色": "獨立音樂、小型演唱會、藝文活動",
        "技術難度": "中",
        "備註": "API 相對友善，資料結構清晰",
        "建議爬取頻率": "每小時"
    },
    {
        "網站名稱": "年代售票",
        "網址": "https://www.ticket.com.tw",
        "等級": 1,
        "市占率": "高",
        "特色": "大型演唱會、體育賽事",
        "技術難度": "中高",
        "備註": "老牌售票系統，資料豐富",
        "建議爬取頻率": "每小時"
    },
    {
        "網站名稱": "KLOOK 客路",
        "網址": "https://www.klook.com/zh-TW/experiences/city/1-taipei-things-to-do/tag/265-concerts",
        "等級": 1,
        "市占率": "高",
        "特色": "演唱會票券、旅遊體驗",
        "技術難度": "中",
        "備註": "國際平台，含台灣演唱會資訊",
        "建議爬取頻率": "每 2 小時"
    },
    
    # 等級 2 (次要) - 中型平台或特定類型
    {
        "網站名稱": "ibon 售票系統",
        "網址": "https://ticket.ibon.com.tw",
        "等級": 2,
        "市占率": "中高",
        "特色": "7-11 通路，演唱會、展覽、活動",
        "技術難度": "中",
        "備註": "整合超商通路，便利性高",
        "建議爬取頻率": "每 2 小時"
    },
    {
        "網站名稱": "全民購票網",
        "網址": "https://www.17life.com/event",
        "等級": 2,
        "市占率": "中",
        "特色": "結合團購，演唱會和活動票券",
        "技術難度": "低中",
        "備註": "偶有演唱會優惠票",
        "建議爬取頻率": "每 3 小時"
    },
    {
        "網站名稱": "Accupass 活動通",
        "網址": "https://www.accupass.com",
        "等級": 2,
        "市占率": "中",
        "特色": "藝文活動、講座、小型音樂會",
        "技術難度": "低中",
        "備註": "偏向文創和獨立活動",
        "建議爬取頻率": "每 3 小時"
    },
    {
        "網站名稱": "寬宏售票",
        "網址": "https://kham.com.tw",
        "等級": 2,
        "市占率": "中",
        "特色": "展覽、大型演唱會",
        "技術難度": "中",
        "備註": "主辦兼售票，內容獨家",
        "建議爬取頻率": "每 2 小時"
    },
    {
        "網站名稱": "FamiTicket 全家售票",
        "網址": "https://www.famiticket.com.tw",
        "等級": 2,
        "市占率": "中",
        "特色": "全家便利商店售票系統",
        "技術難度": "中",
        "備註": "部分演唱會獨家販售",
        "建議爬取頻率": "每 3 小時"
    },
    
    # 等級 3 (補充) - 小型或特定領域
    {
        "網站名稱": "Citytalk 城市通",
        "網址": "https://www.citytalk.tw",
        "等級": 3,
        "市占率": "中低",
        "特色": "藝文活動、小型演出",
        "技術難度": "低",
        "備註": "活動資訊整合平台",
        "建議爬取頻率": "每日"
    },
    {
        "網站名稱": "Indievox",
        "網址": "https://www.indievox.com",
        "等級": 3,
        "市占率": "低中",
        "特色": "獨立音樂演出",
        "技術難度": "低",
        "備註": "獨立樂團和小型 Live House",
        "建議爬取頻率": "每日"
    },
    {
        "網站名稱": "Opentix 兩廳院售票",
        "網址": "https://www.opentix.life",
        "等級": 3,
        "市占率": "中",
        "特色": "藝文表演、音樂會",
        "技術難度": "低中",
        "備註": "偏向古典音樂和藝文展演",
        "建議爬取頻率": "每日"
    },
    {
        "網站名稱": "博客來售票",
        "網址": "https://tickets.books.com.tw",
        "等級": 3,
        "市占率": "低中",
        "特色": "藝文展演、演唱會",
        "技術難度": "低中",
        "備註": "結合書店通路",
        "建議爬取頻率": "每日"
    },
    {
        "網站名稱": "GOMAJI 夠麻吉",
        "網址": "https://www.gomaji.com/ticket",
        "等級": 3,
        "市占率": "低",
        "特色": "團購票券",
        "技術難度": "低",
        "備註": "偶有演唱會團購票",
        "建議爬取頻率": "每日"
    },
    {
        "網站名稱": "udn售票網",
        "網址": "https://tickets.udn.com",
        "等級": 3,
        "市占率": "低中",
        "特色": "藝文活動、展覽",
        "技術難度": "低中",
        "備註": "聯合報系統合平台",
        "建議爬取頻率": "每日"
    }
]

def create_ticket_sites_excel():
    """建立售票網站清單 Excel 檔案"""
    
    # 建立 DataFrame
    df = pd.DataFrame(ticket_sites)
    
    # 依等級和市占率排序
    df = df.sort_values(['等級', '市占率'], ascending=[True, False])
    
    # 生成檔案名稱（包含日期）
    filename = f'台灣演唱會售票網站爬蟲清單_{datetime.now().strftime("%Y%m%d")}.xlsx'
    
    # 建立 Excel Writer
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        # 寫入主要清單
        df.to_excel(writer, sheet_name='售票網站清單', index=False)
        
        # 建立統計摘要
        summary_data = {
            '等級': [1, 2, 3],
            '網站數量': [
                len(df[df['等級'] == 1]),
                len(df[df['等級'] == 2]),
                len(df[df['等級'] == 3])
            ],
            '爬取策略': [
                '最高優先，每小時爬取',
                '次要優先，每 2-3 小時爬取',
                '補充資料，每日爬取'
            ]
        }
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='統計摘要', index=False)
        
        # 調整欄位寬度
        for sheet_name in writer.sheets:
            worksheet = writer.sheets[sheet_name]
            for column in worksheet.columns:
                max_length = 0
                column = [cell for cell in column]
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column[0].column_letter].width = adjusted_width
    
    print(f"✓ Excel 檔案已建立: {filename}")
    print(f"\n統計資訊:")
    print(f"  等級 1 (最高優先): {len(df[df['等級'] == 1])} 個網站")
    print(f"  等級 2 (次要): {len(df[df['等級'] == 2])} 個網站")
    print(f"  等級 3 (補充): {len(df[df['等級'] == 3])} 個網站")
    print(f"  總計: {len(df)} 個售票網站")
    
    return filename

def print_site_list():
    """在終端機顯示網站清單"""
    print("\n" + "="*80)
    print("台灣演唱會售票網站爬蟲優先順序清單")
    print("="*80 + "\n")
    
    for level in [1, 2, 3]:
        sites = [site for site in ticket_sites if site['等級'] == level]
        print(f"\n【等級 {level}】{'='*70}")
        for i, site in enumerate(sites, 1):
            print(f"\n{i}. {site['網站名稱']}")
            print(f"   網址: {site['網址']}")
            print(f"   市占率: {site['市占率']} | 技術難度: {site['技術難度']}")
            print(f"   特色: {site['特色']}")
            print(f"   爬取頻率: {site['建議爬取頻率']}")
            print(f"   備註: {site['備註']}")

if __name__ == "__main__":
    # 顯示清單
    print_site_list()
    
    print("\n" + "="*80)
    print("正在生成 Excel 檔案...")
    print("="*80 + "\n")
    
    # 建立 Excel 檔案
    filename = create_ticket_sites_excel()
    
    print(f"\n完成！請查看檔案: {filename}")
