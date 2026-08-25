#!/usr/bin/env python3
"""Build a modular ImageGen prompt for a verified scientific figure."""

import argparse
import copy
import json
import os
import sys


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_PROFILES = os.path.join(ROOT, "references", "figure-style-presets.json")
DEFAULT_ARCHETYPES = os.path.join(ROOT, "references", "figure-archetypes.json")
REQUIRED_FIELDS = ("purpose", "title", "story", "exact_text")


def load_json(path):
    with open(path, "r", encoding="utf-8") as stream:
        return json.load(stream)


def deep_merge(base, override):
    """Return a recursively merged copy without mutating either input."""
    result = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def require_string(spec, field):
    value = spec.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % field)
    return value.strip()


def require_string_list(spec, field):
    value = spec.get(field)
    if not isinstance(value, list) or not value:
        raise ValueError("%s must be a non-empty list" % field)
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError("%s must contain only non-empty strings" % field)
    return [item.strip() for item in value]


def optional_string_list(spec, field):
    value = spec.get(field, [])
    if not isinstance(value, list):
        raise ValueError("%s must be a list" % field)
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError("%s must contain only non-empty strings" % field)
    return [item.strip() for item in value]


def bullet_section(title, items):
    if not items:
        return ""
    return "%s\n%s" % (title, "\n".join("- %s" % item for item in items))


def format_palette(palette):
    return ", ".join("%s %s" % (key.replace("_", " "), value)
                     for key, value in palette.items())


def build_prompt(spec, profiles, archetypes, profile_name=None,
                 archetype_name=None):
    for field in REQUIRED_FIELDS:
        if field not in spec:
            raise ValueError("missing required field: %s" % field)

    purpose = require_string(spec, "purpose")
    title = require_string(spec, "title")
    story = require_string_list(spec, "story")
    exact_text = require_string_list(spec, "exact_text")

    selected_profile = profile_name or spec.get("profile", "nature-neuroscience")
    selected_archetype = archetype_name or spec.get("archetype", "mechanism")
    if selected_profile not in profiles:
        raise ValueError("unknown profile: %s" % selected_profile)
    if selected_archetype not in archetypes:
        raise ValueError("unknown archetype: %s" % selected_archetype)

    overrides = spec.get("style_overrides", {})
    if not isinstance(overrides, dict):
        raise ValueError("style_overrides must be an object")
    profile = deep_merge(profiles[selected_profile], overrides)
    archetype = archetypes[selected_archetype]

    subtitle = spec.get("subtitle")
    if subtitle is not None and (not isinstance(subtitle, str) or not subtitle.strip()):
        raise ValueError("subtitle must be a non-empty string when supplied")

    observed = optional_string_list(spec, "observed")
    inferred = optional_string_list(spec, "inferred")
    layout_notes = optional_string_list(spec, "layout_notes")
    constraints = optional_string_list(spec, "constraints")
    custom_avoid = optional_string_list(spec, "avoid")
    data = spec.get("data")
    if data is not None and not isinstance(data, (dict, list)):
        raise ValueError("data must be an object or list")

    font = profile["font"]
    canvas = profile["canvas"]
    sections = [
        "USE CASE\nscientific-educational",
        "ASSET\nComplete publication-grade scientific figure rendered end to end, including every label and all typography.",
        "PURPOSE\n%s" % purpose,
        "TITLE\n%s" % title,
    ]
    if subtitle:
        sections.append("SUBTITLE\n%s" % subtitle.strip())

    sections.extend([
        "STYLE PROFILE\n%s\n%s" % (profile["name"], profile["intent"]),
        "TYPOGRAPHY — HARD REQUIREMENT\n"
        "- Render every character in %s throughout; %s is the only acceptable visual fallback.\n"
        "- Text colour: %s. Minimum readable text at 1,536 px width: %s px; body %s px; section headings %s px; title %s px; panel letters %s px.\n%s" % (
            font["family"], font["fallback"], font["text_color"],
            font["minimum_px_at_1536_width"], font["body_px_at_1536_width"],
            font["section_px_at_1536_width"], font["title_px_at_1536_width"],
            font["panel_label_px_at_1536_width"],
            "\n".join("- %s" % item for item in font["rules"])),
        "CANVAS\n- Background: %s\n- Aspect: %s\n- Margin: %s\n- Density: %s" % (
            canvas["background"], canvas["aspect"], canvas["margin"],
            canvas["density"]),
        "PALETTE\n%s" % format_palette(profile["palette"]),
        bullet_section("VISUAL LANGUAGE", profile["visual_language"]),
        "ARCHETYPE\n%s — %s" % (selected_archetype, archetype["goal"]),
        bullet_section("COMPOSITION", archetype["composition"]),
        bullet_section("EVIDENCE-BACKED STORY", story),
    ])

    if observed:
        sections.append(bullet_section("DIRECTLY OBSERVED", observed))
    if inferred:
        sections.append(bullet_section(
            "INFERRED, MODEL-SUPPORTED, MIXED, OR UNCERTAIN", inferred))
    if data is not None:
        sections.append("EXACT DATA — DO NOT ALTER\n%s" % json.dumps(
            data, ensure_ascii=False, indent=2, sort_keys=True))
    if layout_notes:
        sections.append(bullet_section("TOPIC-SPECIFIC LAYOUT", layout_notes))
    if constraints:
        sections.append(bullet_section("SCIENTIFIC CONSTRAINTS", constraints))

    sections.append(
        "EXACT TEXT MANIFEST — RENDER EVERY STRING VERBATIM IN ARIAL\n%s" %
        "\n".join("- %s" % json.dumps(item, ensure_ascii=False)
                  for item in exact_text))

    all_avoid = list(profile["avoid"]) + custom_avoid
    sections.extend([
        bullet_section("AVOID", all_avoid),
        bullet_section("ARCHETYPE QA", archetype["qa"]),
        "FINAL CONTRACT\n"
        "Generate the complete final figure now. Do not leave blank text placeholders. "
        "Do not add text that is absent from the exact-text manifest. Preserve every "
        "number, unit, interval, denominator, qualifier, and relationship exactly. "
        "No watermark, logo, masthead, or imitation journal branding."
    ])
    return "\n\n".join(section for section in sections if section)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Build a modular prompt for a scientific-review figure")
    parser.add_argument("--spec", help="JSON evidence and copy specification")
    parser.add_argument("--profile", help="Override the style profile")
    parser.add_argument("--archetype", help="Override the figure archetype")
    parser.add_argument("--profiles", default=DEFAULT_PROFILES,
                        help="Style profile JSON file")
    parser.add_argument("--archetypes", default=DEFAULT_ARCHETYPES,
                        help="Archetype JSON file")
    parser.add_argument("--list-profiles", action="store_true")
    parser.add_argument("--list-archetypes", action="store_true")
    parser.add_argument("--out", help="Write prompt to a file instead of stdout")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    profiles = load_json(args.profiles)
    archetypes = load_json(args.archetypes)

    if args.list_profiles:
        for name in sorted(profiles):
            print("%s\t%s" % (name, profiles[name]["name"]))
        return 0
    if args.list_archetypes:
        for name in sorted(archetypes):
            print("%s\t%s" % (name, archetypes[name]["goal"]))
        return 0
    if not args.spec:
        raise ValueError("--spec is required unless listing profiles or archetypes")

    prompt = build_prompt(load_json(args.spec), profiles, archetypes,
                          args.profile, args.archetype)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as stream:
            stream.write(prompt)
            stream.write("\n")
    else:
        print(prompt)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        sys.exit(2)
