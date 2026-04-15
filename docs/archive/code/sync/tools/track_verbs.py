"""Tool 6: track_verbs - Action verb registry management.

Maintains a global registry of verbs used across the entire resume
to prevent repetition and ensure variety.
"""

import json
from pydantic import BaseModel, Field, ConfigDict


class TrackVerbsInput(BaseModel):
    """Input for resume_track_verbs tool."""

    model_config = ConfigDict(json_schema_extra={"example": {
        "action": "check",
        "verbs": ["led", "managed", "directed"]
    }})

    action: str = Field(
        ...,
        description="'check' to test availability, 'register' to mark as used, 'list' to see all used, 'reset' to clear all"
    )
    verbs: list[str] = Field(
        default_factory=list,
        description="Verbs to check or register (lowercase, infinitive form)"
    )


class TrackVerbsOutput(BaseModel):
    """Output from resume_track_verbs tool."""

    model_config = ConfigDict(json_schema_extra={"example": {
        "action_performed": "check",
        "results": {
            "led": True,
            "managed": True,
            "directed": False
        },
        "conflicts": ["directed"],
        "total_used": 5,
        "all_used_verbs": ["led", "managed", "built", "created", "directed"]
    }})

    action_performed: str = Field(
        ...,
        description="Echo of the action that was performed"
    )
    results: dict[str, bool] = Field(
        ...,
        description="Verb → available (for check) or registered (for register)"
    )
    conflicts: list[str] = Field(
        ...,
        description="Verbs already used (for check action)"
    )
    total_used: int = Field(
        ...,
        description="Total unique verbs registered in this session"
    )
    all_used_verbs: list[str] = Field(
        ...,
        description="Complete list of all registered verbs (for list action)"
    )


class TrackVerbsState:
    """Internal state holder for verb registry.

    This is managed by the MCP server's lifespan and passed
    to the tool. The tool returns updated state for the server
    to persist.
    """

    def __init__(self, used_verbs: set = None):
        """Initialize with optional existing verb set.

        Args:
            used_verbs: Set of already-registered verbs, or None to start empty
        """
        self.used_verbs = used_verbs if used_verbs is not None else set()

    def check(self, verbs: list[str]) -> tuple[dict[str, bool], list[str]]:
        """Check availability of verbs.

        Args:
            verbs: List of verbs to check

        Returns:
            Tuple of (results dict, conflicts list)
        """
        results = {}
        conflicts = []

        for verb in verbs:
            verb_lower = verb.lower()
            if verb_lower in self.used_verbs:
                results[verb] = False
                conflicts.append(verb)
            else:
                results[verb] = True

        return results, conflicts

    def register(self, verbs: list[str]) -> dict[str, bool]:
        """Register verbs as used.

        Args:
            verbs: List of verbs to register

        Returns:
            Results dict with all verbs marked True
        """
        results = {}

        for verb in verbs:
            verb_lower = verb.lower()
            self.used_verbs.add(verb_lower)
            results[verb] = True

        return results

    def list_all(self) -> list[str]:
        """Get all registered verbs.

        Returns:
            Sorted list of all used verbs
        """
        return sorted(list(self.used_verbs))

    def reset(self) -> None:
        """Clear all registered verbs."""
        self.used_verbs.clear()


async def resume_track_verbs(
    params: TrackVerbsInput,
    state: TrackVerbsState = None
) -> str:
    """Manage a global registry of action verbs used across the entire resume.

    Maintains state across all tool calls within a session to ensure zero
    verb repetition. Supports four actions:

    - check: Returns which verbs are available (not yet used) and which conflict
    - register: Marks verbs as used (call after a section is finalized)
    - list: Returns all currently used verbs
    - reset: Clears the registry (call at session start or between candidates)

    Algorithm:
    1. check: For each verb, look up in used_verbs; return availability
    2. register: Add all verbs to used_verbs set
    3. list: Return sorted list of all used verbs
    4. reset: Clear the used_verbs set

    Args:
        params: TrackVerbsInput with action and optional verbs list
        state: TrackVerbsState instance (managed by server lifespan)

    Returns:
        JSON string with TrackVerbsOutput containing results, conflicts, and totals
    """
    try:
        # Initialize state if not provided (for standalone testing)
        if state is None:
            state = TrackVerbsState()

        action = params.action.lower()
        results = {}
        conflicts = []
        all_used_verbs = []

        if action == "check":
            # Check availability of verbs
            results, conflicts = state.check(params.verbs)
            all_used_verbs = state.list_all()

        elif action == "register":
            # Register verbs as used
            results = state.register(params.verbs)
            all_used_verbs = state.list_all()

        elif action == "list":
            # List all used verbs
            all_used_verbs = state.list_all()
            results = {}

        elif action == "reset":
            # Reset the registry
            state.reset()
            all_used_verbs = []
            results = {}

        else:
            error_output = {
                "error": f"Invalid action '{params.action}'. Must be 'check', 'register', 'list', or 'reset'.",
                "action_performed": params.action,
                "results": {},
                "conflicts": [],
                "total_used": len(state.used_verbs),
                "all_used_verbs": state.list_all()
            }
            return json.dumps(error_output, indent=2)

        output = TrackVerbsOutput(
            action_performed=action,
            results=results,
            conflicts=conflicts,
            total_used=len(state.used_verbs),
            all_used_verbs=all_used_verbs
        )

        return json.dumps(output.model_dump(), indent=2)

    except Exception as e:
        error_output = {
            "error": f"resume_track_verbs failed: {str(e)}",
            "action_performed": params.action,
            "results": {},
            "conflicts": [],
            "total_used": 0,
            "all_used_verbs": []
        }
        return json.dumps(error_output, indent=2)
