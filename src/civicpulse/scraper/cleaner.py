import re

from bs4 import BeautifulSoup, Tag


class ContentCleaner:
    def clean(self, html: str) -> str:
        soup = BeautifulSoup(html, "lxml")

        for tag_name in ("nav", "header", "footer", "script", "style", "aside", "noscript"):
            for tag in soup.find_all(tag_name):
                tag.decompose()

        removable_classes = re.compile(
            r"breadcrumb|site-header|site-footer|menu|sidebar|pagination|skip-link"
        )
        for tag in soup.find_all(class_=removable_classes):
            tag.decompose()

        main = (
            soup.find("main")
            or soup.find("article")
            or soup.find(id="content")
            or soup.find("div", class_=re.compile(r"field.items|page.content|main.content"))
            or soup.find("body")
        )

        if not isinstance(main, Tag):
            return ""

        parts: list[str] = []
        for child in main.children:
            if not isinstance(child, Tag):
                continue
            if child.name in ("h1", "h2"):
                parts.append("# " + child.get_text(strip=True))
            elif child.name in ("h3", "h4"):
                parts.append("## " + child.get_text(strip=True))
            else:
                parts.append(child.get_text(separator=" ", strip=True))

        text = "\n\n".join(parts)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()
