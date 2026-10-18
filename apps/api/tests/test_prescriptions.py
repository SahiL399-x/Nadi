def test_consent_requires_at_least_one_pharmacy(client, patient_token):
    # craft a prescription id that does not exist is fine; validation happens before lookup
    h = {"Authorization": f"Bearer {patient_token}"}
    r = client.post("/v1/prescriptions/00000000-0000-0000-0000-000000000000/consent",
                    json={"pharmacyIds": []}, headers=h)
    assert r.status_code == 400
