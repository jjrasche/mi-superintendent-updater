"""HTML compression utility for storage optimization"""
import re


def compress_html(html: str) -> str:
    """
    Compress HTML by removing unnecessary whitespace while preserving structure.

    This helps with storage while keeping HTML readable for debugging.

    Args:
        html: Raw HTML string

    Returns:
        Compressed HTML string (typically 30-50% smaller)
    """
    if not html:
        return html

    # Remove comments (<!-- ... -->)
    html = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)

    # Remove multiple whitespace/newlines (replace with single space)
    html = re.sub(r'\s+', ' ', html)

    # Remove whitespace between tags
    html = re.sub(r'>\s+<', '><', html)

    # Remove leading/trailing whitespace
    html = html.strip()

    return html


def decompress_html(compressed: str) -> str:
    """
    Decompress HTML (currently just returns as-is since compression is lossy).

    In future could add pretty-printing for readability.

    Args:
        compressed: Compressed HTML string

    Returns:
        Same string (decompression is identity function for now)
    """
    return compressed


def get_compression_ratio(original: str, compressed: str) -> float:
    """
    Calculate compression ratio.

    Args:
        original: Original HTML
        compressed: Compressed HTML

    Returns:
        Ratio (e.g., 0.65 means compressed is 65% of original size)
    """
    if not original:
        return 0.0
    return len(compressed) / len(original)
