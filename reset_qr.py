import requests

ACCESS_TOKEN = "EAAVZBobCt7AcBO8trGDsP8t4bTe2mRA7sNdZCQ346G9ZANwsi4CVdKM5MwYwaPlirOHAcpDQ63LoHxPfx81tN9h2SUIHc1LUeEByCzS8eQGH2J7wwe9tqAxZAdwr4SxkXGku2l7imqWY16qemnlOBrjYH3dMjN4gamsTikIROudOL3ScvBzwkuShhth0rR9P"
PHONE_NUMBER_ID = "241683569037594"
GRAPH_API_VERSION = "v22.0"
GRAPH_API_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{PHONE_NUMBER_ID}/message_qrdls"

HEADERS = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Content-Type": "application/json"
}

def get_qr_codes():
    response = requests.get(GRAPH_API_URL, headers=HEADERS)
    if response.status_code == 200:
        data = response.json()
        qr_codes = data.get("data", [])
        print(f"Retrieved {len(qr_codes)} QR codes.")
        return qr_codes
    else:
        print(f"Error retrieving QR codes: {response.json()}")
        return []

def delete_qr_codes():
    qr_codes = get_qr_codes()
    if not qr_codes:
        print("No QR codes found.")
        return
    for qr in qr_codes:
        qr_id = qr.get("code")
        if qr_id:
            delete_url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{PHONE_NUMBER_ID}/message_qrdls?code={qr_id}"
            response = requests.delete(delete_url, headers=HEADERS)
            if response.status_code == 200:
                print(f"Deleted QR Code: {qr_id}")
            else:
                print(f"Failed to delete QR Code {qr_id}: {response.json()}")

delete_qr_codes()
