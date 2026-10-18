def test_openapi_lists_core_routes(client):
    spec = client.get("/openapi.json").json()
    paths = spec["paths"].keys()
    for p in ["/v1/auth/verify-otp", "/v1/consultations/intake",
              "/v1/doctors", "/v1/doctor/queue",
              "/v1/prescriptions/{prescription_id}/consent", "/v1/pharmacy/inbox"]:
        assert p in paths
