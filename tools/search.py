from ddgs import DDGS


def web_search(query: str, max_results: int = 5) -> str:
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results, timelimit="m"))
            if not results:
                results = list(ddgs.text(query, max_results=max_results))

        if not results:
            return "Geen resultaten gevonden."

        lines = []
        for i, r in enumerate(results, 1):
            lines.append(f"[{i}] {r['title']}\n{r['href']}\n{r['body']}")

        return "\n\n".join(lines)

    except Exception as e:
        return f"Search error: {e}"
