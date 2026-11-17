#if !os(iOS) || !targetEnvironment(simulator) || !DEBUG
#error("This external appearance host is Debug iOS Simulator QA only.")
#endif
import Foundation
import SwiftUI
import UIKit

private let appearanceQAID = "com.saleh.halaltag.productioncomposition.qa.r20261117r9"

@MainActor
private struct AppearanceFixture {
    let caseID: String
    let runID: String
    let style: UIUserInterfaceStyle
    let category: UIContentSizeCategory
    let languageLaunchID: String?

    init() {
        precondition(Bundle.main.bundleIdentifier == appearanceQAID, "Unexpected QA identity")
        let args = CommandLine.arguments
        func one(_ key: String) -> String {
            let indices = args.indices.filter { args[$0] == key }
            precondition(indices.count == 1 && indices[0] + 1 < args.count, "Missing/duplicate QA argument")
            return args[indices[0] + 1]
        }
        let languageIndices = args.indices.filter { args[$0] == "--language-launch-id" }
        precondition(languageIndices.count <= 1, "Duplicate language launch identifier")
        if let index = languageIndices.first {
            precondition(index + 1 < args.count && UUID(uuidString: args[index + 1]) != nil,
                         "Invalid language launch identifier")
            languageLaunchID = args[index + 1]
        } else { languageLaunchID = nil }
        let selected = one("--appearance-case")
        let run = one("--appearance-run-id")
        precondition(UUID(uuidString: run) != nil, "Invalid bound QA run")
        switch selected {
        case "light-large": style = .light; category = .large
        case "dark-large": style = .dark; category = .large
        case "light-accessibility5": style = .light; category = .accessibilityExtraExtraExtraLarge
        default: preconditionFailure("Unreviewed appearance case")
        }
        caseID = selected
        runID = run
    }

    func record(window: UIWindow, host: UIViewController) {
        guard let scene = window.windowScene else { preconditionFailure("Missing owned window scene") }
        // The runner sets the owned simulator's user setting before this launch.
        // Do not override SwiftUI or UIKit size: the audit must be able to change it.
        let applicationCategory = UIApplication.shared.preferredContentSizeCategory
        let sceneCategory = scene.traitCollection.preferredContentSizeCategory
        precondition([applicationCategory, sceneCategory,
                      window.traitCollection.preferredContentSizeCategory,
                      host.traitCollection.preferredContentSizeCategory].allSatisfy { $0 == category },
                     "Initial inherited system size does not match the bound case")
        func frame(_ r: CGRect) -> [String: CGFloat] {
            ["x": r.minX, "y": r.minY, "width": r.width, "height": r.height]
        }
        var value: [String: Any] = [
            "schema_version": 1, "run_id": runID, "case_id": caseID,
            "bundle_id": Bundle.main.bundleIdentifier ?? "",
            "requested_style": style.rawValue,
            "window_style": window.traitCollection.userInterfaceStyle.rawValue,
            "host_style": host.traitCollection.userInterfaceStyle.rawValue,
            "requested_content_size": category.rawValue,
            "content_size_source": "INHERITED_SYSTEM_SETTING",
            "application_content_size": applicationCategory.rawValue,
            "scene_content_size": sceneCategory.rawValue,
            "window_content_size": window.traitCollection.preferredContentSizeCategory.rawValue,
            "host_content_size": host.traitCollection.preferredContentSizeCategory.rawValue,
            "screen_bounds": frame(scene.screen.bounds),
            "screen_native_bounds": frame(scene.screen.nativeBounds),
            "screen_scale": scene.screen.scale, "screen_native_scale": scene.screen.nativeScale,
            "scene_bounds": frame(scene.coordinateSpace.bounds), "window_frame": frame(window.frame),
            "host_frame": frame(host.view.convert(host.view.bounds, to: window)),
            "safe_area_top": host.view.safeAreaInsets.top, "safe_area_bottom": host.view.safeAreaInsets.bottom,
            "orientation": scene.interfaceOrientation.rawValue,
            "artificial_window_resize": false, "fixed_inner_container": false,
            "recorded_at": ISO8601DateFormatter().string(from: Date())
        ]
        if let languageLaunchID { value["language_launch_id"] = languageLaunchID }
        do {
            let documents = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
            var folder = documents.appendingPathComponent("AppearanceQA", isDirectory: true)
                .appendingPathComponent(runID, isDirectory: true).appendingPathComponent(caseID, isDirectory: true)
            if let languageLaunchID { folder.appendPathComponent(languageLaunchID, isDirectory: true) }
            precondition(!FileManager.default.fileExists(atPath: folder.path), "A case cannot silently run twice")
            try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
            let data = try JSONSerialization.data(withJSONObject: value, options: [.sortedKeys, .prettyPrinted])
            try data.write(to: folder.appendingPathComponent("started.json"), options: .atomic)
        } catch { preconditionFailure("Could not retain actual native trait evidence: \(error)") }
    }
}

@MainActor
private final class AppearanceHostingController: UIHostingController<AnyView> {
    var onFirstAppearance: (() -> Void)?
    private var recorded = false
    override func viewDidAppear(_ animated: Bool) {
        super.viewDidAppear(animated)
        if !recorded { recorded = true; onFirstAppearance?() }
    }
    override var supportedInterfaceOrientations: UIInterfaceOrientationMask { .portrait }
}

@MainActor
final class AppearanceSceneDelegate: UIResponder, UIWindowSceneDelegate {
    var window: UIWindow?
    func scene(_ scene: UIScene, willConnectTo session: UISceneSession, options connectionOptions: UIScene.ConnectionOptions) {
        guard let scene = scene as? UIWindowScene else { preconditionFailure("Expected a native window scene") }
        let fixture = AppearanceFixture()
        let window = UIWindow(windowScene: scene)
        let host = AppearanceHostingController(rootView: AnyView(ContentView()))
        window.overrideUserInterfaceStyle = fixture.style
        window.rootViewController = host
        self.window = window
        host.onFirstAppearance = { [weak window, weak host] in
            guard let window, let host else { preconditionFailure("Owned QA window disappeared") }
            fixture.record(window: window, host: host)
        }
        window.makeKeyAndVisible()
    }
}

@main
@MainActor
final class AppearanceAppDelegate: UIResponder, UIApplicationDelegate {
    func application(_ application: UIApplication, didFinishLaunchingWithOptions options: [UIApplication.LaunchOptionsKey: Any]? = nil) -> Bool { true }
    func application(_ application: UIApplication, configurationForConnecting session: UISceneSession, options: UIScene.ConnectionOptions) -> UISceneConfiguration {
        let config = UISceneConfiguration(name: "HalalTagAppearanceQA", sessionRole: session.role)
        config.delegateClass = AppearanceSceneDelegate.self
        return config
    }
}
