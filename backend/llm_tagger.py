"""
LLM integration for taxonomy generation and paper tagging.
Supports multiple LLM providers via the llm module.
"""

import json
import re
from typing import Optional

from database import Paper, Taxonomy, PaperTags
from llm import get_provider, LLMError, ProviderName

# Default taxonomy if LLM call fails
DEFAULT_CONTRIBUTION_TAGS = [
    "Benchmark / Evaluation",
    "Dataset / Data Curation",
    "Architecture / Model Design",
    "Training Recipe / Scaling / Distillation",
    "Post-training / Alignment",
    "Reasoning / Test-time Compute",
    "Agents / Tool Use / Workflow",
    "Multimodal Method",
    "RAG / Retrieval / Memory",
    "Safety / Robustness / Interpretability",
    "Systems / Efficiency",
    "Survey / Tutorial",
    "Technical Report / Model Release",
    "Theory / Analysis",
    "Application / Domain-Specific",
    "Foundational Research"
]

DEFAULT_TASK_TAGS = [
    "RAG",
    "Coding / SWE Agents",
    "Video Reasoning",
    "Long-context",
    "Scientific Reasoning",
    "Medical Imaging",
    "Evaluation Frameworks",
    "Alignment / Preference Learning",
    "World Models / 3D / 4D",
    "Multimodal Understanding",
    "Language Understanding",
    "Generation / Synthesis",
    "Embedding / Representation",
    "Knowledge Graphs",
    "Robotics / Embodied AI",
    "Speech / Audio Processing",
    "Document Understanding",
    "Math Reasoning",
    "Planning / Search",
    "Multi-agent Systems",
    "General NLP",
    "Computer Vision"
]

DEFAULT_MODALITY_TAGS = [
    "text",
    "vision",
    "video",
    "audio",
    "multimodal",
    "code",
    "3D"
]


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


# For testing without API key - uses default taxonomy and simple heuristics
def tag_paper_heuristic(paper: Paper, taxonomy: Taxonomy) -> PaperTags:
    """Simple heuristic-based tagging for testing without API."""
    title_lower = paper.title.lower()
    abstract_lower = paper.abstract.lower()
    combined = title_lower + " " + abstract_lower

    # Determine primary contribution - more comprehensive matching
    primary = "Foundational Research"  # Default fallback instead of OTHER

    if any(w in combined for w in ["benchmark", "evaluation", "assess", "leaderboard", "metric"]):
        primary = "Benchmark / Evaluation"
    elif any(w in combined for w in ["dataset", "corpus", "data curation", "annotation", "labeled data"]):
        primary = "Dataset / Data Curation"
    elif any(w in combined for w in ["architecture", "transformer", "attention", "model design", "neural network", "layer"]):
        primary = "Architecture / Model Design"
    elif any(w in combined for w in ["training", "scaling", "distillation", "pre-training", "pretraining", "fine-tuning"]):
        primary = "Training Recipe / Scaling / Distillation"
    elif any(w in combined for w in ["alignment", "rlhf", "dpo", "sft", "preference", "human feedback", "instruction tuning"]):
        primary = "Post-training / Alignment"
    elif any(w in combined for w in ["reasoning", "chain-of-thought", "test-time", "cot", "step-by-step", "think"]):
        primary = "Reasoning / Test-time Compute"
    elif any(w in combined for w in ["agent", "tool use", "workflow", "planning", "action", "environment"]):
        primary = "Agents / Tool Use / Workflow"
    elif any(w in combined for w in ["multimodal", "vision-language", "vlm", "image-text", "visual question"]):
        primary = "Multimodal Method"
    elif any(w in combined for w in ["rag", "retrieval", "memory", "knowledge base", "external knowledge"]):
        primary = "RAG / Retrieval / Memory"
    elif any(w in combined for w in ["safety", "robustness", "interpretab", "explain", "bias", "fairness", "toxic"]):
        primary = "Safety / Robustness / Interpretability"
    elif any(w in combined for w in ["efficient", "quantization", "serving", "latency", "inference", "compression", "pruning"]):
        primary = "Systems / Efficiency"
    elif any(w in combined for w in ["survey", "tutorial", "review", "overview", "comprehensive study"]):
        primary = "Survey / Tutorial"
    elif any(w in combined for w in ["technical report", "release", "introducing", "we present", "we release"]):
        primary = "Technical Report / Model Release"
    elif any(w in combined for w in ["theory", "analysis", "theoretical", "prove", "theorem", "bound"]):
        primary = "Theory / Analysis"
    elif any(w in combined for w in ["medical", "clinical", "health", "drug", "disease", "patient", "diagnosis",
                                      "legal", "law", "finance", "financial", "education", "scientific"]):
        primary = "Application / Domain-Specific"

    # Ensure primary is in taxonomy, use "Foundational Research" as final fallback
    if primary not in taxonomy.contribution_tags:
        if "Foundational Research" in taxonomy.contribution_tags:
            primary = "Foundational Research"
        elif "Application / Domain-Specific" in taxonomy.contribution_tags:
            primary = "Application / Domain-Specific"
        else:
            primary = taxonomy.contribution_tags[0] if taxonomy.contribution_tags else "Foundational Research"

    # Determine task tags - more comprehensive
    task_tags = []
    task_keywords = {
        "RAG": ["rag", "retrieval-augmented", "retrieval augmented"],
        "Coding / SWE Agents": ["code", "programming", "software engineer", "github", "repository", "developer"],
        "Video Reasoning": ["video", "temporal", "frame", "clip"],
        "Long-context": ["long-context", "long context", "extended context", "128k", "1m token"],
        "Math Reasoning": ["math", "mathematical", "arithmetic", "geometry", "algebra"],
        "Scientific Reasoning": ["scientific", "science", "chemistry", "physics", "biology"],
        "Multimodal Understanding": ["multimodal", "multi-modal", "cross-modal"],
        "Language Understanding": ["language understanding", "nlp", "nlu", "semantic", "syntactic"],
        "Generation / Synthesis": ["generation", "synthesis", "generate", "create", "produce"],
        "Embedding / Representation": ["embedding", "representation", "encode", "vector"],
        "Document Understanding": ["document", "pdf", "ocr", "layout"],
        "Speech / Audio Processing": ["speech", "audio", "voice", "acoustic", "asr", "tts"],
        "Planning / Search": ["planning", "search", "monte carlo", "tree search", "mcts"],
        "Multi-agent Systems": ["multi-agent", "multiple agents", "agent collaboration"],
        "General NLP": ["nlp", "natural language", "text", "linguistic"],
        "Computer Vision": ["image", "visual", "object detection", "segmentation", "recognition"],
    }

    for tag, keywords in task_keywords.items():
        if any(kw in combined for kw in keywords) and tag in taxonomy.task_tags:
            task_tags.append(tag)
            if len(task_tags) >= 3:
                break

    # If no task tags found, add a general one based on modality
    if not task_tags:
        if any(w in combined for w in ["image", "vision", "visual"]):
            if "Computer Vision" in taxonomy.task_tags:
                task_tags.append("Computer Vision")
        elif any(w in combined for w in ["text", "language", "nlp"]):
            if "General NLP" in taxonomy.task_tags:
                task_tags.append("General NLP")

    # Determine modality
    modality_tags = []
    if any(w in combined for w in ["video"]):
        modality_tags.append("video")
    if any(w in combined for w in ["image", "vision", "visual", "picture", "photo"]):
        modality_tags.append("vision")
    if any(w in combined for w in ["audio", "speech", "voice", "sound"]):
        modality_tags.append("audio")
    if any(w in combined for w in ["code", "programming", "python", "java", "repository"]):
        modality_tags.append("code")
    if any(w in combined for w in ["3d", "three-dimensional", "point cloud", "mesh"]):
        modality_tags.append("3D")
    if any(w in combined for w in ["multimodal", "multi-modal"]):
        modality_tags.append("multimodal")
    if not modality_tags or any(w in combined for w in ["text", "language", "nlp", "document"]):
        modality_tags.append("text")

    # Filter to only valid tags
    modality_tags = [t for t in modality_tags if t in taxonomy.modality_tags]
    if not modality_tags:
        modality_tags = ["text"]

    return PaperTags(
        paper_id=paper.id,
        month=taxonomy.month,
        primary_contribution_tag=primary,
        secondary_contribution_tags=[],
        task_tags=task_tags[:3],
        modality_tags=modality_tags,
        research_question="",
        confidence=0.6,
        rationale="Heuristic tagging"
    )
