"""Simple SSH tunnel connectivity test"""
import requests
from utils.ssh_tunnel import ssh_tunnel
from config import SSH_HOST, SSH_REMOTE_PORT

def test_tunnel():
    print("=" * 60)
    print("Simple SSH Tunnel Test")
    print("=" * 60)

    print(f"\n1. Opening SSH tunnel to {SSH_HOST}:{SSH_REMOTE_PORT}...")

    with ssh_tunnel() as local_url:
        print(f"   [OK] Tunnel established: {local_url}")

        print(f"\n2. Testing connection to Ollama API...")
        # Remove /api/generate from the URL for this test
        base_url = local_url.replace('/api/generate', '')

        try:
            # Test basic connectivity
            response = requests.get(f"{base_url}/api/tags", timeout=10)
            response.raise_for_status()

            data = response.json()
            print(f"   [OK] Connected successfully!")
            print(f"   Available models: {len(data.get('models', []))}")
            for model in data.get('models', [])[:3]:
                print(f"     - {model['name']}")

            print(f"\n3. Testing simple generation...")
            test_payload = {
                "model": "gpt-oss:120b",
                "prompt": "Say 'test' in JSON format: {\"result\": \"test\"}",
                "stream": False,
                "format": "json"
            }

            gen_response = requests.post(f"{base_url}/api/generate", json=test_payload, timeout=60)
            gen_response.raise_for_status()

            result = gen_response.json()
            print(f"   [OK] Generation test completed")
            print(f"   Response field: '{result.get('response', '')[:100]}'")
            print(f"   Thinking field: '{result.get('thinking', '')[:100]}'")

            print("\n" + "=" * 60)
            print("[OK] All connectivity tests passed!")
            print("=" * 60)
            return True

        except Exception as e:
            print(f"\n   [ERROR] {type(e).__name__}: {e}")
            print("\n" + "=" * 60)
            print("[FAILED] Connectivity test failed")
            print("=" * 60)
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    import sys
    success = test_tunnel()
    sys.exit(0 if success else 1)
