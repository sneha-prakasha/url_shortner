def test_signup_login_me(client):
    r = client.post("/api/auth/signup", json={"email": "A@Example.com", "password": "password123"})
    assert r.status_code == 201
    assert r.json()["user"]["email"] == "a@example.com"  # normalised to lower-case

    r = client.post("/api/auth/login", json={"email": "a@example.com", "password": "password123"})
    assert r.status_code == 200
    token = r.json()["access_token"]

    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["email"] == "a@example.com"


def test_duplicate_signup_rejected(client):
    body = {"email": "a@example.com", "password": "password123"}
    assert client.post("/api/auth/signup", json=body).status_code == 201
    assert client.post("/api/auth/signup", json=body).status_code == 409


def test_wrong_password_and_unknown_user_look_the_same(client):
    client.post("/api/auth/signup", json={"email": "a@example.com", "password": "password123"})
    wrong = client.post("/api/auth/login", json={"email": "a@example.com", "password": "nope-nope-1"})
    unknown = client.post("/api/auth/login", json={"email": "who@example.com", "password": "password123"})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()


def test_validation(client):
    assert client.post("/api/auth/signup", json={"email": "nope", "password": "password123"}).status_code == 422
    assert client.post("/api/auth/signup", json={"email": "a@b.com", "password": "short"}).status_code == 422


def test_protected_routes_need_token(client):
    assert client.get("/api/links").status_code == 401
    assert client.get("/api/overview").status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer garbage"}).status_code == 401
