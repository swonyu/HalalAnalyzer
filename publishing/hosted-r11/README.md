# HalalTag R11: distinct hosted successor, inventory stage

This proposal implements **inventory only**. It cannot build, test, archive, sign, upload an app, mutate a simulator, or acquire the native build lock. Its proposed workflow may upload the complete inventory evidence after root binds and publishes this new control. The new native executor and Halal-specific archive verifier remain separate, unimplemented gates.

Revision 2 preserves the frozen revision 1 package and the same inventory protocol. It adds two independent peer corrections: every permitted command gets an exclusive `STARTED` record and immediate file-backed stdout/stderr before launch, and any occupied native-lock path, including a dangling symbolic link, fails eligibility. These changes add no command or native authority. Focused fixtures check success, timeout and interruption without starting a process.

The app is the exact public R11 commit `7ef009beb0c1f6f355eeceb931d899553ea8cad5`, tree `97b9e5eca0e4bc5c82ceb8b133fc823eed1af4bf`. All 165 existing Git files and modes must remain unchanged. The native subset is all 47 original inputs. This proposal adds control files only; it does not modify an app, test, fixture, audit, gesture budget or project setting.

## Why this is separately identified

The original Mac is unavailable. Seventeen of the 23 exact private R10 parent supports were recovered, including the unchanged 61,657-byte frozen lifecycle runner with SHA-256 `1980cdf5a564a802198183fd79ee2f0a325b486908bab45e01beaadb02e50f99`. Six supports remain missing: the current native adapter, production-case evidence validator, original adapter contracts, adapter delta, reference metadata and unconfigured acknowledgment. The older available appearance-only adapters are not relabeled as those files.

The public R5–R11 preparation recipes describe transformations of those private predecessor packages; they do not contain all missing bodies. The frozen R11 source and prior packages remain preserved. A future hosted executor will therefore be an explicit new successor, reviewed against the exact current source and evidence contract. No equivalence to the missing adapter is claimed.

## Exact inventory gate

`inventory_only.py` defaults to pure file inspection. The `inventory` mode requires a concrete root review, public `swonyu/HalalAnalyzer`, the exact proposed push branch, a standard GitHub-hosted macOS ARM64 context and attempt 1. It rejects reused attempts and requires at least ten minutes before the continuing deadline, `2026-11-18T22:26:12Z`.

The workflow uses standard `xcode-27` with `/Applications/Xcode_27.app/Contents/Developer`. The official [runner image inventory](https://github.com/actions/runner-images/blob/main/images/macos/xcode-27-arm64-Readme.md) currently lists Xcode 27.0 build `27A266a`, iOS 27.0 SDKs and an installed iOS 27.0 runtime. That document does not establish the original runtime build or availability of the SE3 device type; the actual hosted machine must prove both.

Before Apple inventory commands, the driver verifies the actual checkout commit, its single exact R11 parent, a clean worktree, every original Git blob and mode, and the complete reviewed control-file set. It also checks the 19 UI selectors against all four original UI test files and the actual case plan. No Git ref is changed.

The permitted Apple commands are `xcodebuild -version`, SDK version queries, `simctl list` for runtimes/device types/devices, and `simctl help ui`. A process-name snapshot and a read-only native-lock existence check are retained. There is no `build`, `test`, `archive`, `create`, `boot`, `install`, `launch`, `shutdown`, `delete`, setting change, runtime download, package installation, lock acquisition or lock cleanup command in this driver.

Actual eligibility requires all of these together:

- macOS 27 on ARM64, the reviewed Xcode build and both exact iOS 27.0 SDKs.
- Device type `com.apple.CoreSimulator.SimDeviceType.iPhone-SE-3rd-generation`, name `iPhone SE (3rd generation)`, model `iPhone14,6`, family `iPhone`, found exactly once.
- Runtime `com.apple.CoreSimulator.SimRuntime.iOS-27-0`, version `27.0`, build `24A5423a`, available and found exactly once.
- No preexisting native build lock, no source/control changes during inventory, and complete evidence collection and upload.

An otherwise usable newer runtime or larger phone fails this gate. No fallback is selected. Even a successful inventory does not prove actual 375×667-point windows or 750×1334-pixel screenshots; the original native assertions must establish those properties later.

## Coverage that the future native successor must retain

`coverage-contract.json` contains every current UI case, all source pins, the full expected model label sequence and the 14 current shipping inputs. The inventory step does not run those checks or turn the historical model fixture into a current result.

| Area | Required current contract | Existing material / new code boundary |
|---|---|---|
| Complete source | All 165 Git blobs/modes; all 47 native SHA-256 bindings | Recovered and verified; new hosted source binding only |
| Model checks | Compile the same three sources; actual `PASS`, exactly 211 checks, complete expected ordered label sequence | Exact current source and public R6/R6b receipt logic recovered; new hosted call binding |
| Nineteen UI methods | English three, functional ten, Arabic three, state three; exact original order; one real matching passed leaf per result; no retries/skips | All four exact current test files and 19-case plan recovered; missing adapter requires new reviewed orchestration |
| Real launch evidence | Exactly 20 original host receipts and 17 distinct supplementary launch UUIDs | Current QA host and test sources recovered; new per-case receipt-delta validator required |
| Appearance and accessibility | Current unfiltered contrast/clipped-text/Dynamic Type audits; original PNG/geometry/AX pairs; measured gesture/recovery limits | Exact English/Arabic guards, PNG helper, size helper and tests recovered |
| Settings and installation | Owned simulator style/text readbacks before and after every method; exact app, test bundle, xctestrun and configured installation resource | Existing lifecycle and available old evidence helpers inform the explicit successor; no claim of missing-adapter equivalence |
| Lifecycle | Same monotonic 45-minute batch, 120-second cleanup reserve, 1,200-second per-case maximum and zero retries; remaining-time caps; only owned process groups and new simulator; no lock release before cleanup proof | Frozen lifecycle file recovered unchanged; new hosted entry and subclass must compose its functions |
| Production archive | Actual shipping project, Release, generic iOS device, unsigned; original bundle/team/version/minimum-OS/device families; retained archive and archive xcresult | Frozen generic archive function recovered; explicit new Halal resource/privacy/minimum-OS verifier required |
| Original evidence | All per-case xcresults, summaries, trees, original attachments/PNG/AX/host receipts, raw logs and archive evidence | New complete packaging and measured cost gate required; no silent evidence truncation |

The original model labels are not globally unique: the Arabic sample-preview label intentionally appears three times. The public R6b repair removed an incorrect global uniqueness requirement. The nine boundary regression labels must each occur once. The three current model source Git blobs are byte-identical to the source that produced the historical 211-entry fixture; the successor contract preserves the entire sequence, including the repeated labels.

The recovered `Runner.production_archive` rejects `UI_TESTING`, requires one app target, retains effective Release settings, creates `Production.xcarchive` and `ProductionArchive.xcresult`, verifies bundle identity, populated icon metadata and a nonempty `Assets.car`, and rejects signing material. Its app-specific external verifier is only called for Lumina. A new Halal verifier must additionally bind the current privacy manifest/resources, `HalalTag.v1.1`, team `WY272L3F3N`, version `1.0`/build `1`, iOS minimum `26.5`, supported device families and absence of QA content. The generic function is not represented as already proving those Halal-specific gates.

The QA target uses a dedicated `.qa.r20261117r11` identity and a Debug/simulator-only host. Only a run-owned copy of its test installation manifest may be configured, after actual build/install evidence exists. The frozen original, shipping source and all test assertions stay unchanged. Shipping lifecycle smoke, iPad/orientation behavior, physical VoiceOver, signing and store release remain separately evidenced requirements.

## Evidence and zero-dollar scope

Every command retains its original stdout, stderr, command, result and digest. Failures still produce a failed report and are eligible for evidence collection. A malformed or missing final report cannot produce acceptance; the collector retains the original and records the failure separately. No file is omitted from the inventory archive. Its contents and hashes are checked after packing.

The inventory archive is capped at 20,000,000 bytes with one-day retention. An oversized archive is not truncated or uploaded; originals and the complete archive are left in the job workspace, and the job fails. They are not claimed as durable external evidence until the actual upload succeeds and root later downloads/verifies it. A native attempt's much larger raw evidence needs its own measured packaging and budget review.

Only standard public hosted compute is proposed. GitHub's [billing documentation](https://docs.github.com/en/billing/concepts/product-billing/github-actions) distinguishes free standard public runners from paid larger runners and separately measured storage. The existing root-reviewed zero-dollar budget receipt is referenced by SHA-256 only; no account billing detail is published. No cache, larger runner, storage purchase, dependency installation or automatic retry is added.

## Root binding and review

The submitted candidate is `UNBOUND`, with no `root-review.json`. Root must review the sealed proposal and independent peer, then create an actual review that binds the proposal receipt, peer receipt, unchanged candidate contract and every control file. Only `authorization` and `root_review_sha256` in `candidate.json` are excluded from the candidate contract digest. The actual reviewed root receipt is itself pinned by `root_review_sha256`.

Root alone owns publishing the new branch. A push to the exact branch triggers this inventory-only job; it does not authorize a native successor. The workflow accepts the inventory only if the actual preflight, complete collection and upload all succeed, and a real artifact ID, outer digest and inner archive digest are present. A queued job, collected file or intended upload is not accepted as completed delivery.
