# Prompt: Analyze a paper from papers.csv

## Instructions

1. Open `data/papers.csv`.
2. Select papers to analyze depending on the mode:
   - **Default (no extra instructions):** starting from the top (most recent date), take all consecutive rows where `processed` = `0` and `downloaded` = `1`. Stop at the first row where `processed` = `1`.
   - **Backfill (older papers):** if the user asks to analyze older/past papers without specifying exact dates, find the most recent calendar month that has unprocessed rows (`processed` = `0`, `downloaded` = `1`) and process all such rows within that month. If the user specifies a particular date range, month, or arxiv_id(s), use that filter instead.
3. For each selected row:
   - Open the corresponding PDF from `papers/originals/{arxiv_id}.pdf`.
   - If `papers/figures/{arxiv_id}.json` exists, read the figure captions and pick the one that best illustrates the model architecture or pipeline (look for "architecture", "framework", "pipeline", "overview" in the caption). Use its `url` for the `![architecture]({url})` line in the template (after Tags, before Summary). If no JSON or no suitable figure — omit the image line.
   - Analyze the paper following the template below.
   - Save the result (in English) to `papers/analysis/{arxiv_id}.md`.
   - Translate the entire analysis into Russian and save to `papers/analysis_ru/{arxiv_id}.md`.

**Formatting rules:**
- Do NOT use LaTeX math notation (`$...$`, `\(...\)`, `\[...\]`) anywhere in the output. Confluence cannot render it.
- Write formulas in plain text or Unicode: `v = ε − z_video`, `L_total = L_rec + λ · L_adv`, `t > (1 − τ_inj) · T`.
- Use subscript/superscript words instead of LaTeX: `x_input` not `$x_{\text{input}}$`.
- Greek letters: use Unicode characters (α, β, γ, λ, ε, τ, θ) or spell them out.

---

## Analysis template (output .md file format)

```markdown
# {title}

- **arXiv:** [{arxiv_id}]({url})
- **Date:** {date}
- **Authors:** {authors}
- **Code:** {code_url or "not available"}

---

## Recommendation: {score}/10

<!-- DO NOT write any explanation for the score — output ONLY the number.
     Internally evaluate these four factors equally to arrive at the score:
     1. Topic relevance — how close is the paper to talking head generation,
        lip sync, face reenactment, portrait animation, or 3D face reconstruction?
     2. Novelty — does it introduce a new approach, architecture, or idea?
     3. Results — does it achieve SOTA or a significant improvement in metrics / visual quality?
     4. Real-time capability — can the method run in real-time (≥25 FPS)
        or near real-time (≥15 FPS)? Methods that are far from real-time
        should score lower on this axis.
     Each factor contributes ~2.5 points to the final 10-point score.
     See the scoring guide at the end of this prompt. -->

---

## Tags

{Comma-separated, 5–20 tags. Use hyphens instead of spaces (e.g. "talking-head", not "talking head"). Include:
- the model/method name itself (e.g. GeoDiff4D, OmniHuman, KlingAvatar…)
- task type (talking-head, lip-sync, face-reenactment, portrait-animation, tts, voice-conversion…)
- modalities (audio-driven, text-driven, image-driven, video-driven)
- key methods/architectures and novelty (diffusion, GAN, NeRF, 3DGS, transformer, flow-matching, joint-image-normal-diffusion, pose-free-encoder…)
- representation type (2D, 3D, mesh, point-cloud, implicit)
- important properties (real-time, one-shot, few-shot, zero-shot, emotion-control, multilingual)
- competitor/baseline names (SadTalker, Wav2Lip, LivePortrait, AniPortrait…)}

---

![architecture]({url_of_best_figure})

<!-- Pick the figure that best illustrates the model architecture or pipeline overview.
     Open papers/figures/{arxiv_id}.json — it contains a list of figures with "caption" and "url".
     Read the captions to find the most relevant one (e.g. "overall pipeline", "architecture",
     "framework overview", "model structure"). Use its "url" value above.
     If no figures JSON exists or no suitable figure is found, omit this line entirely. -->

---

## Summary

{2–4 sentences: what the method does, input/output, core idea.}

---

## Novelty / Key Contributions

{3–5 bullet points: how it differs from existing approaches, key technical innovations.}

---

## Model Architecture

{Description of the structure:
- Main components/modules and their roles
- Generative model type (diffusion, GAN, autoregressive, flow…)
- How audio/text/image is encoded
- How lip sync, identity preservation, and emotion control are achieved
- Pipeline overview: input → module 1 → module 2 → … → output}

---

## Datasets

| Name | Type | Size | Purpose |
|------|------|------|---------|
| {name} | {video / image / audio / multimodal} | {hours of video / clip count / image count} | {train / eval / test} |

{Note if proprietary/custom data is used.}

---

## Key Results

{2–4 sentences in plain language. Describe:
- what benchmarks / datasets were used for evaluation
- where the method excels compared to previous best (and by how much, qualitatively)
- where it falls short or performs on par
- any notable qualitative findings (e.g. "handles extreme poses better")
Avoid raw metric tables — summarize the numbers into human-readable conclusions.}

---

## Competitors / Baselines

{Bullet list of 2–3 closest / most well-known competitors. For each:
- **Name (year):** one sentence — how this paper's method differs or improves.}

---

## Input / Output

- **Input:** {single portrait + audio / video + audio / text + …}
- **Output:** {talking head video / 3D avatar / frame sequence / …}
- **Resolution:** {512×512 / 256×256 / …}
- **Real-time:** {yes / no, FPS if stated}

---

## Limitations

{What the authors note as limitations + your own observations:
- quality on challenging angles/lighting
- dependence on input data quality
- computational requirements
- generalization (cross-identity, unseen poses)
- ethical considerations}

---

## Training Details

- **Framework:** {PyTorch / JAX / …}
- **GPU:** {type and count}
- **Training time:** {if mentioned}
- **Pre-trained models used:** {face encoder, audio encoder, etc.}
```

---

## Relevance scoring guide

| Score | Description |
|-------|-------------|
| 9–10 | Directly on topic, novel architecture or SOTA results, real-time or near real-time capable. |
| 7–8 | Closely related task, good results/novelty. May lack real-time capability or be slightly off-topic. |
| 5–6 | Adjacent area or partially applicable. Significant gaps in at least two factors. |
| 3–4 | Indirectly related, limited novelty, no real-time consideration. |
| 1–2 | Minimal connection to the topic. |

Factors (each ~2.5 pts): **topic relevance**, **novelty**, **results quality**, **real-time capability**.
