# Resolved Segment Compression

Summarize the supplied resolved customer-support conversation segment.

Your output must have exactly three parts, in this order:

1. Write ONE sentence naming what was resolved. Use a concise, past-tense
   outcome statement.

2. Write 3-6 bullet points containing the important facts from the segment.
   Preserve all concrete values verbatim, including:
   - identifiers such as order IDs and subscription IDs
   - monetary amounts
   - dates
   - status values
   - snake_case status tokens
   Do not round, normalize, paraphrase, reinterpret, or invent these values.

3. Write ONE sentence naming the resolution, meaning the terminal state reached
   by the resolved segment.

Rules:
- Keep the entire output at or below 500 tokens.
- Be concise and information-dense.
- Copy identifiers and amounts byte-exactly from the transcript.
- Preserve snake_case status tokens verbatim from the transcript.
- Do not invent information that is not present in the source segment.
- Do not add a preamble before the three-part structure.
- Do not add closing remarks after the resolution sentence.
- Do not use code fences.
- Return only the required three-part summary.