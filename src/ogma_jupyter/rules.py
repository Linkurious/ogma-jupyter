"""Serializable rule descriptors for Ogma style rules.

Each function mirrors the ogma.rules.* JS API and returns a plain dict
that the JS side reconstructs into the corresponding ogma.rules function call.

Examples
--------
>>> from ogma_jupyter import rules
>>> color_rule = rules.map(field="data.country", values={"France": "blue"}, fallback="gray")
>>> size_rule = rules.slices(field="data.score", values={"nbSlices": 5, "min": 2, "max": 20})
>>> label_rule = rules.template("{{name}} ({{age}})")
"""

from typing import Any, Dict, List, Optional, Union


def map(
    field: str,
    values: Dict[str, Any],
    fallback: Optional[Any] = None,
) -> Dict:
    """Create a categorical data → value mapping rule.

    Mirrors ogma.rules.map(). Given a node or edge, returns a value
    based on a discrete mapping of data property values.

    Parameters
    ----------
    field : str
        Data property path, e.g. ``"data.country"`` or ``"data.type"``.
    values : dict
        Mapping from data value to output value, e.g.
        ``{"France": "blue", "Italy": "green"}``.
    fallback : any, optional
        Value to use when the data property is not in the mapping.
        Can be a list for alternating values.

    Returns
    -------
    dict
        Serializable rule descriptor.
    """
    if not isinstance(values, dict):
        raise ValueError(f"values must be a dict, got {type(values).__name__}")
    result: Dict[str, Any] = {"type": "map", "field": field, "values": values}
    if fallback is not None:
        result["fallback"] = fallback
    return result


def slices(
    field: str,
    values: Union[Dict, List],
    stops: Optional[Union[Dict, List]] = None,
    fallback: Optional[Any] = None,
    reverse: bool = False,
) -> Dict:
    """Create a numerical range → value mapping rule.

    Mirrors ogma.rules.slices(). Given a node or edge, returns a value
    based on which numerical range the data property falls into.

    Parameters
    ----------
    field : str
        Data property path to slice, e.g. ``"data.score"``.
    values : dict or list
        Output values. As a dict: ``{"nbSlices": 5, "min": 2, "max": 10}``.
        As a list: ``["blue", "green", "red"]`` (one entry per slice).
    stops : dict or list, optional
        Boundaries of slices. As a dict: ``{"min": 0, "max": 1000}``.
        As a list: ``[0, 100]`` (boundaries between slices).
    fallback : any, optional
        Value when the property is not a number.
    reverse : bool, optional
        If True, low data values get high output values.

    Returns
    -------
    dict
        Serializable rule descriptor.
    """
    result: Dict[str, Any] = {"type": "slices", "field": field, "values": values}
    if stops is not None:
        result["stops"] = stops
    if fallback is not None:
        result["fallback"] = fallback
    if reverse:
        result["reverse"] = reverse
    return result


def template(template_str: str) -> Dict:
    """Create a text template rule from data properties.

    Mirrors ogma.rules.template(). Replaces ``{{property}}`` placeholders
    in the string with the corresponding data property value.

    Parameters
    ----------
    template_str : str
        Template string, e.g. ``"{{name}} (age: {{age}})"``

    Returns
    -------
    dict
        Serializable rule descriptor.
    """
    if not isinstance(template_str, str):
        raise TypeError(f"template must be a string, got {type(template_str).__name__}")
    return {"type": "template", "template": template_str}
