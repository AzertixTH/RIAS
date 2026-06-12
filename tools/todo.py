_TODO: list[dict] = []
_COUNTER = 0


def todo(action: str, text: str = None, id: int = None) -> str:
    global _COUNTER

    if action == "add":
        if not text:
            return "text is verplicht voor add"
        _COUNTER += 1
        _TODO.append({"id": _COUNTER, "text": text, "done": False})
        return f"[{_COUNTER}] Toegevoegd: {text}"

    if action == "list":
        if not _TODO:
            return "Geen taken."
        lines = []
        for t in _TODO:
            mark = "✓" if t["done"] else "○"
            lines.append(f"[{t['id']}] {mark} {t['text']}")
        return "\n".join(lines)

    if action == "done":
        if id is None:
            return "id is verplicht voor done"
        for t in _TODO:
            if t["id"] == id:
                t["done"] = True
                return f"[{id}] Afgevinkt: {t['text']}"
        return f"Taak {id} niet gevonden."

    if action == "remove":
        if id is None:
            return "id is verplicht voor remove"
        for i, t in enumerate(_TODO):
            if t["id"] == id:
                removed = _TODO.pop(i)
                return f"[{id}] Verwijderd: {removed['text']}"
        return f"Taak {id} niet gevonden."

    if action == "clear":
        _TODO.clear()
        return "Alle taken gewist."

    return f"Onbekende actie: {action}. Gebruik: add, list, done, remove, clear"
