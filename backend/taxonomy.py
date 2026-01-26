"""
Curated taxonomy for ML/AI research papers with stable colors.

This module provides a standardized taxonomy aligned with established
research fields, with deterministic color assignments for consistent
visualization across time.
"""

import hashlib
from typing import Optional
from pydantic import BaseModel


class TaxonomyCategory(BaseModel):
    """A category in the taxonomy."""
    id: str
    name: str
    color: str
    description: str
    parent_id: Optional[str] = None
    aliases: list[str] = []


# ============= Curated Contribution Taxonomy =============
# What the paper introduces (contribution type)

CONTRIBUTION_TAXONOMY: list[TaxonomyCategory] = [
    TaxonomyCategory(
        id="benchmark",
        name="Benchmark / Evaluation",
        color="#3B82F6",  # Blue
        description="New benchmarks, evaluation frameworks, or systematic assessments",
        aliases=["evaluation", "benchmark", "leaderboard", "assessment"]
    ),
    TaxonomyCategory(
        id="dataset",
        name="Dataset / Data Curation",
        color="#10B981",  # Green
        description="New datasets, data collection, annotation, or curation methods",
        aliases=["dataset", "corpus", "data collection", "annotation"]
    ),
    TaxonomyCategory(
        id="architecture",
        name="Architecture / Model Design",
        color="#8B5CF6",  # Purple
        description="Novel model architectures, attention mechanisms, or structural innovations",
        aliases=["architecture", "transformer", "model design", "neural network"]
    ),
    TaxonomyCategory(
        id="training",
        name="Training / Scaling / Optimization",
        color="#F59E0B",  # Amber
        description="Training recipes, scaling laws, distillation, or optimization techniques",
        aliases=["training", "scaling", "distillation", "pre-training", "optimization"]
    ),
    TaxonomyCategory(
        id="alignment",
        name="Post-training / Alignment",
        color="#EC4899",  # Pink
        description="RLHF, DPO, instruction tuning, preference learning, and alignment methods",
        aliases=["alignment", "rlhf", "dpo", "instruction tuning", "preference"]
    ),
    TaxonomyCategory(
        id="reasoning",
        name="Reasoning / Inference",
        color="#6366F1",  # Indigo
        description="Chain-of-thought, test-time compute, reasoning capabilities",
        aliases=["reasoning", "chain-of-thought", "cot", "inference", "test-time"]
    ),
    TaxonomyCategory(
        id="agents",
        name="Agents / Tool Use",
        color="#14B8A6",  # Teal
        description="Autonomous agents, tool use, workflows, and planning systems",
        aliases=["agent", "tool use", "workflow", "planning", "autonomous"]
    ),
    TaxonomyCategory(
        id="multimodal",
        name="Multimodal Learning",
        color="#F97316",  # Orange
        description="Vision-language models, cross-modal learning, multimodal fusion",
        aliases=["multimodal", "vision-language", "vlm", "cross-modal"]
    ),
    TaxonomyCategory(
        id="retrieval",
        name="RAG / Retrieval / Memory",
        color="#06B6D4",  # Cyan
        description="Retrieval-augmented generation, memory systems, knowledge bases",
        aliases=["rag", "retrieval", "memory", "knowledge base"]
    ),
    TaxonomyCategory(
        id="safety",
        name="Safety / Interpretability",
        color="#EF4444",  # Red
        description="Safety, robustness, interpretability, fairness, and bias mitigation",
        aliases=["safety", "interpretability", "robustness", "fairness", "bias"]
    ),
    TaxonomyCategory(
        id="efficiency",
        name="Efficiency / Systems",
        color="#84CC16",  # Lime
        description="Quantization, pruning, efficient inference, serving systems",
        aliases=["efficiency", "quantization", "pruning", "inference", "serving"]
    ),
    TaxonomyCategory(
        id="generation",
        name="Generation / Synthesis",
        color="#A855F7",  # Violet
        description="Text, image, video, or audio generation methods",
        aliases=["generation", "synthesis", "generative", "diffusion"]
    ),
    TaxonomyCategory(
        id="understanding",
        name="Understanding / Analysis",
        color="#0EA5E9",  # Sky
        description="NLU, document understanding, semantic analysis",
        aliases=["understanding", "nlu", "semantic", "analysis"]
    ),
    TaxonomyCategory(
        id="application",
        name="Domain Application",
        color="#78716C",  # Stone
        description="Domain-specific applications (medical, legal, scientific, etc.)",
        aliases=["medical", "clinical", "legal", "scientific", "domain"]
    ),
    TaxonomyCategory(
        id="survey",
        name="Survey / Tutorial",
        color="#64748B",  # Slate
        description="Literature surveys, tutorials, comprehensive reviews",
        aliases=["survey", "tutorial", "review", "overview"]
    ),
    TaxonomyCategory(
        id="release",
        name="Model Release / Report",
        color="#FFD21E",  # HF Yellow
        description="Technical reports, model releases, system descriptions",
        aliases=["release", "technical report", "model card"]
    ),
]


# ============= Task/Application Taxonomy =============
# What research area/task the paper addresses

TASK_TAXONOMY: list[TaxonomyCategory] = [
    TaxonomyCategory(
        id="nlp-general",
        name="Natural Language Processing",
        color="#3B82F6",
        description="General NLP tasks and methods",
        aliases=["nlp", "natural language", "text processing"]
    ),
    TaxonomyCategory(
        id="cv-general",
        name="Computer Vision",
        color="#10B981",
        description="Image and video understanding",
        aliases=["computer vision", "image", "visual"]
    ),
    TaxonomyCategory(
        id="speech",
        name="Speech / Audio",
        color="#8B5CF6",
        description="Speech recognition, synthesis, audio processing",
        aliases=["speech", "audio", "asr", "tts", "voice"]
    ),
    TaxonomyCategory(
        id="code",
        name="Code / Software Engineering",
        color="#F59E0B",
        description="Code generation, program synthesis, SWE agents",
        aliases=["code", "programming", "software", "github"]
    ),
    TaxonomyCategory(
        id="math",
        name="Mathematical Reasoning",
        color="#EC4899",
        description="Math problem solving, theorem proving",
        aliases=["math", "mathematical", "theorem", "proof"]
    ),
    TaxonomyCategory(
        id="science",
        name="Scientific Discovery",
        color="#6366F1",
        description="Scientific reasoning, chemistry, biology, physics",
        aliases=["science", "scientific", "chemistry", "biology", "physics"]
    ),
    TaxonomyCategory(
        id="medical",
        name="Medical / Healthcare",
        color="#EF4444",
        description="Medical imaging, clinical NLP, healthcare AI",
        aliases=["medical", "clinical", "healthcare", "diagnosis"]
    ),
    TaxonomyCategory(
        id="robotics",
        name="Robotics / Embodied AI",
        color="#14B8A6",
        description="Robotic control, embodied agents, physical AI",
        aliases=["robotics", "embodied", "robot", "manipulation"]
    ),
    TaxonomyCategory(
        id="long-context",
        name="Long Context",
        color="#F97316",
        description="Extended context windows, long document processing",
        aliases=["long-context", "long context", "extended context"]
    ),
    TaxonomyCategory(
        id="multilingual",
        name="Multilingual / Cross-lingual",
        color="#06B6D4",
        description="Multilingual models, translation, cross-lingual transfer",
        aliases=["multilingual", "cross-lingual", "translation"]
    ),
    TaxonomyCategory(
        id="3d-world",
        name="3D / World Models",
        color="#84CC16",
        description="3D understanding, world models, spatial reasoning",
        aliases=["3d", "world model", "spatial", "point cloud"]
    ),
    TaxonomyCategory(
        id="video",
        name="Video Understanding",
        color="#A855F7",
        description="Video analysis, temporal reasoning, action recognition",
        aliases=["video", "temporal", "action recognition"]
    ),
    TaxonomyCategory(
        id="document",
        name="Document Understanding",
        color="#0EA5E9",
        description="PDF parsing, OCR, document QA, layout analysis",
        aliases=["document", "pdf", "ocr", "layout"]
    ),
    TaxonomyCategory(
        id="knowledge",
        name="Knowledge / Reasoning",
        color="#78716C",
        description="Knowledge graphs, commonsense reasoning, QA",
        aliases=["knowledge", "reasoning", "qa", "commonsense"]
    ),
]


# ============= Modality Taxonomy =============

MODALITY_TAXONOMY: list[TaxonomyCategory] = [
    TaxonomyCategory(id="text", name="Text", color="#3B82F6", description="Text/language data"),
    TaxonomyCategory(id="image", name="Image", color="#10B981", description="Static images"),
    TaxonomyCategory(id="video", name="Video", color="#8B5CF6", description="Video/temporal data"),
    TaxonomyCategory(id="audio", name="Audio", color="#F59E0B", description="Audio/speech data"),
    TaxonomyCategory(id="code", name="Code", color="#EC4899", description="Source code"),
    TaxonomyCategory(id="3d", name="3D", color="#14B8A6", description="3D geometry/point clouds"),
    TaxonomyCategory(id="multimodal", name="Multimodal", color="#F97316", description="Multiple modalities"),
]


# ============= Color Utilities =============

def get_category_color(category_name: str, taxonomy_type: str = "contribution") -> str:
    """
    Get the color for a category by name.
    Falls back to a deterministic hash-based color if not found.
    """
    taxonomies = {
        "contribution": CONTRIBUTION_TAXONOMY,
        "task": TASK_TAXONOMY,
        "modality": MODALITY_TAXONOMY,
    }

    taxonomy = taxonomies.get(taxonomy_type, CONTRIBUTION_TAXONOMY)

    # Try exact match
    for cat in taxonomy:
        if cat.name == category_name or cat.id == category_name:
            return cat.color
        if category_name.lower() in [a.lower() for a in cat.aliases]:
            return cat.color

    # Fallback: deterministic hash-based color
    return generate_color_from_string(category_name)


def generate_color_from_string(s: str) -> str:
    """Generate a deterministic color from a string."""
    hash_bytes = hashlib.md5(s.encode()).digest()
    # Use first 3 bytes for RGB, ensure reasonable saturation/lightness
    r = 100 + (hash_bytes[0] % 100)  # 100-199
    g = 100 + (hash_bytes[1] % 100)  # 100-199
    b = 100 + (hash_bytes[2] % 100)  # 100-199
    return f"#{r:02x}{g:02x}{b:02x}"


def get_contribution_tags() -> list[str]:
    """Get list of contribution tag names."""
    return [cat.name for cat in CONTRIBUTION_TAXONOMY]


def get_task_tags() -> list[str]:
    """Get list of task tag names."""
    return [cat.name for cat in TASK_TAXONOMY]


def get_modality_tags() -> list[str]:
    """Get list of modality tag names."""
    return [cat.name for cat in MODALITY_TAXONOMY]


def get_taxonomy_with_colors() -> dict:
    """Get full taxonomy with colors for frontend."""
    return {
        "contribution": [
            {"id": cat.id, "name": cat.name, "color": cat.color, "description": cat.description}
            for cat in CONTRIBUTION_TAXONOMY
        ],
        "task": [
            {"id": cat.id, "name": cat.name, "color": cat.color, "description": cat.description}
            for cat in TASK_TAXONOMY
        ],
        "modality": [
            {"id": cat.id, "name": cat.name, "color": cat.color, "description": cat.description}
            for cat in MODALITY_TAXONOMY
        ],
    }


def find_best_match(query: str, taxonomy_type: str = "contribution") -> Optional[TaxonomyCategory]:
    """
    Find the best matching category for a query string.
    Useful for mapping LLM-generated tags to canonical taxonomy.
    """
    taxonomies = {
        "contribution": CONTRIBUTION_TAXONOMY,
        "task": TASK_TAXONOMY,
        "modality": MODALITY_TAXONOMY,
    }

    taxonomy = taxonomies.get(taxonomy_type, CONTRIBUTION_TAXONOMY)
    query_lower = query.lower()

    # Exact match on name or id
    for cat in taxonomy:
        if cat.name.lower() == query_lower or cat.id == query_lower:
            return cat

    # Alias match
    for cat in taxonomy:
        for alias in cat.aliases:
            if alias.lower() in query_lower or query_lower in alias.lower():
                return cat

    # Partial name match
    for cat in taxonomy:
        if query_lower in cat.name.lower() or cat.name.lower() in query_lower:
            return cat

    return None
