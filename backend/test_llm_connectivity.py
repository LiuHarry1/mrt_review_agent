#!/usr/bin/env python3
"""
Test script for LLM provider connectivity.
Usage:
    python test_llm_connectivity.py          # Test all providers
    python test_llm_connectivity.py qwen     # Test Qwen only
    python test_llm_connectivity.py azure    # Test Azure OpenAI only
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.llm.factory import LLMClientFactory
from app.llm.provider import LLMProvider, LLMError
from dotenv import load_dotenv

def test_qwen():
    """Test Qwen (DashScope) provider."""
    print("\n" + "="*60)
    print("Testing Qwen (DashScope)")
    print("="*60)
    
    try:
        # Check API key
        api_key = os.getenv("DASHSCOPE_API_KEY") or os.getenv("QWEN_API_KEY")
        if not api_key:
            print("✗ No API key found. Set DASHSCOPE_API_KEY or QWEN_API_KEY")
            return False
        
        # Create client
        client = LLMClientFactory.create_client(LLMProvider.QWEN)
        print(f"✓ Client created")
        print(f"  Model: {client.model}")
        
        # Test request
        print("\nSending test request...")
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say 'Hello' in one word."}
        ]
        
        payload = client._normalize_payload(messages, model=client.model)
        payload["max_tokens"] = 20
        
        response_data = client._make_request("chat/completions", payload)
        response_text = client._extract_response(response_data)
        
        print(f"✓ Request successful!")
        print(f"  Response: {response_text}")
        return True
        
    except LLMError as e:
        print(f"✗ Error: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False


def test_azure():
    """Test Azure OpenAI provider."""
    print("\n" + "="*60)
    print("Testing Azure OpenAI")
    print("="*60)
    
    try:
        # Check API key
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        
        if not api_key:
            print("✗ No API key found. Set AZURE_OPENAI_API_KEY")
            return False
        if not endpoint:
            print("✗ No endpoint found. Set AZURE_OPENAI_ENDPOINT")
            return False
        
        # Create client
        client = LLMClientFactory.create_client(LLMProvider.AZURE_OPENAI)
        print(f"✓ Client created")
        print(f"  Model: {client.model}")
        print(f"  Endpoint: {endpoint}")
        
        # Test request
        print("\nSending test request...")
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say 'Hello' in one word."}
        ]
        
        payload = client._normalize_payload(messages, model=client.model)
        payload["max_tokens"] = 20
        
        response_data = client._make_request("chat/completions", payload)
        response_text = client._extract_response(response_data)
        
        print(f"✓ Request successful!")
        print(f"  Response: {response_text}")
        return True
        
    except LLMError as e:
        print(f"✗ Error: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False


def main():
    """Main function."""
    if len(sys.argv) > 1:
        provider = sys.argv[1].lower()
        
        if provider == "qwen":
            success = test_qwen()
            sys.exit(0 if success else 1)
        elif provider in ["azure", "azure_openai"]:
            success = test_azure()
            sys.exit(0 if success else 1)
        else:
            print(f"Unknown provider: {provider}")
            print("Usage: python test_llm_connectivity.py [qwen|azure]")
            sys.exit(1)
    else:
        # Test all providers
        print("="*60)
        print("LLM Provider Connectivity Test")
        print("="*60)
        
        results = []
        results.append(("Qwen", test_qwen()))
        results.append(("Azure OpenAI", test_azure()))
        
        # Summary
        print("\n" + "="*60)
        print("Summary")
        print("="*60)
        for name, success in results:
            status = "✓" if success else "✗"
            print(f"{status} {name}: {'Success' if success else 'Failed'}")
        
        success_count = sum(1 for _, success in results if success)
        print(f"\n{success_count}/{len(results)} providers working")
        
        sys.exit(0 if success_count > 0 else 1)


if __name__ == "__main__":
    # main()
    #load env file
    load_dotenv()
    test_qwen()
