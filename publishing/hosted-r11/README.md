# HalalTag R11: explicit installed-runtime inventory successor v3

This is an **unbound inventory-only proposal**. Root must review, bind and publish a new branch before an actual attempt. It contains no native build, test, archive, signing, simulator mutation or store-publication authority.

## Why this new platform contract is explicit

The original exact-platform inventory ran on commit `7394b369aaf85fb99830af6ceeb2de4f4c35097e`, run `44346043468`, attempt 1. It **failed** because the required iOS 27.0 runtime build `24A5423a` was absent. Its original outcome remains failed. Collection and upload succeeded; they did not make the platform eligible. The final workflow gate correctly checked the failed step outcome despite `continue-on-error`.

The downloaded original artifact is 45,177 bytes with SHA-256 `85c3a63040eba18dd325b9f65fe0d1a2e1df4573f8aa70a71c4fb7fa38978d4b`. Its 44,963-byte inner archive has SHA-256 `36f3e7702636819f335bc2aacdc4b05f427fa93024ee850128ad89da7d3b37ee`. All 58 tar members, 57 indexed original files, 13 command records/raw streams, all 165 original Git blobs/modes, 47 native hashes and eight bound controls were verified. The complete failed artifact and verification receipt accompany this proposal in `Review/`.

That real hosted inventory observed macOS 27.0.1, Xcode 27.0 build `27A266a`, both iOS 27.0 SDKs, and the exact iPhone SE (3rd generation) device type/model `iPhone14,6`. The installed matching iOS 27.0 runtime is build **`24A434`**. Other installed iOS entries were 27.1 and 27.2 variants. Version 3 proposes only that specific observed iOS 27.0 build; it never selects a runtime automatically.

The candidate's `platform_revision` binds the original failure, real artifact IDs/hashes, original build, new build and scope. The driver checks that complete literal contract. Root's receipt binds the candidate contract and actual control bytes. This is new platform evidence; it does not establish that the original runtime gate passed, and does not establish equivalence of native results across builds.

## Preserved app and test requirements

The original app source remains commit `7ef009beb0c1f6f355eeceb931d899553ea8cad5`, tree `97b9e5eca0e4bc5c82ceb8b133fc823eed1af4bf`. The workflow commit must be exactly one direct child of that source commit. Every one of the 165 original Git blobs and modes remains unchanged, including all 47 native inputs. The source index and coverage contract are byte-identical to inventory v2.

All 19 UI cases and their exact original order, all 211 model labels in their expected sequence, all 20 host receipts and 17 distinct supplementary launch UUIDs remain required. The nine boundary labels still occur once each; the original Arabic preview label repetition is retained. Inventory never executes those tests or turns a historical fixture into a current pass.

The original native window and screenshot assertions remain **375 × 667 points** and **750 × 1334 pixels**. All original appearance, accessibility, clipped-text, Dynamic Type, navigation, recovery, real-launch, installation and evidence assertions remain unchanged. The original 45-minute native limit, 120-second cleanup reserve, 1,200-second per-case maximum and zero retries remain the native successor's obligations. This read-only inventory does not prove any native geometry or behavior.

The original native R11 result remains 211 model checks and 14 completed UI cases followed by SIGTERM; all 19 current UI cases and a production archive remain unverified. All six formerly missing private parent supports were recovered exactly in the resumption, with their original bytes preserved. This availability does not grant native ownership or relax the original Mac hold.

## Exact new inventory boundary

The new scope is `HALALTAG_R11_INSTALLED_RUNTIME_HOSTED_INVENTORY_V3` and the new push branch is `continuation/halaltag-r11-hosted-preflight-v3-d57`. No old attempt is rerun. All public repository, first-attempt, hosted ARM64, root binding, source identity and deadline checks remain in force. The continuing deadline is `2026-11-18T22:26:12Z`; starting inventory requires at least ten minutes remaining.

The platform must still prove macOS 27, Xcode 27.0 build `27A266a`, both 27.0 SDKs, exactly one SE3 device type with original model/family, and exactly one available `com.apple.CoreSimulator.SimRuntime.iOS-27-0` runtime, version `27.0`, build `24A434`. A missing, duplicated, unavailable, older or newer runtime fails. An occupied native-lock path, including a dangling symbolic link, fails without mutation.

The command allowlist is unchanged: source Git inspection; Xcode/SDK version reads; simulator runtime/device type/device listings; simulator UI help; process-name inventory. Every command has exclusive STARTED and terminal receipts and immediate original stdout/stderr files. No build, test, archive, simulator create/boot/install/launch/change/shutdown/delete, download, package install or lock mutation is present.

Complete output collection still includes every original file and a checked member index. The 20,000,000-byte artifact cap, one-day retention, standard `xcode-27` runner, zero additional spend, read-only token, pinned actions and no-cancel concurrency policy remain unchanged. Root must confirm current included storage for the complete archive plus upload overhead before publishing. The prior zero-dollar policy pin alone is not a fresh storage allowance.

The actual new job, complete collection, artifact upload and later download/hash/member verification must succeed before a new accepted-platform receipt exists. A queued job or successful failed-evidence upload is not acceptance. Native execution requires a separate reviewed successor, new root binding, actual current platform recheck, complete original evidence preservation and all native/archive gates.

## Review artifacts

`Review/PROPOSAL-RECEIPT.json` binds every file and the payload ZIP. `Review/root-review-UNCONFIGURED.json` is a template, not authorization. The submitted candidate remains `UNBOUND` with no root receipt. Only its `authorization` and `root_review_sha256` fields are excluded from its canonical contract digest. Root alone owns final binding and GitHub publication.
