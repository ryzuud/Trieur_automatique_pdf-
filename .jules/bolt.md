## 2024-05-18 - [Limit PDF extraction to first 5 pages]
**Learning:** Extracting text from full PDFs using `pdfplumber` scales linearly with the number of pages, leading to massive delays and resource exhaustion on large files. Since the application only needs to identify providers using keywords on the invoice header, scanning beyond the first few pages is unnecessary.
**Action:** Always consider early termination when processing potentially large documents if the required information is likely at the beginning. Use `MAX_PAGES_TO_EXTRACT` to prevent DoS-like resource usage on parsing.
