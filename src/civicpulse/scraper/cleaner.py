"""
ContentCleaner — strips HTML boilerplate and extracts main content as plain text.

Removes <nav>, <header>, <footer>, <script>, <style> elements.
Extracts the main content area and converts to clean plain text.

Interface:
    cleaner = ContentCleaner()
    text: str = cleaner.clean(html)
"""


class ContentCleaner:
    """Strips navigation, headers, footers, and scripts from raw HTML."""

    def clean(self, html: str) -> str:
        """Return clean plain text extracted from the main content area of html."""
        raise NotImplementedError
