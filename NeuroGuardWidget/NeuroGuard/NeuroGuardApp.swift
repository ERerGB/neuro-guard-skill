import AppKit
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
        applyMenuBarIcon(tier: "OK")

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

    /// SF Symbol names — template rendering matches system menu bar (black / white by appearance).
    private static func symbolName(forTier tier: String) -> String {
        switch tier {
        case "LOCK": return "lock.fill"
        case "FINAL_WARN": return "exclamationmark.triangle.fill"
        case "WARN", "DIM": return "exclamationmark.circle"
        default: return "circle"
        }
    }

    /// Monochrome status item (no emoji); urgency only by glyph shape + tooltip.
    private func applyMenuBarIcon(tier: String) {
        guard let button = statusItem?.button else { return }
        let name = Self.symbolName(forTier: tier)
        let config = NSImage.SymbolConfiguration(pointSize: 11, weight: .medium)
        if let image = NSImage(systemSymbolName: name, accessibilityDescription: "Neuro Guard")?
            .withSymbolConfiguration(config) {
            image.isTemplate = true
            button.title = ""
            button.image = image
            button.imagePosition = .imageOnly
        } else {
            // Fallback if SF Symbols unavailable (should not happen on macOS 14+)
            button.image = nil
            button.title = "●"
        }
        button.toolTip = "Neuro Guard · \(tier)"
    }

    @objc private func updateMenuBarIcon() {
        var tier = "OK"
        if let data = try? Data(contentsOf: telemetryPath),
           let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
           let t = json["tier"] as? String {
            tier = t
        }
        applyMenuBarIcon(tier: tier)
        WidgetCenter.shared.reloadAllTimelines()
    }

    @objc private func openFullView() {
        NSWorkspace.shared.open(URL(string: "http://127.0.0.1:9877/")!)
    }

    @objc private func quit() {
        NSApp.terminate(nil)
    }
}
