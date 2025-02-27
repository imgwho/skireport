import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from PIL import Image

def scrape_and_split_screenshot_snow_data():
    """抓取日本滑雪场降雪数据并将表格截图分割成两部分"""
    url = "https://www.j2ski.com/snow_forecast/Japan/"
    
    try:
        # 获取当前日期作为文件名前缀
        date_prefix = datetime.now().strftime('%Y-%m-%d')
        
        # 设置Chrome为移动设备模式
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # 无头模式
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=390,2000")  # 增加高度以容纳完整表格
        chrome_options.add_argument("--no-sandbox")  # 在GitHub Actions中需要
        chrome_options.add_argument("--disable-dev-shm-usage")  # 在GitHub Actions中需要
        
        # 设置移动设备模拟
        mobile_emulation = {
            "deviceMetrics": { "width": 390, "height": 2000, "pixelRatio": 3.0 },
            "userAgent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1"
        }
        chrome_options.add_experimental_option("mobileEmulation", mobile_emulation)
        
        # 初始化WebDriver
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(url)
        
        # 等待页面加载
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "topResortsSnow"))
        )
        
        # 找到目标表格
        table = driver.find_element(By.ID, "topResortsSnow")
        
        # 获取表格尺寸
        table_height = table.size['height']
        table_width = table.size['width']
        
        # 调整窗口大小以适应表格
        driver.set_window_size(table_width + 50, table_height + 200)
        
        # 滚动到表格位置
        driver.execute_script("arguments[0].scrollIntoView();", table)
        time.sleep(1)  # 等待滚动完成
        
        # 创建输出目录
        output_dir = 'japan_snow_reports'
        os.makedirs(output_dir, exist_ok=True)
        
        # 截图整个表格 - 添加日期前缀
        full_screenshot_path = os.path.join(output_dir, f'{date_prefix}_topResortsSnow_mobile_full.png')
        table.screenshot(full_screenshot_path)
        
        # 获取表格中所有行
        rows = driver.find_elements(By.CSS_SELECTOR, "#topResortsSnow tr")
        
        # 获取表格数据用于描述
        html_content = driver.page_source
        driver.quit()
        
        # 使用PIL分割图片
        img = Image.open(full_screenshot_path)
        width, height = img.size
        
        # 计算表格的行数
        total_rows = len(rows)
        
        # 使用BeautifulSoup解析HTML获取表格结构
        soup = BeautifulSoup(html_content, 'html.parser')
        table_html = soup.find('table', id='topResortsSnow')
        tr_elements = table_html.find_all('tr')
        
        # 使用PIL直接处理图片
        # 首先，我们需要确定表格的总高度
        img_height = img.size[1]
        
        # 我们希望在图片高度的中间位置附近找到一个行边界
        middle_height = img_height // 2
        
        # 使用固定的行高估计（根据实际表格调整）
        estimated_row_height = img_height // total_rows
        
        # 计算中间行的索引
        middle_row_index = middle_height // estimated_row_height
        
        # 确保middle_row_index在有效范围内
        middle_row_index = min(middle_row_index, total_rows - 1)
        middle_row_index = max(middle_row_index, 1)  # 至少从第二行开始分割
        
        # 计算分割点（在中间行的底部）
        split_point = middle_row_index * estimated_row_height
        
        # 确保分割点在有效范围内
        split_point = min(split_point, img_height - 100)  # 确保第二部分至少有100像素高
        split_point = max(split_point, 100)  # 确保第一部分至少有100像素高
        
        # 分割图片 - 添加日期前缀
        img1 = img.crop((0, 0, width, split_point))
        img2 = img.crop((0, split_point, width, height))
        
        # 保存分割后的图片 - 添加日期前缀
        img1_path = os.path.join(output_dir, f'{date_prefix}_topResortsSnow_part1.png')
        img2_path = os.path.join(output_dir, f'{date_prefix}_topResortsSnow_part2.png')
        img1.save(img1_path)
        img2.save(img2_path)
        
        # 提取表头和表格数据
        headers = []
        for th in table_html.find_all('th'):
            headers.append(th.text.strip())
        
        # 提取表格数据
        rows_data = []
        for tr in table_html.find_all('tr')[1:]:  # 跳过表头行
            row = []
            for td in tr.find_all('td'):
                row.append(td.text.strip())
            if row:  # 确保行不为空
                rows_data.append(row)
        
        # 创建DataFrame
        df = pd.DataFrame(rows_data, columns=headers)
        
        # 生成描述
        description = generate_description(df)
        
        # 保存描述 - 添加日期前缀
        description_path = os.path.join(output_dir, f'{date_prefix}_topResortsSnow_description.txt')
        with open(description_path, 'w', encoding='utf-8') as f:
            f.write(description)
        
        print(f"截图和描述已保存到 {output_dir} 目录")
        return [img1_path, img2_path], description, date_prefix
        
    except Exception as e:
        print(f"抓取数据时出错: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None

def generate_description(df):
    """根据表格数据生成描述"""
    try:
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        # 确定正确的列名
        resort_col = df.columns[0]  # 通常是第一列
        snow_7day_col = None
        snow_48hr_col = None
        
        # 查找降雪量列
        for col in df.columns:
            if '7 Day' in col:
                snow_7day_col = col
            if '48 Hr' in col:
                snow_48hr_col = col
        
        if not snow_7day_col:
            return f"无法找到7天降雪量数据列，请检查表格结构"
        
        # 提取数字部分
        df[snow_7day_col] = df[snow_7day_col].str.extract(r'(\d+)').astype(float)
        if snow_48hr_col:
            df[snow_48hr_col] = df[snow_48hr_col].str.extract(r'(\d+)').astype(float)
        
        # 计算统计数据
        max_snow_7day = df[snow_7day_col].max()
        max_resort_7day = df.loc[df[snow_7day_col].idxmax()][resort_col]
        avg_snow_7day = df[snow_7day_col].mean()
        total_resorts = len(df)
        resorts_with_snow = len(df[df[snow_7day_col] > 0])
        
        # 获取前5名滑雪场（7天降雪量）
        top5_7day = df.sort_values(snow_7day_col, ascending=False).head(5)
        
        # 生成描述文本
        description = f"""日本滑雪场降雪预报分析 ({current_date})

根据J2Ski网站的最新数据，日本滑雪场的降雪预报如下：

- 共收录{total_resorts}个日本滑雪场的降雪预报
- 其中{resorts_with_snow}个滑雪场未来7天预计有降雪
- 未来7天最大降雪量为{max_snow_7day}厘米，位于{max_resort_7day}
- 平均预计7天降雪量为{avg_snow_7day:.1f}厘米

未来7天降雪量前5名滑雪场：
"""
        
        for i, (_, row) in enumerate(top5_7day.iterrows(), 1):
            description += f"{i}. {row[resort_col]}: {row[snow_7day_col]}厘米\n"
        
        # 如果有48小时降雪量数据，也添加相关描述
        if snow_48hr_col:
            max_snow_48hr = df[snow_48hr_col].max()
            max_resort_48hr = df.loc[df[snow_48hr_col].idxmax()][resort_col]
            avg_snow_48hr = df[snow_48hr_col].mean()
            resorts_with_snow_48hr = len(df[df[snow_48hr_col] > 0])
            
            # 获取前3名滑雪场（48小时降雪量）
            top3_48hr = df.sort_values(snow_48hr_col, ascending=False).head(3)
            
            description += f"\n未来48小时有{resorts_with_snow_48hr}个滑雪场预计有降雪"
            description += f"\n未来48小时最大降雪量为{max_snow_48hr}厘米，位于{max_resort_48hr}"
            description += f"\n平均预计48小时降雪量为{avg_snow_48hr:.1f}厘米"
            
            description += "\n\n未来48小时降雪量前3名滑雪场：\n"
            for i, (_, row) in enumerate(top3_48hr.iterrows(), 1):
                description += f"{i}. {row[resort_col]}: {row[snow_48hr_col]}厘米\n"
            
        description += "\n此数据截取自J2Ski网站，更新于" + current_date
        
        return description
        
    except Exception as e:
        return f"生成描述时出错: {str(e)}"

if __name__ == "__main__":
    screenshot_paths, description, date_prefix = scrape_and_split_screenshot_snow_data()
    if description:
        print("\n" + description)
        print(f"\n图片已保存为: {screenshot_paths}")
        print(f"\n描述文件已保存为: {date_prefix}_topResortsSnow_description.txt")
