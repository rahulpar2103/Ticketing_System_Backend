import requests

def test_login_and_fetch():
    base_url = "http://localhost:8000"
    print("[*] Testing FastAPI Backend Connection & CORS Headers...")
    
    # 1. Test Login Endpoint
    login_url = f"{base_url}/auth/login"
    payload = {
        "username": "rahul",
        "password": "Password@123"
    }
    
    try:
        # FastAPI OAuth2 expects form urlencoded payload
        response = requests.post(login_url, data=payload)
        print(f"[*] Response Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("[+] Login Successful!")
            data = response.json()
            token = data.get("access_token")
            print(f"[+] Access Token received: {token[:15]}...")
            
            # 2. Test fetching user info
            me_url = f"{base_url}/users/me"
            headers = {"Authorization": f"Bearer {token}"}
            me_response = requests.get(me_url, headers=headers)
            if me_response.status_code == 200:
                print(f"[+] Current User profile: {me_response.json()}")
            else:
                print(f"[-] Failed to fetch /users/me: {me_response.status_code}")
                
            # 3. Test fetching tickets list
            tickets_url = f"{base_url}/tickets"
            tickets_response = requests.get(tickets_url, headers=headers)
            if tickets_response.status_code == 200:
                tickets_data = tickets_response.json()
                print(f"[+] Total Tickets available: {tickets_data.get('total')}")
                print(f"[+] First ticket in queue: {tickets_data.get('items')[0]['title']}")
            else:
                print(f"[-] Failed to fetch tickets list: {tickets_response.status_code}")
        else:
            print(f"[-] Login Failed. Status Code: {response.status_code}")
            print(f"[-] Detail: {response.text}")
            
    except Exception as e:
        print(f"[-] Connection Error: {e}")

if __name__ == "__main__":
    test_login_and_fetch()
