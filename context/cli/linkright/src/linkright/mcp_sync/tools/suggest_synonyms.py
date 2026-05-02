"""Tool 5: suggest_synonyms - Width optimization via word substitution.

Finds synonym replacements in text that adjust width closer to target.
Enables LLM-driven width tuning without manual rewrites.
"""

import json
import re
from pydantic import BaseModel, Field, ConfigDict

try:
    # Try absolute import (when used as MCP tool)
    from data.synonym_bank import SYNONYM_BANK
    from data.roboto_weights import ROBOTO_REGULAR_WEIGHTS, ROBOTO_BOLD_WEIGHTS, REGULAR_DEFAULT, BOLD_DEFAULT
except ImportError:
    # Fall back to relative import (when imported from package)
    from ..data.synonym_bank import SYNONYM_BANK
    from ..data.roboto_weights import ROBOTO_REGULAR_WEIGHTS, ROBOTO_BOLD_WEIGHTS, REGULAR_DEFAULT, BOLD_DEFAULT


class SynonymSuggestion(BaseModel):
    """Individual synonym suggestion with width impact."""

    model_config = ConfigDict(json_schema_extra={"example": {
        "original_word": "led",
        "replacement_word": "directed",
        "width_delta": 3.5,
        "estimated_new_total": 101.5,
        "position_in_text": 12
    }})

    original_word: str = Field(
        ...,
        description="Word in the text to replace"
    )
    replacement_word: str = Field(
        ...,
        description="Suggested synonym"
    )
    width_delta: float = Field(
        ...,
        description="Change in character-units (positive = expansion)"
    )
    estimated_new_total: float = Field(
        ...,
        description="Projected width after substitution"
    )
    position_in_text: int = Field(
        ...,
        description="Character index where original_word starts"
    )


class SynonymInput(BaseModel):
    """Input for resume_suggest_synonyms tool."""

    model_config = ConfigDict(json_schema_extra={"example": {
        "text": "Led the team through a major project",
        "current_width": 98.5,
        "target_width": 100.0,
        "direction": "expand"
    }})

    text: str = Field(
        ...,
        description="Current line text (plain text, no HTML tags)"
    )
    current_width: float = Field(
        ...,
        description="Current weighted total in character-units"
    )
    target_width: float = Field(
        ...,
        description="Target budget in character-units (usually target_95)"
    )
    direction: str = Field(
        ...,
        description="'expand' (need more width) or 'trim' (need less width)"
    )


class SynonymOutput(BaseModel):
    """Output from resume_suggest_synonyms tool."""

    model_config = ConfigDict(json_schema_extra={"example": {
        "suggestions": [{
            "original_word": "led",
            "replacement_word": "directed",
            "width_delta": 3.5,
            "estimated_new_total": 102.0,
            "position_in_text": 0
        }],
        "gap_to_close": -2.0
    }})

    suggestions: list[SynonymSuggestion] = Field(
        ...,
        description="Sorted by how close estimated_new_total is to target_width"
    )
    gap_to_close: float = Field(
        ...,
        description="Remaining character-units to reach target (positive = still need adjustment)"
    )


def _calculate_word_width(word: str, is_bold: bool = False) -> float:
    """Calculate width of a word using Roboto character weights.

    Args:
        word: The word to measure
        is_bold: Whether to use bold weights

    Returns:
        Total width in character-units
    """
    weights = ROBOTO_BOLD_WEIGHTS if is_bold else ROBOTO_REGULAR_WEIGHTS
    default = BOLD_DEFAULT if is_bold else REGULAR_DEFAULT

    total = 0.0
    for char in word:
        total += weights.get(char, default)

    return total


def _tokenize_text(text: str) -> list[tuple[str, int]]:
    """Tokenize text into words with their positions.

    Args:
        text: Input text

    Returns:
        List of (word, position) tuples
    """
    tokens = []
    # Match word characters (letters, digits, apostrophes)
    for match in re.finditer(r"\b[\w']+\b", text):
        tokens.append((match.group(), match.start()))
    return tokens


def _find_synonym_matches(
    text: str,
    direction: str,
    current_width: float,
    target_width: float
) -> list[SynonymSuggestion]:
    """Find all synonym matches in text and calculate impacts.

    Args:
        text: Input text to scan
        direction: "expand" or "trim"
        current_width: Current total width
        target_width: Target width

    Returns:
        List of suggestion objects, sorted by proximity to target
    """
    suggestions = []

    # Get synonym bank for this direction
    if direction not in ["expand", "trim"]:
        return suggestions

    synonym_pairs = SYNONYM_BANK.get(direction, [])

    # Tokenize the text
    tokens = _tokenize_text(text)

    # For each token, check if it matches a synonym pair
    for token, position in tokens:
        token_lower = token.lower()

        for original, replacement, delta in synonym_pairs:
            if original.lower() == token_lower:
                # Found a match
                estimated_new = current_width + delta
                suggestion = SynonymSuggestion(
                    original_word=token,
                    replacement_word=replacement,
                    width_delta=delta,
                    estimated_new_total=estimated_new,
                    position_in_text=position
                )
                suggestions.append(suggestion)
                break  # Only one replacement per token

    # Sort by proximity to target width: |estimated_new - target|
    suggestions.sort(
        key=lambda s: abs(s.estimated_new_total - target_width)
    )

    return suggestions


async def resume_suggest_synonyms(params: SynonymInput) -> str:
    """Find word substitutions in text that adjust width closer to target.

    Scans the text for words that exist in the synonym bank and calculates
    the width impact of each substitution. Returns suggestions sorted by
    how closely they would bring the total width to the target budget.

    The LLM chooses which suggestion to apply (language quality decision).
    The MCP only computes — it never rewrites content.

    Algorithm:
    1. Tokenize text into words with positions
    2. For each word, check if it matches a synonym in the requested direction
    3. Calculate width delta using Roboto character weights
    4. Estimate new total = current_width + delta
    5. Sort by proximity to target (|estimated_new - target|)
    6. Return top suggestions with remaining gap

    Args:
        params: SynonymInput with text, current_width, target_width, direction

    Returns:
        JSON string with SynonymOutput containing suggestions and gap_to_close
    """
    try:
        # Validate direction
        if params.direction not in ["expand", "trim"]:
            error_output = {
                "error": f"Invalid direction '{params.direction}'. Must be 'expand' or 'trim'.",
                "suggestions": [],
                "gap_to_close": params.target_width - params.current_width
            }
            return json.dumps(error_output, indent=2)

        # Find all matching synonyms
        suggestions = _find_synonym_matches(
            params.text,
            params.direction,
            params.current_width,
            params.target_width
        )

        # If we have suggestions, gap is from the best suggestion
        # Otherwise, gap is from current width
        if suggestions:
            gap_to_close = params.target_width - suggestions[0].estimated_new_total
        else:
            gap_to_close = params.target_width - params.current_width

        output = SynonymOutput(
            suggestions=suggestions[:10],  # Return top 10 suggestions
            gap_to_close=round(gap_to_close, 2)
        )

        return json.dumps(output.model_dump(), indent=2)

    except Exception as e:
        error_output = {
            "error": f"resume_suggest_synonyms failed: {str(e)}",
            "suggestions": [],
            "gap_to_close": params.target_width - params.current_width
        }
        return json.dumps(error_output, indent=2)
