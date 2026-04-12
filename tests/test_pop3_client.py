import unittest

from biztogmail_app.pop3_client import extract_message_id, pop_fetch_headers, pop_fetch_raw, pop_uidl_list


class FakePop:
    def uidl(self):
        return (
            b"+OK",
            [b"1 UID-001", b"invalid", b"two parts extra", b"X UID-002", b"2 UID-002"],
            0,
        )

    def retr(self, msg_num):
        return b"+OK", [f"Subject: Test {msg_num}".encode(), b"", b"body"], 0

    def top(self, msg_num, _lines):
        return b"+OK", [b"Message-ID: <abc@example.com>", b"Subject: Demo"], 0


class Pop3ClientTests(unittest.TestCase):
    def test_pop_uidl_list_ignores_malformed_rows(self):
        self.assertEqual(pop_uidl_list(FakePop()), [(1, "UID-001"), (2, "UID-002")])

    def test_pop_fetch_raw_joins_lines_with_crlf(self):
        raw = pop_fetch_raw(FakePop(), 3)
        self.assertEqual(raw, b"Subject: Test 3\r\n\r\nbody\r\n")

    def test_pop_fetch_headers_appends_header_terminator(self):
        headers = pop_fetch_headers(FakePop(), 1)
        self.assertEqual(headers, b"Message-ID: <abc@example.com>\r\nSubject: Demo\r\n\r\n")

    def test_extract_message_id_strips_angle_brackets(self):
        self.assertEqual(extract_message_id(b"Message-ID: <abc@example.com>\r\n\r\n"), "abc@example.com")

    def test_extract_message_id_returns_none_when_missing(self):
        self.assertIsNone(extract_message_id(b"Subject: Demo\r\n\r\n"))
