## 📝 Summary

Describe the change and why it is needed.

## 🎯 Scope Check

- [ ] This keeps HA Idleon read-only.
- [ ] This does not add Idleon login, Steam login, browser scraping, session scraping, or token scraping.
- [ ] This does not add write actions or services.
- [ ] This does not expose raw account JSON as entity attributes.
- [ ] Any new noisy entities are disabled by default.

## 🧪 Testing

- [ ] `ruff check .`
- [ ] `ruff format --check .`
- [ ] `python -m pytest`

## 🔐 Privacy

- [ ] No real Idleon account exports are included.
- [ ] No private URLs, tokens, cookies, usernames, or local file paths are included.
