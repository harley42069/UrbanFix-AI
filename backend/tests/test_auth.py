from __future__ import annotations


def test_register_login_me_flow(client):
    register_payload = {
        "email": "auth1@example.com",
        "username": "auth_user",
        "password": "Secret123!",
        "full_name": "Auth User",
        "role": "citizen",
    }

    reg = client.post("/api/v1/auth/register", json=register_payload)
    assert reg.status_code == 201, reg.text
    reg_body = reg.json()
    assert reg_body["success"] is True
    assert reg_body["data"]["email"] == register_payload["email"]

    login = client.post(
        "/api/v1/auth/login",
        data={"username": register_payload["username"], "password": register_payload["password"]},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200, login.text
    login_body = login.json()
    token = login_body["data"]["access_token"]
    assert token

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200, me.text
    me_body = me.json()
    assert me_body["success"] is True
    assert me_body["data"]["username"] == register_payload["username"]
