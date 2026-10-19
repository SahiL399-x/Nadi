def test_doctor_can_add_and_list_notes(client, doctor_token, db):
    from sqlalchemy import select

    from app.models import Consultation, ConsultationStatus

    cid = str(
        db.scalar(
            select(Consultation.id).where(Consultation.status == ConsultationStatus.IN_PROGRESS)
        )
    )
    h = {"Authorization": f"Bearer {doctor_token}"}
    post = client.post(f"/v1/consultations/{cid}/notes", json={"text": "advised rest"}, headers=h)
    assert post.status_code == 200
    got = client.get(f"/v1/consultations/{cid}/notes", headers=h)
    assert got.status_code == 200
    assert any(n["text"] == "advised rest" for n in got.json())
