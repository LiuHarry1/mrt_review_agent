"""
测试 Azure OpenAI 代理服务器配置
用于找出正确的部署名称、API版本和端点格式
"""
import os
import httpx
import json
from typing import List, Tuple

# 代理服务器配置
PROXY_BASE_URL = "https://api.gptsapi.net"
API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")

# 如果未设置，尝试从命令行参数获取
import sys
if not API_KEY and len(sys.argv) > 1:
    API_KEY = sys.argv[1]

# 注意：代理服务器使用 OpenAI 兼容格式，不是 Azure OpenAI 格式
# base_url 应该是 "https://api.gptsapi.net/v1"
# 使用 Authorization: Bearer 头部，不是 api-key 头部

# 要测试的 API 版本
API_VERSIONS = [
    "2024-06-01",
    "2024-02-15-preview",
    "2023-12-01-preview",
    "2023-05-15",
    "2023-03-15-preview",
]

# 要测试的部署名称
DEPLOYMENT_NAMES = [
    "gpt-4-turbo",
    "gpt-4",
    "gpt-35-turbo",
    "gpt-3.5-turbo",
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4-32k",
    "gpt-4-turbo-preview",
]

# 要测试的端点格式（OpenAI 兼容格式）
ENDPOINT_FORMATS = [
    "/v1/chat/completions",  # OpenAI 标准格式
    "/chat/completions",     # 简化格式
    "/v/openai/deployments/{deployment}/chat/completions",  # Azure 格式（测试）
    "/openai/deployments/{deployment}/chat/completions",    # Azure 格式（测试）
]


def test_endpoint(
    base_url: str,
    deployment_name: str,
    api_version: str,
    endpoint_format: str,
    api_key: str,
    timeout: float = 10.0
) -> Tuple[bool, int, str]:
    """
    测试一个端点配置
    
    Returns:
        (success, status_code, message)
    """
    try:
        # 判断是 OpenAI 格式还是 Azure 格式
        is_openai_format = endpoint_format in ["/v1/chat/completions", "/chat/completions"]
        
        # 构建 URL
        if is_openai_format:
            # OpenAI 格式：base_url 应该包含 /v1
            if base_url.endswith("/v1"):
                url = f"{base_url}{endpoint_format}"
            else:
                url = f"{base_url}/v1{endpoint_format}" if endpoint_format.startswith("/") else f"{base_url}/v1/{endpoint_format}"
        else:
            # Azure 格式
            if "{deployment}" in endpoint_format:
                endpoint = endpoint_format.format(deployment=deployment_name)
            else:
                endpoint = endpoint_format
            
            if "?" in endpoint:
                url = f"{base_url}{endpoint}&api-version={api_version}"
            else:
                url = f"{base_url}{endpoint}?api-version={api_version}"
        
        # 准备请求头
        if is_openai_format:
            # OpenAI 格式：使用 Bearer token
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
        else:
            # Azure 格式：使用 api-key
            headers = {
                "api-key": api_key,
                "Content-Type": "application/json"
            }
        
        # 准备请求体
        if is_openai_format:
            # OpenAI 格式：模型名称在请求体中
            payload = {
                "model": deployment_name,
                "messages": [
                    {"role": "user", "content": "Hello"}
                ],
                "max_tokens": 5
            }
        else:
            # Azure 格式：部署名称在 URL 中
            payload = {
                "messages": [
                    {"role": "user", "content": "Hello"}
                ],
                "max_tokens": 5
            }
        
        # 发送请求
        with httpx.Client(timeout=timeout) as client:
            response = client.post(url, json=payload, headers=headers)
            
            status_code = response.status_code
            response_text = response.text[:500] if response.text else ""
            
            if status_code == 200:
                try:
                    data = response.json()
                    return (True, status_code, f"成功! 响应: {json.dumps(data, ensure_ascii=False)[:200]}")
                except:
                    return (True, status_code, f"成功! 响应: {response_text[:200]}")
            elif status_code == 401:
                return (False, status_code, "认证失败 - API Key 可能不正确")
            elif status_code == 404:
                return (False, status_code, "404 - 部署名称或端点格式不正确")
            elif status_code == 400:
                return (False, status_code, f"400 - 请求格式错误: {response_text[:200]}")
            else:
                return (False, status_code, f"错误 {status_code}: {response_text[:200]}")
                
    except httpx.TimeoutException:
        return (False, 0, "请求超时")
    except httpx.ConnectError as e:
        return (False, 0, f"连接错误: {str(e)[:200]}")
    except Exception as e:
        return (False, 0, f"异常: {str(e)[:200]}")


def main():
    """主测试函数"""
    print("=" * 80)
    print("Azure OpenAI 代理服务器配置测试")
    print("=" * 80)
    print(f"代理服务器: {PROXY_BASE_URL}")
    print(f"API Key: {'已设置' if API_KEY else '未设置 (需要设置 AZURE_OPENAI_API_KEY 环境变量)'}")
    print()
    
    if not API_KEY:
        print("错误: 请设置 AZURE_OPENAI_API_KEY 环境变量")
        print("例如: set AZURE_OPENAI_API_KEY=your-api-key")
        print("或者: python test_azure_proxy.py your-api-key")
        print()
        print("提示: 如果你有 API Key，可以:")
        print("  1. 设置环境变量: set AZURE_OPENAI_API_KEY=your-key")
        print("  2. 或作为参数传递: python test_azure_proxy.py your-key")
        return
    
    print("开始测试...")
    print()
    
    successful_configs = []
    
    # 首先测试 OpenAI 兼容格式（最可能）
    print("1. 测试 OpenAI 兼容格式（最可能）...")
    print("-" * 80)
    
    openai_configs = [
        ("gpt-4-turbo", "", "/v1/chat/completions"),
        ("gpt-4", "", "/v1/chat/completions"),
        ("gpt-3.5-turbo", "", "/v1/chat/completions"),
        ("gpt-4o", "", "/v1/chat/completions"),
        ("gpt-4o-mini", "", "/v1/chat/completions"),
    ]
    
    for deployment, api_version, endpoint_format in openai_configs:
        print(f"测试: {deployment} | OpenAI格式 | {endpoint_format}")
        success, status, message = test_endpoint(
            PROXY_BASE_URL, deployment, api_version, endpoint_format, API_KEY
        )
        status_symbol = "[OK]" if success else "[FAIL]"
        print(f"  结果: {status_symbol} - {message}")
        if success:
            successful_configs.append((deployment, "OpenAI格式", endpoint_format))
        print()
    
    # 然后测试 Azure 格式
    print("2. 测试 Azure OpenAI 格式...")
    print("-" * 80)
    
    azure_configs = [
        ("gpt-4-turbo", "2024-02-15-preview", "/v/openai/deployments/{deployment}/chat/completions"),
        ("gpt-4", "2024-02-15-preview", "/v/openai/deployments/{deployment}/chat/completions"),
        ("gpt-35-turbo", "2024-02-15-preview", "/v/openai/deployments/{deployment}/chat/completions"),
        ("gpt-4-turbo", "2024-06-01", "/v/openai/deployments/{deployment}/chat/completions"),
        ("gpt-4", "2024-06-01", "/v/openai/deployments/{deployment}/chat/completions"),
    ]
    
    for deployment, api_version, endpoint_format in azure_configs:
        print(f"测试: {deployment} | {api_version} | {endpoint_format}")
        success, status, message = test_endpoint(
            PROXY_BASE_URL, deployment, api_version, endpoint_format, API_KEY
        )
        status_symbol = "[OK]" if success else "[FAIL]"
        print(f"  结果: {status_symbol} - {message}")
        if success:
            successful_configs.append((deployment, api_version, endpoint_format))
        print()
    
    # 如果常见配置都失败，进行完整测试
    if not successful_configs:
        print("2. 常见配置都失败，进行完整测试...")
        print("-" * 80)
        
        for api_version in API_VERSIONS:
            print(f"\n测试 API 版本: {api_version}")
            for deployment in DEPLOYMENT_NAMES:
                for endpoint_format in ENDPOINT_FORMATS:
                    success, status, message = test_endpoint(
                        PROXY_BASE_URL, deployment, api_version, endpoint_format, API_KEY, timeout=5.0
                    )
                    if success:
                        print(f"  [OK] 成功: {deployment} | {endpoint_format}")
                        print(f"    响应: {message}")
                        successful_configs.append((deployment, api_version, endpoint_format))
                    elif status == 401:
                        print(f"  [!] 认证问题: {deployment} | {endpoint_format}")
                        break  # API Key 错误，跳过其他测试
                    # 其他错误不打印，避免输出过多
    
    # 总结
    print()
    print("=" * 80)
    print("测试总结")
    print("=" * 80)
    
    if successful_configs:
        print(f"找到 {len(successful_configs)} 个可用配置:")
        for deployment, api_version, endpoint_format in successful_configs:
            print(f"  - 部署名称: {deployment}")
            print(f"    API 版本: {api_version}")
            print(f"    端点格式: {endpoint_format}")
            print(f"    完整URL: {PROXY_BASE_URL}{endpoint_format.format(deployment=deployment)}?api-version={api_version}")
            print()
    else:
        print("未找到可用配置。可能的原因:")
        print("  1. API Key 不正确")
        print("  2. 代理服务器端点格式完全不同")
        print("  3. 需要不同的认证方式")
        print("  4. 代理服务器暂时不可用")
        print()
        print("建议:")
        print("  - 检查 API Key 是否正确")
        print("  - 联系代理服务提供商获取正确的配置信息")
        print("  - 查看代理服务器的 API 文档")


if __name__ == "__main__":
    main()

