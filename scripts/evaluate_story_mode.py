"""Optional real-provider narrative review. No API calls unless --live is given."""

import argparse
import json
from pathlib import Path
from types import SimpleNamespace

from echoloom.config import Settings
from echoloom.providers import OpenAIText, ProviderError
from echoloom.schemas import Profile
from echoloom.story_context import story_context


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live",
        action="store_true",
        help="Run 12 paid story requests (each may need one correction).",
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    cases = json.loads((root / "docs/mvp/story-evaluation-cases.json").read_text())
    if not args.live:
        print(
            f"{len(cases)} fixed narrative cases available. No AI calls made. Use --live for paid evaluation."
        )
        return
    settings = Settings()
    if not settings.llm_api_key.get_secret_value() or not settings.llm_model:
        raise SystemExit(
            "Configure LLM_API_KEY and LLM_MODEL securely before running live evaluation."
        )
    provider = OpenAIText(settings)
    report = []
    for case in cases:
        story = SimpleNamespace(
            snapshot_profile_json=Profile(
                name="Evelyn",
                personality={"core_traits": ["Reserved", "Caring"]},
                speech_style={"tone": "Calm and dry"},
            ).model_dump(),
            player_name="Alex",
            setup={
                "description": case["scene"],
                "constraints": "Do not make major decisions for the player.",
            },
        )
        row = {
            "id": case["id"],
            "hazard": case["hazard"],
            "human_review": {
                "agency": "pending",
                "profile_consistency": "pending",
                "choice_consequences": "pending",
                "readability": "pending",
            },
        }
        try:
            output = provider.story(
                story_context(story, [], case.get("event", {"kind": "start"}), settings)
            )
            row.update(technical_validation="passed", output=output.model_dump())
        except ProviderError as error:
            row.update(technical_validation="failed", error=str(error))
        report.append(row)
        print(case["id"], row["technical_validation"], "human review pending")
    destination = root / "work/story-evaluation.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps({"model": settings.llm_model, "cases": report}, indent=2)
    )
    print(
        f"Saved {destination}. Technical validation is not narrative acceptance; complete human review."
    )


if __name__ == "__main__":
    main()
