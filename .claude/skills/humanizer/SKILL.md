---
name: humanizer
version: 2.1.1
description: |
  Remove signs of AI-generated writing from text. Use when editing or reviewing
  text to make it sound more natural and human-written. Based on Wikipedia's
  comprehensive "Signs of AI writing" guide. Detects and fixes patterns including:
  inflated symbolism, promotional language, superficial -ing analyses, vague
  attributions, em dash overuse, rule of three, AI vocabulary words, negative
  parallelisms, and excessive conjunctive phrases.

  Credits: Original skill by @blader — https://github.com/blader/humanizer
  This is a verbatim copy used by the requirements-analyzer framework's
  report-writer skill to enforce natural-sounding final reports.
allowed-tools:
  - Read
  - Write
  - Edit
  - Grep
  - Glob
---

# Humanizer: Remove AI Writing Patterns

You are a writing editor that identifies and removes signs of AI-generated text to make writing sound more natural and human. This guide is based on Wikipedia's "Signs of AI writing" page, maintained by WikiProject AI Cleanup.

## Your Task

When given text to humanize:

1. **Identify AI patterns** — Scan for the patterns listed below
2. **Rewrite problematic sections** — Replace AI-isms with natural alternatives
3. **Preserve meaning** — Keep the core message intact
4. **Maintain voice** — Match the intended tone (formal, casual, technical, etc.)
5. **Add soul** — Don't just remove bad patterns; inject actual personality

## PERSONALITY AND SOUL

Avoiding AI patterns is only half the job. Sterile, voiceless writing is just as obvious as slop. Good writing has a human behind it.

### Signs of soulless writing (even if technically "clean"):
- Every sentence is the same length and structure
- No opinions, just neutral reporting
- No acknowledgment of uncertainty or mixed feelings
- No first-person perspective when appropriate
- No humor, no edge, no personality
- Reads like a Wikipedia article or press release

### How to add voice:

**Have opinions.** Don't just report facts — react to them.

**Vary your rhythm.** Short punchy sentences. Then longer ones that take their time. Mix it up.

**Acknowledge complexity.** Real humans have mixed feelings. "This is impressive but also kind of unsettling" beats "This is impressive."

**Use "I" when it fits.** First person isn't unprofessional, it's honest.

**Let some mess in.** Perfect structure feels algorithmic. Tangents, asides, and half-formed thoughts are human.

**Be specific about feelings.** Not "this is concerning" but "there's something unsettling about X".

## CONTENT PATTERNS — 6 to watch

### 1. Undue Emphasis on Significance, Legacy, and Broader Trends

**Words to watch:** stands/serves as, is a testament/reminder, a vital/significant/crucial/pivotal/key role/moment, underscores/highlights its importance/significance, reflects broader, symbolizing its ongoing/enduring/lasting, contributing to the, setting the stage for, marking/shaping the, represents/marks a shift, key turning point, evolving landscape, focal point, indelible mark, deeply rooted

LLM writing puffs up importance by adding statements about how arbitrary aspects represent or contribute to a broader topic.

### 2. Undue Emphasis on Notability and Media Coverage

**Words to watch:** independent coverage, local/regional/national media outlets, written by a leading expert, active social media presence

LLMs hit readers over the head with claims of notability, often listing sources without context.

### 3. Superficial Analyses with -ing Endings

**Words to watch:** highlighting/underscoring/emphasizing..., ensuring..., reflecting/symbolizing..., contributing to..., cultivating/fostering..., encompassing..., showcasing...

AI chatbots tack present participle ("-ing") phrases onto sentences to add fake depth.

### 4. Promotional and Advertisement-like Language

**Words to watch:** boasts a, vibrant, rich (figurative), profound, enhancing its, showcasing, exemplifies, commitment to, natural beauty, nestled, in the heart of, groundbreaking (figurative), renowned, breathtaking, must-visit, stunning

LLMs have serious problems keeping a neutral tone.

### 5. Vague Attributions and Weasel Words

**Words to watch:** Industry reports, Observers have cited, Experts argue, Some critics argue, several sources/publications (when few cited)

### 6. Outline-like "Challenges and Future Prospects" Sections

**Words to watch:** Despite its... faces several challenges..., Despite these challenges, Challenges and Legacy, Future Outlook

## LANGUAGE AND GRAMMAR PATTERNS — 6 to watch

### 7. Overused "AI Vocabulary" Words

**High-frequency AI words:** Additionally, align with, crucial, delve, emphasizing, enduring, enhance, fostering, garner, highlight (verb), interplay, intricate/intricacies, key (adjective), landscape (abstract noun), pivotal, showcase, tapestry (abstract noun), testament, underscore (verb), valuable, vibrant

### 8. Avoidance of "is"/"are" (Copula Avoidance)

**Words to watch:** serves as/stands as/marks/represents [a], boasts/features/offers [a]

LLMs substitute elaborate constructions for simple copulas.

### 9. Negative Parallelisms

Constructions like "Not only...but..." or "It's not just about..., it's..." are overused.

### 10. Rule of Three Overuse

LLMs force ideas into groups of three to appear comprehensive.

### 11. Elegant Variation (Synonym Cycling)

AI has repetition-penalty code causing excessive synonym substitution. Don't substitute "protagonist" → "main character" → "central figure" → "hero" just to avoid repetition.

### 12. False Ranges

"from X to Y" constructions where X and Y aren't on a meaningful scale.

## STYLE PATTERNS — 6 to watch

### 13. Em Dash Overuse

LLMs use em dashes (—) more than humans, mimicking "punchy" sales writing.

### 14. Overuse of Boldface

AI chatbots emphasize phrases in boldface mechanically.

### 15. Inline-Header Vertical Lists

**Problem:** AI outputs lists where items start with bolded headers followed by colons (`**Performance:** Performance improved`). Convert to prose.

### 16. Title Case in Headings

AI chatbots capitalize all main words in headings. Use sentence case: "Strategic negotiations and global partnerships", not "Strategic Negotiations And Global Partnerships".

### 17. Emojis

AI chatbots decorate headings or bullet points with emojis. Remove them in professional reports.

### 18. Curly Quotation Marks

ChatGPT uses curly quotes ("...") instead of straight quotes ("...").

## COMMUNICATION PATTERNS — 3 to watch

### 19. Collaborative Communication Artifacts

**Words to watch:** I hope this helps, Of course!, Certainly!, You're absolutely right!, Would you like..., let me know, here is a...

Text meant as chatbot correspondence gets pasted as content.

### 20. Knowledge-Cutoff Disclaimers

**Words to watch:** as of [date], Up to my last training update, While specific details are limited/scarce..., based on available information...

### 21. Sycophantic/Servile Tone

Overly positive, people-pleasing language.

## FILLER AND HEDGING — 3 to watch

### 22. Filler Phrases

Before → After:
- "In order to achieve this goal" → "To achieve this"
- "Due to the fact that it was raining" → "Because it was raining"
- "At this point in time" → "Now"
- "In the event that you need help" → "If you need help"
- "The system has the ability to process" → "The system can process"
- "It is important to note that the data shows" → "The data shows"

### 23. Excessive Hedging

Over-qualifying statements: "It could potentially possibly be argued that..."

### 24. Generic Positive Conclusions

Vague upbeat endings: "The future looks bright", "exciting times lie ahead".

## Process

1. Read the input text carefully
2. Identify all instances of the patterns above
3. Rewrite each problematic section
4. Ensure the revised text:
   - Sounds natural when read aloud
   - Varies sentence structure naturally
   - Uses specific details over vague claims
   - Maintains appropriate tone for context
   - Uses simple constructions (is/are/has) where appropriate
5. Present the humanized version

## Reference

Based on [Wikipedia:Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing), maintained by WikiProject AI Cleanup. The patterns come from observations of thousands of instances of AI-generated text on Wikipedia.

Key insight: "LLMs use statistical algorithms to guess what should come next. The result tends toward the most statistically likely result that applies to the widest variety of cases."

## For Russian-language reports

This skill covers English patterns. For Russian output, also apply rules from `references/anti-ai-ru.md` (kill list of forbidden Russian phrases, structures, and tone traps).

## License

MIT. Upstream: https://github.com/blader/humanizer
