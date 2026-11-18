"""Pure final gate: evidence delivery never substitutes for native acceptance."""
import json
import os
import re


def exact_digest(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def positive(value):
    return isinstance(value, str) and re.fullmatch(r"[1-9][0-9]*", value) is not None


def evaluate(env):
    common = all(env.get(key) == "success" for key in (
        "INSPECT_OUTCOME", "RESERVATION_OUTCOME", "NATIVE_OUTCOME", "COLLECT_OUTCOME"))
    common = common and env.get("COMPUTATION_GATE_PASSED") == "true"
    common = common and exact_digest(env.get("ARCHIVE_SHA256")) and positive(env.get("ARCHIVE_BYTES"))
    route = env.get("EVIDENCE_ROUTE")
    actions = (route == "actions_artifact" and env.get("UPLOAD_OUTCOME") == "success"
               and env.get("RELEASE_OUTCOME") == "skipped" and positive(env.get("ARTIFACT_ID"))
               and isinstance(env.get("ARTIFACT_DIGEST"), str)
               and re.fullmatch(r"(sha256:)?[0-9a-f]{64}", env["ARTIFACT_DIGEST"]) is not None)
    release = (route == "root_bound_draft_assets" and env.get("UPLOAD_OUTCOME") == "skipped"
               and env.get("RELEASE_OUTCOME") == "success" and env.get("RELEASE_DELIVERY_VERIFIED") == "true"
               and positive(env.get("RELEASE_ID")) and positive(env.get("DELIVERY_RECEIPT_ASSET_ID"))
               and exact_digest(env.get("DELIVERY_RECEIPT_SHA256"))
               and env.get("RELEASE_ARCHIVE_SHA256") == env.get("ARCHIVE_SHA256")
               and env.get("RELEASE_ARCHIVE_BYTES") == env.get("ARCHIVE_BYTES"))
    keys = ("INSPECT_OUTCOME", "RESERVATION_OUTCOME", "NATIVE_OUTCOME", "COLLECT_OUTCOME", "UPLOAD_OUTCOME",
            "RELEASE_OUTCOME", "COMPUTATION_GATE_PASSED", "EVIDENCE_ROUTE", "ARCHIVE_SHA256", "ARCHIVE_BYTES",
            "ARTIFACT_ID", "ARTIFACT_DIGEST", "RELEASE_ID", "DELIVERY_RECEIPT_ASSET_ID", "DELIVERY_RECEIPT_SHA256")
    return {"observed": {key: env.get(key, "") for key in keys},
            "original_model_ui_unsigned_archive_and_evidence_passed": bool(common and (actions or release)),
            "complete_delivery_route": route if actions or release else "NOT_VERIFIED",
            "independent_download_original_pixel_review_and_Grok_delivery": "PENDING",
            "distribution_signing": "NOT_PERFORMED", "release_is_evidence_only_draft": bool(release),
            "store_release": False}


def main():
    receipt = evaluate(os.environ)
    text = json.dumps(receipt, indent=2)
    print(text)
    with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as stream:
        stream.write("## HalalTag native and complete evidence receipt\n\n```json\n" + text + "\n```\n")
    return 0 if receipt["original_model_ui_unsigned_archive_and_evidence_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
