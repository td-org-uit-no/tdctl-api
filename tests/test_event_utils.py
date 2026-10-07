import re
from datetime import datetime, timedelta, timezone

from app.api.utils import within_cancellation_window
from app.utils import event_utils
from app.utils.event_utils import (
    get_default_confirmation,
    get_default_waitlist_mail,
    num_of_confirmed_participants,
    num_of_waiting_list_participants,
    render_mail_template,
)


def _sample_event():
    return {
        "title": "Testarrangement",
        "date": datetime(2030, 5, 24, 16, 30),
        "address": "Testveien 1",
    }


# --- the late-cancellation window (gates contactEmail) ---------------------
# Pins the boundaries explicitly: this decides whether a non-admin is sent the
# event's contact address, so it should be a decision in code, not an accident.


def _event_starting_in(**delta):
    return {"date": datetime.now() + timedelta(**delta)}


def test_window_is_open_shortly_before_the_event():
    assert within_cancellation_window(_event_starting_in(hours=1))
    assert within_cancellation_window(_event_starting_in(hours=23, minutes=59))


def test_window_is_closed_beyond_24h_either_side():
    assert not within_cancellation_window(_event_starting_in(hours=25))
    assert not within_cancellation_window(_event_starting_in(hours=-25))
    assert not within_cancellation_window(_event_starting_in(days=30))
    assert not within_cancellation_window(_event_starting_in(days=-30))


def test_window_is_deliberately_symmetric():
    """Mirrors the client's Math.abs, so a just-started event is still "in".

    The modal does render for a joined event shortly after it starts, so both
    sides agree. If this is ever meant to be pre-event only, change the client
    too — otherwise the server hides an address the UI is rendering.
    """
    assert within_cancellation_window(_event_starting_in(hours=-1))
    assert within_cancellation_window(_event_starting_in(hours=-23, minutes=59))


def test_window_fails_closed_on_unusable_dates():
    for bad in (None, "2030-05-24 16:30", 12345, {}):
        assert not within_cancellation_window({"date": bad})
    assert not within_cancellation_window({})  # key absent
    # tz-aware would raise on subtraction with a naive now() — must not
    assert not within_cancellation_window(
        {"date": datetime.now(timezone.utc) + timedelta(hours=1)}
    )


def test_num_of_waiting_list_participants_counts_unconfirmed():
    participants = [
        {"confirmed": True},
        {"confirmed": False},
        {"confirmed": None},
        {"confirmed": True},
    ]
    assert num_of_waiting_list_participants(participants) == 2
    # waiting + confirmed must add up to the full participant list
    assert num_of_confirmed_participants(participants) == 2
    assert num_of_waiting_list_participants(
        participants) + num_of_confirmed_participants(participants) == 4


def test_num_of_waiting_list_participants_missing_key_counts_as_waiting():
    # uses .get(...) so participants missing the field are still on the waitlist
    assert num_of_waiting_list_participants([{"confirmed": True}, {}]) == 1


def test_num_of_waiting_list_participants_empty_list():
    assert num_of_waiting_list_participants([]) == 0


def test_num_of_waiting_list_participants_all_confirmed():
    assert num_of_waiting_list_participants(
        [{"confirmed": True}] * 4) == 0


def test_get_default_waitlist_mail_substitutes_all_placeholders():
    event = _sample_event()
    content = get_default_waitlist_mail(event)

    assert event["title"] in content
    assert event["date"].strftime("%d %B, %Y") in content
    assert event["date"].strftime("%H:%M") in content
    assert event["address"] in content

    # every $PLACEHOLDER$ must have been replaced
    assert re.findall(r"\$[A-Z_]+\$", content) == []
    assert "$EVENT_NAME$" not in content


def test_get_default_confirmation_substitutes_all_placeholders():
    event = _sample_event()
    content = get_default_confirmation(event)

    assert event["title"] in content
    assert event["address"] in content
    assert re.findall(r"\$[A-Z_]+\$", content) == []


def test_render_mail_template_backs_default_wrappers():
    event = _sample_event()

    assert render_mail_template(
        "event_waitlist.txt", event) == get_default_waitlist_mail(event)
    assert render_mail_template(
        "event_confirmation.txt", event) == get_default_confirmation(event)


def test_default_mails_use_event_contact_email_when_set():
    contact = "arrangement-kontakt@example.com"
    event = {**_sample_event(), "contactEmail": contact}

    for content in (get_default_confirmation(event),
                    get_default_waitlist_mail(event)):
        assert contact in content
        # the org fallback must not leak alongside the event's own contact
        assert "post@td-uit.no" not in content
        assert "$CONTACT$" not in content
        assert re.findall(r"\$[A-Z_]+\$", content) == []


def test_default_mails_fall_back_to_org_contact_when_unset():
    # contactEmail key absent entirely
    absent = _sample_event()
    assert "contactEmail" not in absent

    # contactEmail present but explicitly None
    explicit_none = {**_sample_event(), "contactEmail": None}

    for event in (absent, explicit_none):
        for content in (get_default_confirmation(event),
                        get_default_waitlist_mail(event)):
            assert "post@td-uit.no" in content
            assert "$CONTACT$" not in content
            assert re.findall(r"\$[A-Z_]+\$", content) == []


def test_default_mails_never_leave_a_placeholder():
    events = [
        _sample_event(),
        {**_sample_event(), "contactEmail": None},
        {**_sample_event(), "contactEmail": "kontakt@td-uit.no"},
    ]

    for event in events:
        for content in (get_default_confirmation(event),
                        get_default_waitlist_mail(event)):
            assert re.findall(r"\$[A-Z_]+\$", content) == []


# ---------------------------------------------------------------------------
# send_emails transport contract
# ---------------------------------------------------------------------------


def test_send_emails_returns_all_addresses_on_success(monkeypatch):
    sent = []
    monkeypatch.setattr(event_utils, "send_mail", sent.append)

    addresses = ["a@example.com", "b@example.com", "c@example.com"]
    result = event_utils.send_emails(addresses, "subject", "body")

    assert result == addresses
    # one real MailPayload per address, each addressed to a single recipient
    assert [p.to[0] for p in sent] == addresses
    for payload in sent:
        assert len(payload.to) == 1
        assert payload.subject == "subject"
        assert payload.content == "body"
        assert payload.sent_by == "no-reply@td-uit.no"


def test_send_emails_returns_only_survivors_when_one_raises(monkeypatch):
    attempted = []

    def fake_send_mail(payload):
        attempted.append(payload.to[0])
        if payload.to[0] == "bad@example.com":
            raise RuntimeError("simulated transport failure")

    monkeypatch.setattr(event_utils, "send_mail", fake_send_mail)

    addresses = ["a@example.com", "bad@example.com", "c@example.com"]
    result = event_utils.send_emails(addresses, "subject", "body")

    # the failed address is dropped, the rest survive, and every one of them
    # was attempted (the failure must not abort the batch)
    assert result == ["a@example.com", "c@example.com"]
    assert attempted == addresses


def test_send_emails_returns_empty_for_empty_list(monkeypatch):
    called = []
    monkeypatch.setattr(
        event_utils, "send_mail", lambda payload: called.append(payload))

    assert event_utils.send_emails([], "subject", "body") == []
    # nothing in, nothing out: the transport is never touched
    assert called == []
