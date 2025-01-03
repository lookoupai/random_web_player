import sys
import os
from typing import Union, Dict
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException
import random

app = FastAPI()

# 跨域处理
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],
)

def parse_video_line(line: str) -> Dict[str, str]:
    """
    解析格式为 'title:xxx,URL:xxx' 的行
    
    Args:
        line: 输入的文本行
        
    Returns:
        包含title和url的字典
        
    Raises:
        ValueError: 当行格式不正确时
    """
    try:
        parts = [part.strip() for part in line.split(',')]
        if len(parts) != 2:
            raise ValueError("行格式必须为 'title:xxx,URL:xxx'")
        
        title_part, url_part = parts
        if not title_part.startswith('title:') or not url_part.startswith('URL:'):
            raise ValueError("标题必须以'title:'开头，URL必须以'URL:'开头")
        
        title = title_part.split('title:', 1)[1].strip()
        url = url_part.split('URL:', 1)[1].strip()
        
        if not title or not url:
            raise ValueError("标题和URL不能为空")
            
        return {
            "title": title,
            "url": url
        }
    except Exception as e:
        raise ValueError(f"解析行时出错: {str(e)}")

def read_random_line(file_path: str) -> str:
    """
    从给定文件中读取随机一行
    
    Args:
        file_path: 文件路径
        
    Returns:
        随机选择的行
        
    Raises:
        HTTPException: 当文件不存在或为空时
    """
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="视频列表文件未找到")

    with open(file_path, 'r', encoding='utf-8') as file:
        lines = [line.strip() for line in file if line.strip()]

    if not lines:
        raise HTTPException(status_code=400, detail="视频列表文件为空")

    return random.choice(lines)

@app.get("/")
async def get_random_video_url() -> Dict[str, Union[str, dict]]:
    """
    返回随机视频信息的API端点
    
    Returns:
        包含状态和视频信息的字典
    """
    try:
        file_path = "./video_urls.txt"
        random_line = read_random_line(file_path)
        video_info = parse_video_line(random_line)
        return {
            "status": "success",
            "data": video_info
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"服务器错误: {str(e)}")
