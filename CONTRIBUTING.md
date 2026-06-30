# 🤝 Contributing

Thanks for helping improve HA Idleon.

## 🎯 Scope

This integration is intentionally small for v1. Contributions should preserve
the current boundaries:

- Read-only Home Assistant integration behavior.
- No Idleon credentials.
- No Steam login.
- No browser scraping.
- No session or token scraping.
- No write actions or services.
- No large raw account JSON attributes.

## 🧪 Development

Use Python 3.14.2 or newer.

```sh
python -m pip install -r requirements_test.txt
scripts/check
```

If your system does not provide `python`, use `python3`.

Individual checks are available as `scripts/lint`, `scripts/format-check`,
`scripts/type-check`, `scripts/test`, and `scripts/release-check`.

## 📬 Pull Requests

- Keep changes focused.
- Add or update tests for behavior changes.
- Update `README.md` or `WHATSNEW.md` when user-facing behavior changes.
- Do not include real Idleon account exports, private URLs, session data, or
  tokens in tests or issues.
