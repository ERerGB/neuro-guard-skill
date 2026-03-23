import WidgetKit
import SwiftUI

// MARK: - Timeline Entry
struct NeuroGuardEntry: TimelineEntry {
    let date: Date
    let tier: String
    let eventTitle: String
    let eventTime: String
    let cutoffTime: String
    let minutesToCutoff: Double
    let snoozeCount: Int
    let maxSnooze: Int
}

// MARK: - Timeline Provider
struct NeuroGuardProvider: TimelineProvider {
    private let telemetryPath = FileManager.default.homeDirectoryForCurrentUser
        .appendingPathComponent(".neuro-guard-telemetry.json")

    private static let fallback = NeuroGuardEntry(
        date: Date(), tier: "OK", eventTitle: "—", eventTime: "—",
        cutoffTime: "—", minutesToCutoff: 0, snoozeCount: 0, maxSnooze: 2
    )

    private func loadTelemetry() -> NeuroGuardEntry {
        guard let data = try? Data(contentsOf: telemetryPath),
              let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            return Self.fallback
        }
        return NeuroGuardEntry(
            date: Date(),
            tier: json["tier"] as? String ?? "OK",
            eventTitle: json["event_title"] as? String ?? "—",
            eventTime: json["event_time"] as? String ?? "—",
            cutoffTime: json["cutoff_time"] as? String ?? "—",
            minutesToCutoff: json["minutes_to_cutoff"] as? Double ?? 0,
            snoozeCount: json["snooze_count"] as? Int ?? 0,
            maxSnooze: json["max_snooze"] as? Int ?? 2
        )
    }

    func placeholder(in context: Context) -> NeuroGuardEntry {
        NeuroGuardEntry(date: Date(), tier: "OK", eventTitle: "—", eventTime: "—", cutoffTime: "—", minutesToCutoff: 165, snoozeCount: 0, maxSnooze: 2)
    }

    func getSnapshot(in context: Context, completion: @escaping (NeuroGuardEntry) -> Void) {
        completion(loadTelemetry())
    }

    func getTimeline(in context: Context, completion: @escaping (Timeline<NeuroGuardEntry>) -> Void) {
        let entry = loadTelemetry()
        let nextUpdate = Calendar.current.date(byAdding: .minute, value: 5, to: Date()) ?? Date()
        let timeline = Timeline(entries: [entry], policy: .after(nextUpdate))
        completion(timeline)
    }
}

// MARK: - Widget View (Matrix-style, matches web card)
struct NeuroGuardWidgetView: View {
    var entry: NeuroGuardEntry
    @Environment(\.widgetFamily) var family

    private var themeColor: Color {
        switch entry.tier {
        case "LOCK": return Color(red: 239/255, green: 68/255, blue: 68/255)
        case "FINAL_WARN": return Color(red: 249/255, green: 115/255, blue: 22/255)
        case "WARN", "DIM": return Color(red: 245/255, green: 158/255, blue: 11/255)
        default: return Color(red: 74/255, green: 222/255, blue: 128/255)
        }
    }

    private var tierLabel: String {
        switch entry.tier {
        case "LOCK": return "LOCKDOWN"
        case "FINAL_WARN": return "CRITICAL"
        case "WARN", "DIM": return "WIND DOWN"
        default: return "NOMINAL"
        }
    }

    private var countdownText: String {
        // Telemetry uses 0 when there is no active cutoff (no event / idle). Avoid showing 00:00.
        let m = entry.minutesToCutoff
        guard m > 0 else { return "— · —" }
        let h = Int(m / 60)
        let min = Int(m.truncatingRemainder(dividingBy: 60))
        return String(format: "%02d:%02d", h, min)
    }

    var body: some View {
        ZStack {
            // Background
            RoundedRectangle(cornerRadius: 20)
                .fill(Color.black.opacity(0.65))
                .overlay(
                    RoundedRectangle(cornerRadius: 20)
                        .stroke(Color.white.opacity(0.1), lineWidth: 1)
                )

            // Ambient glow
            RadialGradient(
                colors: [themeColor.opacity(0.15), Color.clear],
                center: .top,
                startRadius: 0,
                endRadius: 150
            )
            .clipShape(RoundedRectangle(cornerRadius: 20))

            VStack(alignment: .leading, spacing: 10) {
                // Header
                HStack {
                    Text("NEURO GUARD")
                        .font(.system(size: 10, weight: .bold, design: .monospaced))
                        .foregroundColor(.white.opacity(0.5))
                    Spacer()
                    HStack(spacing: 4) {
                        Circle()
                            .fill(themeColor)
                            .frame(width: 5, height: 5)
                            .shadow(color: themeColor, radius: 4)
                        Text(tierLabel)
                            .font(.system(size: 9, weight: .medium, design: .monospaced))
                            .foregroundColor(themeColor)
                    }
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(Color.black.opacity(0.3))
                    .cornerRadius(10)
                }

                // Countdown
                VStack(alignment: .leading, spacing: 4) {
                    Text("Time to Rest Cutoff")
                        .font(.system(size: 9, weight: .medium))
                        .foregroundColor(.white.opacity(0.5))
                    Text(countdownText)
                        .font(.system(size: 28, weight: .light, design: .monospaced))
                        .foregroundColor(.white)
                    Text("Target: \(entry.cutoffTime)")
                        .font(.system(size: 10, weight: .medium))
                        .foregroundColor(themeColor)
                }

                // Event
                VStack(alignment: .leading, spacing: 2) {
                    Text("Next Critical Event")
                        .font(.system(size: 8, weight: .medium))
                        .foregroundColor(.white.opacity(0.5))
                    Text(entry.eventTitle)
                        .font(.system(size: 11, weight: .medium))
                        .lineLimit(1)
                        .truncationMode(.tail)
                    Text("Tomorrow \(entry.eventTime)")
                        .font(.system(size: 9))
                        .foregroundColor(themeColor)
                }
                .padding(8)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(Color.black.opacity(0.2))
                .cornerRadius(12)

                Text("Snoozes: \(entry.maxSnooze - entry.snoozeCount)/\(entry.maxSnooze)")
                    .font(.system(size: 9))
                    .foregroundColor(.white.opacity(0.5))
            }
            .padding(16)
        }
        .widgetURL(URL(string: "http://127.0.0.1:9877/"))
    }
}

// MARK: - Widget
@main
struct NeuroGuardWidget: Widget {
    let kind: String = "NeuroGuardWidget"

    var body: some WidgetConfiguration {
        StaticConfiguration(kind: kind, provider: NeuroGuardProvider()) { entry in
            NeuroGuardWidgetView(entry: entry)
        }
        .configurationDisplayName("Neuro Guard")
        .description("Time to rest cutoff and next critical event.")
        .supportedFamilies([.systemSmall, .systemMedium])
    }
}
