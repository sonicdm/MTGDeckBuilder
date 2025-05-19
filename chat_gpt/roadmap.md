Absolutely. Here's the **updated roadmap.md** reflecting what you've implemented so far, what’s in progress, and what’s planned — based on our discussions.

---

### ✅ Roadmap: MTG Deckbuilder Project

#### ✅ **Completed Features**

* [x] `DeckConfig` refactored into a full-featured Pydantic model.
* [x] `DeckConfig` includes `to_yaml`, `from_yaml`, and validation logic.
* [x] YAML parsing via UI with Gradio 5.x compatibility.
* [x] UI sync functions: `apply_config_to_ui` and `extract_config_from_ui` — now robust and fully aware of all DeckConfig fields.
* [x] Gradio DataFrame bug fixed by converting dicts (e.g. `priority_text`) into lists of lists.
* [x] Standard-legal test YAML (`yaml_test_template.yaml`) built for consistent unit testing.
* [x] Deckbuilder tab fully connected to config loading, saving, and deck generation.

---

### 🛠️ **In Progress / Near Term**

* [ ] Add a **Deck View tab** to browse cards in the currently built deck.
* [ ] Add a **Deck Manager tab** to list saved decks (edit, delete, open).
* [ ] Add **Settings tab** for runtime options (e.g., enable experimental features).
* [ ] Let users enter an **OpenAI API key** via the Settings tab.
* [ ] Update UI to support editing previously saved decks (reload config into builder).
* [ ] UI field mapping for newly added DeckConfig fields (where needed).
* [ ] ChatGPT integration for:

  * [ ] Reviewing current deck config (feedback/suggestions).
  * [ ] Generating a new deck from natural language prompts.

---

### 🚧 **Future Plans**

* [ ] Add deck exporting (e.g. text list, .csv, .json, .arena format).
* [ ] Card image integration via **Scryfall** API.
* [ ] In-app card search browser with filters (colors, type, mana cost, etc.).
* [ ] Smart inventory analysis — what to prioritize based on collection stats.
* [ ] AI Assistant: "Build me a mono-black deck using only my collection and favoring recursion themes."

---

Would you like me to update `roadmap.md` directly for download, or just append this as the file content for you to save?
