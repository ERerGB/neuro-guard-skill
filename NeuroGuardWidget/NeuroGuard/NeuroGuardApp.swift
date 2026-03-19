import SwiftUI
import WidgetKit

@main
struct NeuroGuardApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) var appDelegate

    var body: some Scene {
        Settings {
            EmptyView()
        }
    }
}

class AppDelegate: NSObject, NSApplicationDelegate {
    private var statusItem: NSStatusItem?
    private var syncTimer: Timer?
    private let telemetryPath = FileManager.default.homeDirectoryForCurrentUser
        .appendingPathComponent(".neuro-guard-telemetry.json")

    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.accessory)

        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        if let button = statusItem?.button {
            button.title = "🟢"
        }

        let menu = NSMenu()
        let openItem = NSMenuItem(title: "Open full view", action: #selector(openFullView), keyEquivalent: "")
        openItem.target = self
        menu.addItem(openItem)
        menu.addItem(NSMenuItem.separator())
        let quitItem = NSMenuItem(title: "Quit", action: #selector(quit), keyEquivalent: "q")
        quitItem.target = self
        menu.addItem(quitItem)
        statusItem?.menu = menu

        updateMenuBarIcon()
        syncTimer = Timer.scheduledTimer(withTimeInterval: 10, repeats: true) { [weak self] _ in
            self?.updateMenuBarIcon()
        }
        RunLoop.current.add(syncTimer!, forMode: .common)
    }

    @objc private func updateMenuBarIcon() {
        guard let data = try? Data(contentsOf: telemetryPath),
              let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let tier = json["tier"] as? String else { return }

        let emoji: String
        switch tier {
        case "LOCK": emoji = "🔴"
        case "FINAL_WARN": emoji = "🟠"
        case "WARN", "DIM": emoji = "🟡"
        default: emoji = "🟢"
        }
        statusItem?.button?.title = emoji

        WidgetCenter.shared.reloadAllTimelines()
    }

    @objc private func openFullView() {
        NSWorkspace.shared.open(URL(string: "http://127.0.0.1:9877/")!)
    }

    @objc private func quit() {
        NSApp.terminate(nil)
    }
}
