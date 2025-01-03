import requests
from bs4 import BeautifulSoup
import re
import json
import time
import os
from datetime import datetime
import argparse
import random
import urllib3

class VideoScraper:
    def __init__(self, full_update=False):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.base_url = 'https://www.ainidj.com'
        self.rss_url = 'https://www.ainidj.com/rss/index.xml'
        self.links_file = 'm3u8_links.txt'
        self.last_update_file = 'last_update.txt'
        self.full_update = full_update
        self.proxy_api = 'https://getproxy.bzpl.tech/get'
        self.current_proxy = None
        self.max_retries = 5  # 增加重试次数
        self.verify_url = 'https://www.baidu.com'  # 用于验证代理的URL
        
    def verify_proxy(self, proxy):
        """验证代理是否可用"""
        try:
            test_response = requests.get(
                self.verify_url,
                proxies=proxy,
                timeout=5,
                verify=False  # 不验证SSL证书
            )
            return test_response.status_code == 200
        except:
            return False

    def get_proxy(self):
        """获取新代理"""
        for _ in range(3):  # 最多尝试3次获取可用代理
            try:
                response = requests.get(self.proxy_api)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('proxy'):
                        proxy = data['proxy']
                        proxy_dict = {
                            'http': f'http://{proxy}',
                            'https': f'http://{proxy}'  # 使用http协议连接https网站
                        }
                        
                        # 验证代理是否可用
                        if self.verify_proxy(proxy_dict):
                            print(f"获取到可用代理: {proxy}")
                            return proxy_dict
                        else:
                            print(f"代理 {proxy} 验证失败，尝试获取新代理...")
                            time.sleep(1)
                            
            except Exception as e:
                print(f"获取代理出错: {e}")
                time.sleep(1)
        return None

    def make_request(self, url, method='get', retry_count=0):
        """发送请求，支持自动重试和代理切换"""
        try:
            # 第一次请求尝试不使用代理
            if retry_count == 0:
                try:
                    response = requests.get(
                        url,
                        headers=self.headers,
                        timeout=10,
                        verify=False  # 不验证SSL证书
                    )
                    if response.status_code == 200:
                        return response
                except:
                    print("直连失败，尝试使用代理...")
            
            # 使用代理
            if not self.current_proxy or retry_count > 0:
                self.current_proxy = self.get_proxy()
                if not self.current_proxy:
                    print("无法获取可用代理，尝试直连...")
                    response = requests.get(
                        url,
                        headers=self.headers,
                        timeout=10,
                        verify=False
                    )
                    return response
            
            response = requests.get(
                url,
                headers=self.headers,
                proxies=self.current_proxy,
                timeout=10,
                verify=False
            )
            return response
            
        except Exception as e:
            print(f"请求出错: {e}")
            if retry_count < self.max_retries:
                print(f"正在进行第 {retry_count + 1} 次重试...")
                time.sleep(2)  # 重试前等待
                return self.make_request(url, method, retry_count + 1)
            print("达到最大重试次数，尝试直连...")
            try:
                return requests.get(url, headers=self.headers, timeout=10, verify=False)
            except:
                return None

    def load_existing_links(self):
        """加载已存在的链接"""
        existing_links = set()
        if os.path.exists(self.links_file):
            with open(self.links_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        title = line.split(',URL:')[0].split('title:')[1]
                        existing_links.add(title)
        return existing_links

    def get_last_update_time(self):
        """获取上次更新时间"""
        if self.full_update:  # 如果是全量更新，返回None
            return None
        if os.path.exists(self.last_update_file):
            with open(self.last_update_file, 'r') as f:
                return f.read().strip()
        return None

    def save_last_update_time(self):
        """保存本次更新时间"""
        with open(self.last_update_file, 'w') as f:
            f.write(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
    def get_video_list(self):
        """获取视频列表"""
        try:
            response = self.make_request(self.rss_url)
            if not response:
                return []
                
            soup = BeautifulSoup(response.content, 'xml')
            items = soup.find_all('item')
            
            video_links = []
            last_update = self.get_last_update_time()
            
            for item in items:
                link = item.find('link').text
                pub_date = item.find('pubDate')
                if pub_date:
                    pub_date = pub_date.text.strip()
                
                if '/duanju/' in link:
                    if not self.full_update and last_update and pub_date:
                        try:
                            item_date = datetime.strptime(pub_date, '%Y-%m-%d %H:%M:%S')
                            last_update_date = datetime.strptime(last_update, '%Y-%m-%d %H:%M:%S')
                            if item_date <= last_update_date:
                                continue
                        except ValueError:
                            pass
                    video_links.append(link)
                    
            print(f"找到 {len(video_links)} 个{'全部' if self.full_update else '新'}视频链接")
            return video_links
        except Exception as e:
            print(f"获取视频列表出错: {e}")
            return []

    def get_play_pages(self, content_url):
        """获取播放页链接"""
        try:
            response = self.make_request(content_url)
            if not response:
                return []
                
            soup = BeautifulSoup(response.content, 'html.parser')
            
            play_links = []
            for a in soup.find_all('a', href=True):
                href = a.get('href')
                if href.startswith('/') and '1a' in href:
                    play_links.append(self.base_url + href)
            
            play_links = sorted(list(set(play_links)))
            print(f"在 {content_url} 中找到 {len(play_links)} 个播放页")
            return play_links
        except Exception as e:
            print(f"获取播放页链接出错: {e}")
            return []

    def extract_json_from_script(self, script_text):
        """从script标签中提取JSON数据"""
        try:
            # 使用更精确的正则表达式匹配JSON对象
            pattern = r'var\s+player_aaaa\s*=\s*({[^;]*})'
            match = re.search(pattern, script_text)
            if not match:
                return None
            
            json_str = match.group(1).strip()
            # 处理转义字符
            json_str = json_str.replace('\\"', '"')
            # 解析JSON
            return json.loads(json_str)
        except Exception as e:
            print(f"JSON提取错误: {e}")
            print(f"匹配到的文本: {match.group(1) if match else 'None'}")
            return None

    def get_m3u8_url(self, play_url):
        """获取m3u8地址和标题"""
        try:
            response = self.make_request(play_url)
            if not response:
                return None, None
                
            content = response.text
            
            soup = BeautifulSoup(content, 'html.parser')
            title_elem = soup.find('h1', {'class': 'page-title'})
            if not title_elem:
                print(f"在 {play_url} 中未找到标题")
                return None, None
            
            main_title = title_elem.find('a').text.strip()
            if not main_title:
                return None, None
            
            episode_elem = soup.find('span', {'class': 'btn-pc page-title'})
            episode_info = episode_elem.text.strip() if episode_elem else ""
            
            full_title = f"{main_title}{episode_info}" if episode_info else main_title
            
            scripts = soup.find_all('script')
            player_config = None
            
            for script in scripts:
                if script.string and 'player_aaaa' in script.string:
                    player_config = self.extract_json_from_script(script.string)
                    if player_config:
                        break
            
            if not player_config:
                print(f"在 {play_url} 中未找到有效的播放器配置")
                return None, None
            
            m3u8_url = player_config.get('url', '')
            if not m3u8_url:
                print(f"在播放器配置中未找到URL")
                return None, None
            
            m3u8_url = m3u8_url.replace('\\/', '/')
            
            print(f"成功获取到视频: {full_title}")
            print(f"M3U8地址: {m3u8_url}")
            return full_title, m3u8_url
            
        except Exception as e:
            print(f"获取m3u8地址出错: {e}")
            return None, None

    def save_to_file(self, data, filename='m3u8_links.txt'):
        """保存到文件"""
        try:
            if self.full_update and os.path.exists(filename):
                # 全量更新时，先备份原文件
                backup_file = f"{filename}.bak"
                os.rename(filename, backup_file)
                print(f"原文件已备份为: {backup_file}")
            
            mode = 'w' if self.full_update else 'a'  # 全量更新使用写入模式，增量更新使用追加模式
            existing_data = set()
            
            if not self.full_update and os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    existing_data = set(f.readlines())
            
            with open(filename, mode, encoding='utf-8') as f:
                count = 0
                for title, url in data:
                    line = f'title:{title},URL:{url}\n'
                    if self.full_update or line not in existing_data:
                        f.write(line)
                        count += 1
            
            print(f"成功{'写入' if self.full_update else '追加'} {count} 个视频链接到 {filename}")
        except Exception as e:
            print(f"保存文件出错: {e}")

    def run(self):
        """运行爬虫"""
        results = []
        video_links = self.get_video_list()
        existing_links = set() if self.full_update else self.load_existing_links()
        
        for content_url in video_links:
            print(f"\n处理视频页面: {content_url}")
            play_pages = self.get_play_pages(content_url)
            for play_url in play_pages:
                print(f"\n获取播放地址: {play_url}")
                title, m3u8_url = self.get_m3u8_url(play_url)
                if title and m3u8_url and (self.full_update or title not in existing_links):
                    results.append((title, m3u8_url))
                time.sleep(random.uniform(1, 3))  # 随机延时1-3秒
                
        if results:
            self.save_to_file(results)
            self.save_last_update_time()
        else:
            print("没有新的视频需要更新")

def main():
    # 禁用SSL警告
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    parser = argparse.ArgumentParser(description='视频链接爬虫')
    parser.add_argument('--full', action='store_true', help='进行全量更新（默认为增量更新）')
    args = parser.parse_args()
    
    scraper = VideoScraper(full_update=args.full)
    scraper.run()

if __name__ == '__main__':
    main()