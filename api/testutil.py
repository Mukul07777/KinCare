"""Test helper: a real server-issued session for an account id, sent as a Bearer token (the way an API client would)."""
import main
import roles as roles_mod
import sessions

_tokens: dict[tuple[str, str], str] = {}


def auth_as(account: str, kind: str = "user", roles: tuple[str, ...] = ()) -> dict:
    """Headers that make requests act as `account`. Signed-in ("user") by default, since sharing features need it.
    `roles` are granted (active) first, e.g. roles=("pharmacist",)."""
    for r in roles:
        if r not in roles_mod.of(main.conn, account):
            roles_mod.grant(main.conn, account, r, "test")
    key = (account, kind)
    if key not in _tokens:
        _tokens[key] = sessions.create(main.conn, account, kind)
    # X-Device-Id is ignored by the server now (a test proves it); it stays only so a test can read which account it acts as.
    return {"Authorization": f"Bearer {_tokens[key]}", "X-Device-Id": account}
