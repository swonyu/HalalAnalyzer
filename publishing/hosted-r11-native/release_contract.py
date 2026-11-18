"""Pure contract for one root-created evidence-only draft; no API calls."""
from datetime import datetime
import hashlib
import json
import re


REPOSITORY = "swonyu/HalalAnalyzer"
SOURCE_COMMIT = "7ef009beb0c1f6f355eeceb931d899553ea8cad5"
CANDIDATE_NONCE = "d57f4cd778134ea0b2b9e744147c364e"
TAG = "evidence/halaltag-r11-7ef009beb0c1-" + CANDIDATE_NONCE
TITLE = "HalalTag R11 evidence only " + CANDIDATE_NONCE
BODY = ("Evidence-only draft for the reviewed HalalTag R11 candidate " + CANDIDATE_NONCE + ".\n\n"
        "Source: " + SOURCE_COMMIT + ".\n"
        "This draft is not an app release, store submission, native pass, or permission to publish.\n"
        "A single first-attempt hosted run may reserve it and retain complete original evidence.\n"
        "The actual run, attempt, control commit, unchanged verdict, and downloaded asset hashes "
        "must be recorded separately. Do not publish, overwrite, delete, or retry this draft.\n")
POLICY = {"schema_version": 1, "repository": REPOSITORY, "source_commit": SOURCE_COMMIT,
          "candidate_nonce": CANDIDATE_NONCE, "tag": TAG, "title": TITLE,
          "body_sha256": hashlib.sha256(BODY.encode()).hexdigest(),
          "draft": True, "prerelease": True, "tag_target_type": "commit",
          "tag_target_sha": SOURCE_COMMIT, "initial_assets": [],
          "release_create_update_publish_delete_allowed": False,
          "tag_create_update_delete_allowed": False, "asset_overwrite_delete_retry_allowed": False,
          "maximum_asset_bytes": {"evidence.tar.gz": 2_000_000_000,
                                  "complete-member-index.json": 40_000_000,
                                  "verdict.json": 16_384, "delivery-receipt.json": 1_000_000,
                                  "reservation.json": 16_384},
          "maximum_actions_artifact_bytes": 500_000_000, "additional_spend_usd": 0,
          "runtime_token_permission": "contents:write",
          "runtime_token_used_only_for_existing_draft_assets": True,
          "automatic_retries": 0, "run_attempt": 1,
          "claim_before_native_required": True, "complete_download_hash_crc_gate_required": True}


def require(value, message):
    if not value:
        raise ValueError(message)


def canonical(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=True, indent=2, allow_nan=False) + "\n").encode()


def validate_binding(binding, *, allow_unbound=False):
    require(isinstance(binding, dict) and binding.get("policy") == POLICY,
            "Evidence draft policy differs from the fixed reviewed limits and source")
    if allow_unbound and binding.get("authorization") == "UNBOUND":
        return
    require(binding.get("authorization") == "ROOT_VERIFIED_NEW_EMPTY_EVIDENCE_ONLY_DRAFT",
            "Root has not verified an existing fresh empty evidence-only draft")
    for key in ("release_id", "author_id"):
        require(type(binding.get(key)) is int and binding[key] > 0, "Unbound existing draft identity")
    require(isinstance(binding.get("author_login"), str)
            and re.fullmatch(r"[A-Za-z0-9-]{1,39}", binding["author_login"]), "Unbound draft author")
    for key in ("creation_receipt_sha256", "free_route_review_receipt_sha256"):
        require(re.fullmatch(r"[a-f0-9]{64}", str(binding.get(key, ""))), "Unbound root draft/cost review receipt")
    created = datetime.fromisoformat(binding["created_at"].replace("Z", "+00:00"))
    require(created.tzinfo is not None, "Missing actual draft creation time")
    require(binding.get("root_existing_auth_route_verified") is True
            and binding.get("root_created_tag_and_draft_before_native") is True
            and binding.get("fresh_empty_asset_list_verified") is True,
            "Existing auth, source tag, draft creation and empty asset set require actual root evidence")


def expected_claim(config, env):
    require(re.fullmatch(r"[1-9][0-9]{0,29}", env.get("GITHUB_RUN_ID", ""))
            and env.get("GITHUB_RUN_ATTEMPT") == "1"
            and re.fullmatch(r"[a-f0-9]{40}", env.get("GITHUB_SHA", "")), "Malformed one-shot run identity")
    return {"schema_version": 1, "scope": "EVIDENCE_DRAFT_RESERVATION_ONLY_NOT_NATIVE_ACCEPTANCE",
            "repository": REPOSITORY, "source_commit": SOURCE_COMMIT,
            "candidate_nonce": CANDIDATE_NONCE, "release_id": config["evidence_release"]["release_id"],
            "tag": TAG, "run_id": env["GITHUB_RUN_ID"], "run_attempt": 1,
            "workflow_commit": env["GITHUB_SHA"], "root_review_sha256": config["root_review_sha256"],
            "native_pass": False, "full_evidence_delivered": False, "store_release": False}


def asset_name(env, original_name):
    require(original_name in POLICY["maximum_asset_bytes"], "Unreviewed release evidence file")
    if original_name == "reservation.json":
        return "reservation-" + CANDIDATE_NONCE + ".json"
    require(re.fullmatch(r"[1-9][0-9]{0,29}", env.get("GITHUB_RUN_ID", ""))
            and env.get("GITHUB_RUN_ATTEMPT") == "1"
            and re.fullmatch(r"[a-f0-9]{40}", env.get("GITHUB_SHA", "")), "Malformed evidence asset run identity")
    return "r11-" + CANDIDATE_NONCE + "-" + env["GITHUB_RUN_ID"] + "-1-" + env["GITHUB_SHA"] + "-" + original_name


def validate_remote_release(binding, release, tag):
    validate_binding(binding)
    rid = binding["release_id"]
    require(isinstance(release, dict) and release.get("id") == rid and release.get("draft") is True
            and release.get("prerelease") is True and release.get("tag_name") == TAG
            and release.get("target_commitish") == SOURCE_COMMIT and release.get("name") == TITLE
            and release.get("body") == BODY and release.get("created_at") == binding["created_at"]
            and release.get("published_at") is None and release.get("immutable", False) is False,
            "Root-bound evidence draft changed or was published")
    require(release.get("author", {}).get("id") == binding["author_id"]
            and release["author"].get("login") == binding["author_login"], "Draft author differs from root receipt")
    require(release.get("url") == f"https://api.github.com/repos/{REPOSITORY}/releases/{rid}"
            and release.get("upload_url") == f"https://uploads.github.com/repos/{REPOSITORY}/releases/{rid}/assets{{?name,label}}",
            "Release API or upload destination is not the bound GitHub repository and release")
    require(isinstance(tag, dict) and tag.get("ref") == "refs/tags/" + TAG
            and tag.get("object", {}).get("type") == "commit"
            and tag["object"].get("sha") == SOURCE_COMMIT, "Root-created exact source tag changed or is absent")
