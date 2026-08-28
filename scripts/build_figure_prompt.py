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
DEFAULT_WRITING_STYLES = os.path.join(
    ROOT, "references", "figure-writing-style-overlays.json")
REQUIRED_FIELDS = ("purpose", "title", "story", "exact_text")
RENDER_CONTEXTS = ("article", "standalone", "slide")
REVIEW_STYLES = ("scientific", "popsci", "bullets", "eli5")
RENDER_ROUTES = ("generated", "hybrid", "deterministic")


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


def expand_dotted_keys(value):
    """Expand ``{"canvas.aspect": "2:1"}`` into a nested override.

    Early figure specs used both dotted and nested override syntax. Supporting
    both prevents a requested aspect from being silently ignored.
    """
    if not isinstance(value, dict):
        raise ValueError("style_overrides must be an object")
    expanded = {}
    for key, item in value.items():
        if not isinstance(key, str) or not key:
            raise ValueError("style_overrides keys must be non-empty strings")
        target = expanded
        parts = key.split(".")
        for part in parts[:-1]:
            current = target.setdefault(part, {})
            if not isinstance(current, dict):
                raise ValueError("conflicting dotted style override: %s" % key)
            target = current
        target[parts[-1]] = copy.deepcopy(item)
    return expanded


def merge_writing_style(profile, overlay):
    """Apply a writing-style art-direction overlay without dropping base bans."""
    result = deep_merge(profile, overlay)
    for field in ("visual_language", "avoid", "art_direction", "selection_standard"):
        inherited = profile.get(field, [])
        added = overlay.get(field, [])
        if inherited or added:
            result[field] = list(inherited) + [
                item for item in added if item not in inherited
            ]
    base_rules = profile.get("font", {}).get("rules", [])
    style_rules = overlay.get("font", {}).get("rules", [])
    if base_rules or style_rules:
        if overlay.get("font", {}).get("family") != profile.get("font", {}).get("family"):
            result.setdefault("font", {})["rules"] = list(style_rules)
        else:
            result.setdefault("font", {})["rules"] = list(base_rules) + [
                item for item in style_rules if item not in base_rules
            ]
    return result


def inferred_render_route(spec, archetype_name):
    explicit = spec.get("render_route")
    if explicit:
        return explicit
    if archetype_name == "quantitative":
        return "deterministic"
    return "generated"


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
                 archetype_name=None, writing_styles=None,
                 review_style=None, render_route=None):
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

    writing_styles = writing_styles or load_json(DEFAULT_WRITING_STYLES)
    selected_review_style = review_style or spec.get("review_style", "scientific")
    if selected_review_style == "prose":
        selected_review_style = "scientific"
    if selected_review_style not in REVIEW_STYLES:
        raise ValueError("review_style must be one of: %s" % ", ".join(REVIEW_STYLES))
    if selected_review_style not in writing_styles:
        raise ValueError("missing writing-style overlay: %s" % selected_review_style)

    overrides = expand_dotted_keys(spec.get("style_overrides", {}))
    profile = merge_writing_style(
        profiles[selected_profile], writing_styles[selected_review_style])
    profile = deep_merge(profile, overrides)
    archetype = archetypes[selected_archetype]

    subtitle = spec.get("subtitle")
    if subtitle is not None and (not isinstance(subtitle, str) or not subtitle.strip()):
        raise ValueError("subtitle must be a non-empty string when supplied")

    framing = profile.get("framing", {})
    render_context = spec.get(
        "render_context", framing.get("default_context", "article"))
    if render_context not in RENDER_CONTEXTS:
        raise ValueError(
            "render_context must be one of: %s" % ", ".join(RENDER_CONTEXTS))

    rendered_text = list(exact_text)
    if render_context in ("article", "slide"):
        frame_text = {title}
        if subtitle:
            frame_text.add(subtitle.strip())
        rendered_text = [item for item in rendered_text if item not in frame_text]
    if not rendered_text:
        raise ValueError("exact_text must include at least one in-figure string")

    selected_route = render_route or inferred_render_route(
        spec, selected_archetype)
    if selected_route not in RENDER_ROUTES:
        raise ValueError("render_route must be one of: %s" % ", ".join(RENDER_ROUTES))

    generated_text = optional_string_list(spec, "generated_text")
    if any(item not in rendered_text for item in generated_text):
        raise ValueError("generated_text must be a subset of rendered exact_text")
    if selected_route == "generated":
        if generated_text and generated_text != rendered_text:
            raise ValueError(
                "generated figures must render every exact_text string directly")
        generated_text = list(rendered_text)
    if selected_route == "deterministic" and generated_text:
        raise ValueError("deterministic figures cannot declare generated_text")
    overlay_text = [item for item in rendered_text if item not in generated_text]

    contract_version = spec.get("quality_contract_version")
    if contract_version is not None and contract_version != 1:
        raise ValueError("quality_contract_version must be 1 when supplied")
    target_aspect = spec.get("target_aspect_ratio")
    if target_aspect is not None:
        try:
            target_aspect = float(target_aspect)
        except (TypeError, ValueError) as exc:
            raise ValueError("target_aspect_ratio must be numeric") from exc
        if not 1.0 <= target_aspect <= 4.0:
            raise ValueError("target_aspect_ratio must be between 1.0 and 4.0")
    visual_anchor = spec.get("visual_anchor")
    if visual_anchor is not None and (
        not isinstance(visual_anchor, str) or not visual_anchor.strip()
    ):
        raise ValueError("visual_anchor must be a non-empty string when supplied")
    if contract_version == 1:
        if "review_style" not in spec or "render_route" not in spec:
            raise ValueError(
                "quality contract v1 requires explicit review_style and render_route")
        if target_aspect is None:
            raise ValueError(
                "quality contract v1 requires numeric target_aspect_ratio")
        if selected_archetype != "quantitative" and not visual_anchor:
            raise ValueError(
                "quality contract v1 requires visual_anchor for non-quantitative figures")
        if selected_route == "hybrid" and not isinstance(spec.get("overlay"), dict):
            raise ValueError("quality contract v1 hybrid figures require overlay")

    observed = optional_string_list(spec, "observed")
    inferred = optional_string_list(spec, "inferred")
    layout_notes = optional_string_list(spec, "layout_notes")
    constraints = optional_string_list(spec, "constraints")
    custom_avoid = optional_string_list(spec, "avoid")
    geometry_invariants = optional_string_list(spec, "geometry_invariants")
    custom_art_direction = optional_string_list(spec, "art_direction")
    data = spec.get("data")
    if data is not None and not isinstance(data, (dict, list)):
        raise ValueError("data must be an object or list")

    font = profile["font"]
    canvas = copy.deepcopy(profile["canvas"])
    if render_context == "slide":
        if target_aspect is not None and abs(target_aspect - (16 / 9)) > 0.01:
            raise ValueError("slide target_aspect_ratio must be 16/9")
        canvas["aspect"] = "16:9 landscape (required; no other slide ratio)"
        canvas["margin"] = (
            "Full-bleed canvas; keep the top 19% and bottom 8% visually quiet "
            "because the canonical title/citation chrome overlays those zones"
        )
    if target_aspect is not None and render_context != "slide":
        canvas["aspect"] = (
            "%.4g:1 landscape; preserve this ratio exactly with no anisotropic scaling"
            % target_aspect)

    route_asset = {
        "generated": (
            "Complete publication-grade scientific figure rendered end to end, "
            "including every required label and all final typography directly in pixels."),
        "hybrid": (
            "Last-resort repair route: premium generated scientific illustration "
            "retained after direct-text generation and targeted correction failed. "
            "The remaining exact typographic/data layer is added deterministically."),
        "deterministic": (
            "Deterministic publication-grade scientific figure production brief. "
            "Do not use an image generator for exact plot or data geometry."),
    }[selected_route]
    sections = [
        "USE CASE\nscientific-educational",
        "ASSET\n%s" % route_asset,
        "AUTHORING ROUTE\n%s" % selected_route,
        "REVIEW-STYLE IDENTITY\n%s\n%s" % (
            profile["name"], profile["intent"]),
        "PURPOSE\n%s" % purpose,
    ]
    if selected_route == "generated":
        sections.append(
            "FIRST-PASS DIRECT-TEXT CONTRACT — EXECUTE IN THIS IMAGEGEN CALL\n"
            "Render the entire finished figure now, including all required typography "
            "as an integrated part of the artwork. Do not return a textless base, blank "
            "label zones, placeholders, pseudo-text, or a layout intended for later "
            "typesetting. Render each quoted string in the single exact-text manifest "
            "below exactly once and verbatim; "
            "preserve spelling, capitalization, punctuation, symbols, and numbers. Fit "
            "copy with natural line wrapping and placement, never squeezed or stretched "
            "letterforms. Do not repeat the manifest copy elsewhere in the artwork.")
    if visual_anchor:
        sections.append(
            "DOMINANT VISUAL ANCHOR\n%s" % visual_anchor.strip())
    if render_context == "article":
        sections.append(
            "CAPTION CONTEXT — DO NOT RENDER INSIDE THE ARTWORK\n"
            "Title: %s%s" % (
                title,
                "\nSubtitle: %s" % subtitle.strip() if subtitle else ""))
    elif render_context == "slide":
        sections.append(
            "SLIDE CHROME CONTEXT — DO NOT RENDER INSIDE THE ARTWORK\n"
            "Claim title: %s%s\n"
            "The canonical deck renderer adds this claim, DOI citations, evidence "
            "chip, masthead, and slide counter as real text." % (
                title,
                "\nScope: %s" % subtitle.strip() if subtitle else ""))
    else:
        sections.append("TITLE — RENDER COMPACTLY\n%s" % title)
        if subtitle:
            sections.append("SUBTITLE — RENDER ONLY ONCE\n%s" % subtitle.strip())

    sections.extend([
        "BASE SCIENTIFIC STYLE PROFILE\n%s\n%s" % (
            profiles[selected_profile]["name"],
            profiles[selected_profile]["intent"],
        ),
        "FRAMING\nContext: %s\n%s" % (
            render_context,
            framing.get(
                render_context,
                "Keep the scientific content visually primary.")),
        "TYPOGRAPHY — HARD REQUIREMENT\n"
        "- Render every character in %s throughout; %s is the only acceptable visual fallback.\n"
        "- Text colour: %s. Minimum readable text at 1,536 px width: %s px; body %s px; local headings %s px; compact standalone title %s px; panel letters %s px.\n%s" % (
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
        bullet_section("EDITORIAL ART DIRECTION", profile.get("art_direction", [])),
        bullet_section("CANDIDATE SELECTION STANDARD", profile.get("selection_standard", [])),
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
    if custom_art_direction:
        sections.append(bullet_section(
            "TOPIC-SPECIFIC ART DIRECTION", custom_art_direction))

    geometry_contract = [
        "Preserve the declared canvas aspect ratio exactly from source through final export.",
        "Never resize, condense, expand, shear, or stretch the artwork or typography along one axis.",
        "Every intended circle remains a true circle and every intended square remains square.",
        "Fit copy by wrapping, editing, or moving it—not by distorting glyph proportions.",
    ] + geometry_invariants
    sections.append(bullet_section("GEOMETRY — HARD INVARIANTS", geometry_contract))

    slide_contract = ""
    if render_context == "slide":
        slide_contract = (
            " Keep the top and bottom chrome zones free of essential labels, values, "
            "arrows, and focal structures. Do not render the claim title, citations, "
            "evidence chip, masthead, or slide number in the pixels."
        )
    if selected_route == "generated":
        sections.append(
            "EXACT IN-FIGURE TEXT MANIFEST — RENDER EVERY STRING VERBATIM IN %s\n%s" % (
                font["family"].upper(),
                "\n".join("- %s" % json.dumps(item, ensure_ascii=False)
                          for item in generated_text)))
    elif selected_route == "hybrid":
        if generated_text:
            sections.append(
                "TEXT THE IMAGE MODEL MAY RENDER VERBATIM IN %s\n%s" % (
                    font["family"].upper(),
                    "\n".join("- %s" % json.dumps(item, ensure_ascii=False)
                              for item in generated_text)))
        sections.append(
            "RESERVED DETERMINISTIC OVERLAY COPY — DO NOT RENDER THESE WORDS\n%s\n"
            "Leave optically quiet, compositionally intentional space for this copy. "
            "Render no placeholder glyphs, pseudo-text, letters, numbers, or watermark "
            "in those zones." % "\n".join(
                "- %s" % json.dumps(item, ensure_ascii=False)
                for item in overlay_text))
    else:
        sections.append(
            "EXACT DETERMINISTIC TEXT MANIFEST\n%s" % "\n".join(
                "- %s" % json.dumps(item, ensure_ascii=False)
                for item in rendered_text))

    all_avoid = list(profile["avoid"]) + custom_avoid
    sections.extend([
        bullet_section("AVOID", all_avoid),
        bullet_section("ARCHETYPE QA", archetype["qa"]),
        "FINAL CONTRACT\n"
        + ({
            "generated": (
                "Generate the genuinely polished, fully typeset final figure in this call. "
                "Before returning it, visually verify every quoted manifest string character "
                "by character. Do not leave blank text placeholders, pseudo-text, or add "
                "unlisted copy. Preserve every number, unit, interval, denominator, qualifier, "
                "relationship, font proportion, and geometric invariant."),
            "hybrid": (
                "Generate the polished illustration layer now. Preserve every scientific "
                "relationship and geometry invariant, leave the declared overlay zones quiet, "
                "and render no pseudo-text. The deterministic compositor adds the exact copy."),
            "deterministic": (
                "Render this figure deterministically with mathematically faithful geometry, "
                "natural-width typography, and no anisotropic scaling."),
        }[selected_route])
        + " No watermark, logo, masthead, or imitation journal branding."
        + slide_contract
    ])
    return "\n\n".join(section for section in sections if section)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Build a modular prompt for a Grounded review figure")
    parser.add_argument("--spec", help="JSON evidence and copy specification")
    parser.add_argument("--profile", help="Override the style profile")
    parser.add_argument("--archetype", help="Override the figure archetype")
    parser.add_argument("--review-style", choices=REVIEW_STYLES,
                        help="Override the review writing style")
    parser.add_argument("--render-route", choices=RENDER_ROUTES,
                        help="Override generated, hybrid, or deterministic routing")
    parser.add_argument("--profiles", default=DEFAULT_PROFILES,
                        help="Style profile JSON file")
    parser.add_argument("--writing-styles", default=DEFAULT_WRITING_STYLES,
                        help="Writing-style overlay JSON file")
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
    writing_styles = load_json(args.writing_styles)

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

    prompt = build_prompt(
        load_json(args.spec), profiles, archetypes,
        args.profile, args.archetype, writing_styles,
        args.review_style, args.render_route)
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
