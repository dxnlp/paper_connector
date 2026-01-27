"""
LLM integration for taxonomy generation and paper tagging.
Supports multiple LLM providers via the llm module.
"""

import json
import re
from typing import Optional

from database import Paper, Taxonomy, PaperTags
from llm import get_provider, LLMError, ProviderName
from taxonomy import (
    get_contribution_tags,
    get_task_tags,
    get_modality_tags,
    find_best_match,
    CONTRIBUTION_TAXONOMY,
    TASK_TAXONOMY,
    MODALITY_TAXONOMY,
)

# Default taxonomy from curated taxonomy module
DEFAULT_CONTRIBUTION_TAGS = get_contribution_tags()
DEFAULT_TASK_TAGS = get_task_tags()
DEFAULT_MODALITY_TAGS = get_modality_tags()


async def call_llm(
    system_prompt: str,
    user_prompt: str,
    *,
    provider: Optional[ProviderName] = None,
    api_key: Optional[str] = None,
    **kwargs
) -> str:
    """
    Call the configured LLM provider.

    Args:
        system_prompt: System message for the LLM
        user_prompt: User message/query
        provider: Optional provider name override (minimax, openai, anthropic)
        api_key: Optional API key override
        **kwargs: Provider-specific options (e.g., model, temperature)

    Returns:
        LLM response text

    Raises:
        LLMError: On API or configuration errors
    """
    llm = get_provider(provider)
    response = await llm.complete(
        system_prompt,
        user_prompt,
        api_key=api_key,
        **kwargs
    )
    return response.content


async def call_minimax_llm(
    system_prompt: str,
    user_prompt: str,
    api_key: Optional[str] = None
) -> str:
    """
    Call MiniMax LLM API.

    This is a backward-compatible wrapper around call_llm().
    Prefer using call_llm() directly for new code.

    Args:
        system_prompt: System message for the LLM
        user_prompt: User message/query
        api_key: Optional API key (defaults to env var)

    Returns:
        LLM response text
    """
    return await call_llm(
        system_prompt,
        user_prompt,
        provider="minimax",
        api_key=api_key
    )


def extract_json_from_response(response: str) -> dict:
    """Extract JSON from LLM response, handling markdown code blocks."""
    # Try to find JSON in code blocks (greedy match for nested objects)
    json_match = re.search(r'```(?:json)?\s*(\{[\s\S]*\})\s*```', response)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # Try to find raw JSON
    try:
        # Find the first { and last }
        start = response.find('{')
        end = response.rfind('}')
        if start != -1 and end != -1:
            return json.loads(response[start:end + 1])
    except json.JSONDecodeError:
        pass

    return {}


async def generate_taxonomy(
    papers: list[Paper],
    month: str,
    api_key: Optional[str] = None,
    provider: Optional[ProviderName] = None
) -> Taxonomy:
    """
    Generate a taxonomy for the given papers using LLM.

    Args:
        papers: List of papers to analyze
        month: Month string (e.g., "2025-01")
        api_key: Optional API key
        provider: Optional provider name (minimax, openai, anthropic)

    Returns:
        Taxonomy object with contribution, task, and modality tags
    """
    system_prompt = """You are an expert ML/AI research curator. Your task is to analyze a collection of research papers and propose a structured taxonomy for categorizing them.

Output a JSON object with the following structure:
{
    "contribution_tags": ["tag1", "tag2", ...],  // 12-18 tags for primary contribution type
    "task_tags": ["tag1", "tag2", ...],  // 12-25 tags for research task/application area
    "modality_tags": ["text", "vision", "video", "audio", "multimodal", "code", "3D"],  // Data modalities
    "definitions": {
        "tag_name": "Brief definition of when to use this tag"
    }
}

Guidelines:
- Contribution tags should be orthogonal and contribution-first (what the paper introduces)
- Task tags should reflect the application domain or specific research area
- Always include an "OTHER" tag for edge cases
- Keep tags concise but descriptive
- Focus on tags that will be useful for clustering papers"""

    # Prepare paper summaries for the prompt
    paper_summaries = []
    for p in papers[:100]:  # Limit to avoid token limits
        summary = f"- {p.id}: {p.title}\n  Abstract: {p.abstract[:300]}..."
        paper_summaries.append(summary)

    user_prompt = f"""Analyze the following {len(papers)} papers from {month} and propose a taxonomy:

{chr(10).join(paper_summaries)}

Generate a comprehensive taxonomy JSON that can categorize all these papers effectively."""

    try:
        response = await call_llm(
            system_prompt,
            user_prompt,
            provider=provider,
            api_key=api_key
        )
        taxonomy_data = extract_json_from_response(response)

        if taxonomy_data:
            return Taxonomy(
                month=month,
                contribution_tags=taxonomy_data.get("contribution_tags", DEFAULT_CONTRIBUTION_TAGS),
                task_tags=taxonomy_data.get("task_tags", DEFAULT_TASK_TAGS),
                modality_tags=taxonomy_data.get("modality_tags", DEFAULT_MODALITY_TAGS),
                definitions=taxonomy_data.get("definitions", {})
            )
    except LLMError as e:
        print(f"LLM taxonomy generation failed: {e}")
    except Exception as e:
        print(f"LLM taxonomy generation failed: {e}")

    # Return default taxonomy on failure
    return Taxonomy(
        month=month,
        contribution_tags=DEFAULT_CONTRIBUTION_TAGS,
        task_tags=DEFAULT_TASK_TAGS,
        modality_tags=DEFAULT_MODALITY_TAGS,
        definitions={}
    )


async def tag_paper(
    paper: Paper,
    taxonomy: Taxonomy,
    api_key: Optional[str] = None,
    provider: Optional[ProviderName] = None
) -> PaperTags:
    """
    Tag a single paper using the provided taxonomy.

    Args:
        paper: Paper to tag
        taxonomy: Taxonomy to use for tagging
        api_key: Optional API key
        provider: Optional provider name (minimax, openai, anthropic)

    Returns:
        PaperTags object with assigned tags
    """
    system_prompt = f"""You are an expert ML/AI research curator. Tag the given paper using ONLY the tags from the provided taxonomy.

AVAILABLE TAGS:

Contribution Tags (choose exactly 1 primary, 0-2 secondary):
{json.dumps(taxonomy.contribution_tags, indent=2)}

Task Tags (choose 0-3):
{json.dumps(taxonomy.task_tags, indent=2)}

Modality Tags (choose 1+):
{json.dumps(taxonomy.modality_tags, indent=2)}

Output a JSON object with this exact structure:
{{
    "primary_contribution_tag": "exactly one tag from contribution_tags",
    "secondary_contribution_tags": ["0-2 additional contribution tags"],
    "task_tags": ["0-3 task tags"],
    "modality_tags": ["1+ modality tags"],
    "research_question": "One sentence describing the main research question",
    "confidence": 0.0-1.0,
    "rationale": "Brief explanation for the tagging choices"
}}

IMPORTANT: Only use tags that are EXACTLY in the provided lists. Do not invent new tags."""

    user_prompt = f"""Tag this paper:

Title: {paper.title}

Abstract: {paper.abstract}

ArXiv ID: {paper.id}"""

    try:
        response = await call_llm(
            system_prompt,
            user_prompt,
            provider=provider,
            api_key=api_key
        )
        tags_data = extract_json_from_response(response)

        if tags_data:
            # Validate tags against taxonomy
            primary = tags_data.get("primary_contribution_tag", "OTHER")
            if primary not in taxonomy.contribution_tags:
                primary = "OTHER"

            secondary = [t for t in tags_data.get("secondary_contribution_tags", [])
                        if t in taxonomy.contribution_tags][:2]

            task = [t for t in tags_data.get("task_tags", [])
                   if t in taxonomy.task_tags][:3]

            modality = [t for t in tags_data.get("modality_tags", ["text"])
                       if t in taxonomy.modality_tags]
            if not modality:
                modality = ["text"]

            return PaperTags(
                paper_id=paper.id,
                month=taxonomy.month,
                primary_contribution_tag=primary,
                secondary_contribution_tags=secondary,
                task_tags=task,
                modality_tags=modality,
                research_question=tags_data.get("research_question", ""),
                confidence=float(tags_data.get("confidence", 0.5)),
                rationale=tags_data.get("rationale", "")
            )
    except LLMError as e:
        print(f"LLM tagging failed for {paper.id}: {e}")
    except Exception as e:
        print(f"LLM tagging failed for {paper.id}: {e}")

    # Return default tags on failure
    return PaperTags(
        paper_id=paper.id,
        month=taxonomy.month,
        primary_contribution_tag="OTHER",
        secondary_contribution_tags=[],
        task_tags=["OTHER"],
        modality_tags=["text"],
        research_question="",
        confidence=0.0,
        rationale="Tagging failed"
    )


async def tag_all_papers(
    papers: list[Paper],
    taxonomy: Taxonomy,
    api_key: Optional[str] = None,
    provider: Optional[ProviderName] = None,
    progress_callback=None
) -> list[PaperTags]:
    """
    Tag all papers using the taxonomy.

    Args:
        papers: List of papers to tag
        taxonomy: Taxonomy to use
        api_key: Optional API key
        provider: Optional provider name (minimax, openai, anthropic)
        progress_callback: Optional callback(current, total, paper_id)

    Returns:
        List of PaperTags objects
    """
    all_tags = []

    for i, paper in enumerate(papers):
        if progress_callback:
            progress_callback(i + 1, len(papers), paper.id)

        print(f"Tagging paper {i + 1}/{len(papers)}: {paper.id}")
        tags = await tag_paper(paper, taxonomy, api_key=api_key, provider=provider)
        all_tags.append(tags)

    return all_tags


# For testing without API key - uses default taxonomy and comprehensive heuristics
def tag_paper_heuristic(paper: Paper, taxonomy: Taxonomy) -> PaperTags:
    """
    Comprehensive heuristic-based tagging using keywords extracted from real HF papers.
    Keywords are derived from analysis of 445+ papers from January 2026.
    """
    title_lower = paper.title.lower()
    abstract_lower = paper.abstract.lower()
    combined = title_lower + " " + abstract_lower

    # ============= CONTRIBUTION TYPE KEYWORDS =============
    # Derived from actual paper titles in the dataset

    contribution_keywords = {
        "Benchmark / Evaluation": [
            "benchmark", "bench", "evaluation", "evaluating", "evaluate",
            "leaderboard", "metric", "assess", "measuring", "diagnostic",
            "comprehensiv", "testing", "test suite", "grading",
            # From actual papers:
            "evalbench", "redbench", "finbench", "agencybench", "terminalbench",
            "astroreason-bench", "mirrorench", "sin-bench", "memoryrewardbench",
            "toolprmbench", "deepresearcheval", "sketchjudge", "vidore"
        ],
        "Dataset / Data Curation": [
            "dataset", "corpus", "data curation", "annotation", "labeled data",
            "collection", "curated", "archive", "large-scale data",
            # From actual papers:
            "action100m", "lemas", "ima++", "pubmed-ocr", "danqing",
            "rubrichub", "sci-reasoning"
        ],
        "Architecture / Model Design": [
            "architecture", "transformer", "attention", "model design",
            "neural network", "layer", "module", "backbone", "encoder", "decoder",
            "moe", "mixture-of-experts", "sparse", "dense",
            # From actual papers:
            "hyper-connection", "mhla", "gecko", "tag-moe", "routemoa",
            "diffusion transformer", "autoregressive", "recursive", "pyramidal"
        ],
        "Training Recipe / Scaling / Distillation": [
            "training", "scaling", "distillation", "pre-training", "pretraining",
            "fine-tuning", "finetuning", "continual learning", "curriculum",
            "data mixing", "recipe", "optimization",
            # From actual papers:
            "sft", "supervised fine-tuning", "distribution-aligned", "transition matching",
            "mid-training", "continual pre-train"
        ],
        "Post-training / Alignment": [
            "alignment", "rlhf", "dpo", "ppo", "grpo", "preference optimization",
            "human feedback", "instruction tuning", "reward model", "reward learning",
            "preference tuning", "direct preference",
            # From actual papers:
            "phygdpo", "gdpo", "cppo", "e-grpo", "bapo", "lpo", "yapo",
            "personalalign", "spinal", "process reward", "prl"
        ],
        "Reasoning / Test-time Compute": [
            "reasoning", "chain-of-thought", "cot", "test-time", "think",
            "step-by-step", "inference scaling", "self-consistency",
            "thought", "deliberat", "reflect",
            # From actual papers:
            "diffcot", "cov", "render-of-thought", "acot", "thinking",
            "r1", "omni-r1", "videoauto-r1", "judgerl", "multiplex thinking",
            "chain-of-view", "latent reasoning", "visual thinking", "societies of thought"
        ],
        "Agents / Tool Use / Workflow": [
            "agent", "agentic", "tool use", "tool-use", "workflow", "planning",
            "action", "environment", "autonomous", "multi-agent", "orchestrat",
            # From actual papers:
            "youtu-agent", "swe-agent", "dr. zero", "et-agent", "megaflow",
            "opentinker", "showui", "gui agent", "web agent", "computer use",
            "vla", "vision-language-action", "robotic", "embodied",
            "agentehr", "agentocr", "agentdevel", "maxs", "magma"
        ],
        "Multimodal Method": [
            "multimodal", "multi-modal", "vision-language", "vlm", "mllm",
            "image-text", "visual question", "cross-modal", "omni-modal",
            # From actual papers:
            "javisgpt", "nextflow", "vino", "lavit", "molmo", "qwen3-vl",
            "omni", "um-text", "videoloom", "e5-omni", "ar-omni"
        ],
        "RAG / Retrieval / Memory": [
            "rag", "retrieval", "memory", "knowledge base", "external knowledge",
            "augmented generation", "context", "kv cache", "long-context",
            # From actual papers:
            "simplemem", "memobrain", "hypergraph", "episodic", "realmem",
            "hermes", "memory bank", "agentic-r", "opendecoder"
        ],
        "Safety / Robustness / Interpretability": [
            "safety", "safe", "robustness", "robust", "interpretab", "explain",
            "bias", "fairness", "toxic", "harmful", "jailbreak", "attack",
            "hallucination", "hallucinat", "privacy", "security", "vulnerab",
            # From actual papers:
            "toolsafe", "camels", "halluguard", "evasionbench", "finvault",
            "poisoned", "red team", "adversarial"
        ],
        "Systems / Efficiency": [
            "efficient", "efficiency", "quantization", "serving", "latency",
            "inference", "compression", "pruning", "sparse", "fast", "accelerat",
            "edge", "lightweight", "speculative decoding", "kv compression",
            # From actual papers:
            "snapgen++", "flash", "salad", "dr-lora", "elastic attention",
            "glimprouter", "fp8", "jet-rl", "token compression"
        ],
        "Survey / Tutorial": [
            "survey", "tutorial", "review", "overview", "comprehensive study",
            "roadmap", "practical survey", "advances and frontiers",
            # From actual papers:
            "locate, steer, and improve", "toward efficient agents"
        ],
        "Technical Report / Model Release": [
            "technical report", "release", "introducing", "we present", "we release",
            # From actual papers (exact matches):
            "gr-dexter technical report", "k-exaone technical report",
            "mimo-v2-flash technical report", "translategemma technical report",
            "solar open technical report", "qwen3-tts technical report",
            "vibevoice-asr technical report", "skyreels-v3 technique report",
            "longcat-flash-thinking", "ministral"
        ],
        "Theory / Analysis": [
            "theory", "theoretical", "prove", "theorem", "bound", "analysis",
            "empirical study", "understanding", "mechanistic", "demystify",
            # From actual papers:
            "illusion of", "fallacy", "paradox", "dichotomy", "trade-off",
            "why llms", "can llms", "does inference", "what matters"
        ],
        "Application / Domain-Specific": [
            "medical", "clinical", "health", "drug", "disease", "patient", "diagnosis",
            "legal", "law", "finance", "financial", "education", "scientific",
            "pathology", "dermatolog", "epidemiolog", "radiology",
            # From actual papers:
            "medical sam", "agentehr", "cure-med", "skinflow", "vista-path",
            "mecellem", "bizfinbench", "astroreason"
        ],
        "Video Generation / Understanding": [
            "video generation", "video synthesis", "text-to-video", "video diffusion",
            "video world model", "video understanding", "video reasoning",
            # From actual papers:
            "flowblending", "physrvg", "dreamstyle", "memory-v2v", "skyreels",
            "versecraft", "plenoptic video", "transition matching"
        ],
        "3D / Spatial Intelligence": [
            "3d", "three-dimensional", "point cloud", "mesh", "gaussian splatting",
            "nerf", "novel view", "reconstruction", "spatial", "geometry",
            # From actual papers:
            "gamo", "morphany3d", "gen3r", "3d coca", "openvoxel", "shaper",
            "interp3d", "motion 3-to-4", "360anything", "caricaturegs"
        ],
    }

    # Determine primary contribution with priority ordering
    primary = "Foundational Research"

    # Check in priority order (more specific first)
    priority_order = [
        "Technical Report / Model Release",  # Check first - very specific pattern
        "Benchmark / Evaluation",
        "Dataset / Data Curation",
        "Agents / Tool Use / Workflow",
        "Reasoning / Test-time Compute",
        "Video Generation / Understanding",
        "3D / Spatial Intelligence",
        "RAG / Retrieval / Memory",
        "Post-training / Alignment",
        "Safety / Robustness / Interpretability",
        "Multimodal Method",
        "Systems / Efficiency",
        "Architecture / Model Design",
        "Training Recipe / Scaling / Distillation",
        "Survey / Tutorial",
        "Theory / Analysis",
        "Application / Domain-Specific",
    ]

    for contrib_type in priority_order:
        if contrib_type in contribution_keywords:
            keywords = contribution_keywords[contrib_type]
            if any(kw in combined for kw in keywords):
                primary = contrib_type
                break

    # Map to taxonomy tags (handle slight naming differences)
    tag_mapping = {
        "Video Generation / Understanding": "Multimodal Method",
        "3D / Spatial Intelligence": "Multimodal Method",
    }
    primary = tag_mapping.get(primary, primary)

    # Ensure primary is in taxonomy
    if primary not in taxonomy.contribution_tags:
        if "Foundational Research" in taxonomy.contribution_tags:
            primary = "Foundational Research"
        elif "Application / Domain-Specific" in taxonomy.contribution_tags:
            primary = "Application / Domain-Specific"
        else:
            primary = taxonomy.contribution_tags[0] if taxonomy.contribution_tags else "Foundational Research"

    # ============= TASK TAGS KEYWORDS =============

    task_keywords = {
        "RAG": [
            "rag", "retrieval-augmented", "retrieval augmented", "retrieve",
            "context retrieval", "document retrieval"
        ],
        "Coding / SWE Agents": [
            "code", "coding", "programming", "software engineer", "swe",
            "github", "repository", "developer", "bug fix", "code generation",
            "code completion", "debugging", "x-coder", "diffcoder"
        ],
        "Video Reasoning": [
            "video", "temporal", "frame", "clip", "video understanding",
            "video generation", "video diffusion", "v2v"
        ],
        "Long-context": [
            "long-context", "long context", "extended context", "128k", "1m token",
            "long-horizon", "ultra-long", "endless", "infinite"
        ],
        "Math Reasoning": [
            "math", "mathematical", "arithmetic", "geometry", "algebra",
            "theorem", "proof", "numina", "lean", "formal math"
        ],
        "Scientific Reasoning": [
            "scientific", "science", "chemistry", "physics", "biology",
            "molecular", "drug", "protein", "epidemiolog"
        ],
        "Multimodal Understanding": [
            "multimodal", "multi-modal", "cross-modal", "omni-modal",
            "vision-language", "vlm", "mllm"
        ],
        "Language Understanding": [
            "language understanding", "nlp", "nlu", "semantic", "syntactic",
            "linguistic", "sentiment", "translation"
        ],
        "Generation / Synthesis": [
            "generation", "synthesis", "generate", "generative",
            "text-to-image", "text-to-video", "image generation"
        ],
        "Embedding / Representation": [
            "embedding", "representation", "encode", "vector", "latent",
            "kv-embedding", "e5-omni"
        ],
        "Document Understanding": [
            "document", "pdf", "ocr", "layout", "table", "chart",
            "gutenocr", "typhoon ocr", "chartverse"
        ],
        "Speech / Audio Processing": [
            "speech", "audio", "voice", "acoustic", "asr", "tts",
            "spoken", "diarization", "transcri"
        ],
        "Planning / Search": [
            "planning", "search", "monte carlo", "tree search", "mcts",
            "navigation", "pathfinding", "scheduling"
        ],
        "Multi-agent Systems": [
            "multi-agent", "multiple agents", "agent collaboration",
            "collaborative", "consensus"
        ],
        "General NLP": [
            "nlp", "natural language", "text", "linguistic",
            "language model", "llm"
        ],
        "Computer Vision": [
            "image", "visual", "object detection", "segmentation", "recognition",
            "pose", "depth", "3d reconstruction"
        ],
        "Robotics / Embodied AI": [
            "robot", "robotic", "embodied", "manipulation", "navigation",
            "vla", "vision-language-action", "control"
        ],
        "GUI / Web Agents": [
            "gui", "web agent", "browser", "ui", "interface", "computer use",
            "showui", "os-symphony", "webseek"
        ],
    }

    task_tags = []
    for tag, keywords in task_keywords.items():
        if any(kw in combined for kw in keywords) and tag in taxonomy.task_tags:
            task_tags.append(tag)
            if len(task_tags) >= 3:
                break

    # Fallback task detection
    if not task_tags:
        if any(w in combined for w in ["image", "vision", "visual"]):
            if "Computer Vision" in taxonomy.task_tags:
                task_tags.append("Computer Vision")
        elif any(w in combined for w in ["video"]):
            if "Video Reasoning" in taxonomy.task_tags:
                task_tags.append("Video Reasoning")
        elif any(w in combined for w in ["agent", "agentic"]):
            if "Multi-agent Systems" in taxonomy.task_tags:
                task_tags.append("Multi-agent Systems")

    # ============= MODALITY TAGS =============

    modality_tags = []

    # Video detection (check first, more specific)
    if any(w in combined for w in [
        "video", "temporal", "frame-by-frame", "v2v", "video diffusion",
        "video generation", "video understanding", "clip"
    ]):
        modality_tags.append("video")

    # Vision/Image detection
    if any(w in combined for w in [
        "image", "vision", "visual", "picture", "photo", "pixel",
        "diffusion", "gan", "vae", "t2i", "text-to-image"
    ]):
        modality_tags.append("vision")

    # Audio detection
    if any(w in combined for w in [
        "audio", "speech", "voice", "sound", "acoustic", "music",
        "asr", "tts", "spoken", "waveform"
    ]):
        modality_tags.append("audio")

    # Code detection
    if any(w in combined for w in [
        "code", "coding", "programming", "python", "java", "repository",
        "github", "swe", "software", "compiler"
    ]):
        modality_tags.append("code")

    # 3D detection
    if any(w in combined for w in [
        "3d", "three-dimensional", "point cloud", "mesh", "voxel",
        "gaussian splatting", "nerf", "novel view", "depth"
    ]):
        modality_tags.append("3D")

    # Multimodal detection
    if any(w in combined for w in [
        "multimodal", "multi-modal", "omni-modal", "cross-modal",
        "vision-language", "vlm", "mllm", "unified"
    ]):
        modality_tags.append("multimodal")

    # Text is default or if explicitly mentioned
    if not modality_tags or any(w in combined for w in [
        "text", "language", "nlp", "document", "llm", "token"
    ]):
        if "text" not in modality_tags:
            modality_tags.append("text")

    # Filter to only valid tags in taxonomy
    modality_tags = [t for t in modality_tags if t in taxonomy.modality_tags]
    if not modality_tags:
        modality_tags = ["text"]

    # ============= SECONDARY CONTRIBUTION TAGS =============

    secondary_tags = []
    for contrib_type, keywords in contribution_keywords.items():
        if contrib_type != primary and contrib_type in taxonomy.contribution_tags:
            if any(kw in combined for kw in keywords):
                mapped = tag_mapping.get(contrib_type, contrib_type)
                if mapped != primary and mapped in taxonomy.contribution_tags:
                    secondary_tags.append(mapped)
                    if len(secondary_tags) >= 2:
                        break

    return PaperTags(
        paper_id=paper.id,
        month=taxonomy.month,
        primary_contribution_tag=primary,
        secondary_contribution_tags=secondary_tags[:2],
        task_tags=task_tags[:3],
        modality_tags=modality_tags,
        research_question="",
        confidence=0.7,  # Slightly higher confidence with better keywords
        rationale="Heuristic tagging with comprehensive keywords from HF papers analysis"
    )
