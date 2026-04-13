import AVFoundation
import SwiftUI
import UIKit

struct UiCard: Identifiable {
    let id = UUID()
    let suit: Int
    let rank: Int
    var held: Bool
    var winning: Bool = false
}

struct GameVariantUi: Identifiable {
    let id: String
    let name: String
    let rtpText: String
    let isPremium: Bool
}

private enum AppSheet: Identifiable {
    case help
    case settings

    var id: String {
        switch self {
        case .help: return "help"
        case .settings: return "settings"
        }
    }
}

private enum TrainerHapticEvent {
    case cardHoldToggled
    case dealPerformed
    case drawPerformed
    case winResultShown
}

private enum TrainerSoundEvent {
    case cardHoldToggled
    case dealPerformed
    case drawPerformed
    case winResultShown
}

private final class TrainerHaptics {
    private let selectionGenerator = UISelectionFeedbackGenerator()
    private let impactGenerator = UIImpactFeedbackGenerator(style: .light)
    private let successGenerator = UINotificationFeedbackGenerator()

    func perform(_ event: TrainerHapticEvent, enabled: Bool) {
        guard enabled else {
            return
        }

        switch event {
        case .cardHoldToggled:
            selectionGenerator.prepare()
            selectionGenerator.selectionChanged()
        case .dealPerformed, .drawPerformed:
            impactGenerator.prepare()
            impactGenerator.impactOccurred(intensity: 0.75)
        case .winResultShown:
            successGenerator.prepare()
            successGenerator.notificationOccurred(.success)
        }
    }
}

private final class TrainerSounds {
    private let players: [TrainerSoundEvent: AVAudioPlayer]

    init() {
        var loadedPlayers: [TrainerSoundEvent: AVAudioPlayer] = [:]
        let soundFiles: [(TrainerSoundEvent, String)] = [
            (.cardHoldToggled, "sfx_card_tap"),
            (.dealPerformed, "sfx_deal"),
            (.drawPerformed, "sfx_draw"),
            (.winResultShown, "sfx_win_chime")
        ]
        for (event, resourceName) in soundFiles {
            guard let url = Bundle.main.url(forResource: resourceName, withExtension: "wav"),
                  let player = try? AVAudioPlayer(contentsOf: url) else {
                continue
            }
            player.volume = 0.35
            player.prepareToPlay()
            loadedPlayers[event] = player
        }
        players = loadedPlayers
    }

    func play(_ event: TrainerSoundEvent, enabled: Bool) {
        guard enabled, let player = players[event] else {
            return
        }
        player.currentTime = 0
        player.play()
    }
}

struct ContentView: View {
    @State private var selectedVariantId: String = "jacks_or_better_9_6"
    @State private var bet: Int = 5
    @State private var initialCards: [UiCard] = []
    @State private var finalCards: [UiCard] = []
    @State private var payout: Int = 0
    @State private var errorText: String = ""
    @State private var suggestedMask: Int = 0
    @State private var explanationCategory: String = ""
    @State private var explanationLabel: String = ""
    @State private var explanationSummary: String = ""
    @State private var explanationPatternTip: String = ""
    @State private var showExplanationDetails: Bool = false
    @State private var mistakeSeverity: String = ""
    @State private var mistakeEvDelta: Double? = nil
    @State private var solverNextBest: String = ""
    @State private var solverBestEV: Double? = nil
    @State private var solverNextEV: Double? = nil
    @State private var canDraw: Bool = false
    @State private var autoHoldEnabled: Bool = true
    @State private var autoShowExplanation: Bool = false
    @State private var soundEnabled: Bool = true
    @State private var hapticsEnabled: Bool = true
    @State private var showPaytable: Bool = false
    @State private var activeSheet: AppSheet?
    @State private var settingsMessage: String?

    private let bridge = PokerEngineBridge(seed: UInt64(Date().timeIntervalSince1970 * 1000))
    private let haptics = TrainerHaptics()
    private let sounds = TrainerSounds()
    private let gameVariants: [GameVariantUi] = [
        GameVariantUi(id: "jacks_or_better_9_6", name: "Jacks or Better 9/6", rtpText: "99.54%", isPremium: false),
        GameVariantUi(id: "jacks_or_better_8_5", name: "Jacks or Better 8/5", rtpText: "97.30%", isPremium: false)
    ]
    private var selectedVariant: GameVariantUi {
        gameVariants.first(where: { $0.id == selectedVariantId }) ?? gameVariants[0]
    }
    private var appVersionText: String {
        let version = Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? "1.0"
        let build = Bundle.main.object(forInfoDictionaryKey: "CFBundleVersion") as? String ?? "1"
        return "\(version) (\(build))"
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 8) {
                    VStack(spacing: 8) {
                        Picker("Game", selection: $selectedVariantId) {
                            ForEach(gameVariants) { variant in
                                Text(variant.name).tag(variant.id)
                            }
                        }
                        .pickerStyle(.menu)

                        Text("Expected RTP (optimal play): \(selectedVariant.rtpText)")
                            .font(.subheadline)
                            .foregroundColor(.secondary)
                            .multilineTextAlignment(.center)

                        VStack(spacing: 6) {
                            Button(showPaytable ? "Hide Paytable" : "Show Paytable") {
                                showPaytable.toggle()
                            }
                            .font(.caption.weight(.medium))

                            if showPaytable {
                                VStack(spacing: 4) {
                                    Text("Paytable (\(bet) coin\(bet == 1 ? "" : "s"))")
                                        .font(.subheadline.weight(.semibold))

                                    ForEach(paytableEntries(for: selectedVariantId, bet: bet), id: \.name) { entry in
                                        HStack {
                                            Text(entry.name)
                                                .foregroundColor(.secondary)
                                            Spacer()
                                            Text("\(entry.payout)")
                                                .fontWeight(.semibold)
                                        }
                                        .font(.caption)
                                    }
                                }
                            }
                        }
                        .padding(12)
                        .frame(maxWidth: 320)
                        .background(Color(.secondarySystemBackground))
                        .cornerRadius(12)
                    }

                    HStack(spacing: 14) {
                        HStack {
                            Text("Bet: \(bet)")
                                .font(.headline)
                            Stepper("", value: $bet, in: 1...5)
                                .labelsHidden()
                        }

                        Divider().frame(height: 24)

                        HStack {
                            Text("Show Best Hold")
                                .font(.body)
                            Toggle("Autohold", isOn: $autoHoldEnabled)
                                .labelsHidden()
                        }
                    }

                    HStack(spacing: 16) {
                        Button("Deal") {
                            dealSuggested()
                        }
                        .buttonStyle(.borderedProminent)

                        Button("Draw") {
                            drawSelected()
                        }
                        .buttonStyle(.bordered)
                        .disabled(!canDraw)
                    }

                    if !errorText.isEmpty {
                        Text(errorText)
                            .foregroundColor(.red)
                            .multilineTextAlignment(.center)
                    }

                    VStack(spacing: 14) {
                        VStack(spacing: 8) {
                            Text("Dealt Hand (tap to hold or discard)")
                                .font(.subheadline.weight(.semibold))
                            CardRow(
                                cards: initialCards,
                                interactive: canDraw,
                                suggestedMask: autoHoldEnabled ? suggestedMask : nil
                            ) { idx in
                                if canDraw {
                                    initialCards[idx].held.toggle()
                                    sounds.play(.cardHoldToggled, enabled: soundEnabled)
                                    haptics.perform(.cardHoldToggled, enabled: hapticsEnabled)
                                    updateMistakeAnalysis(cards: initialCards)
                                }
                            }
                        }

                        if !explanationLabel.isEmpty && !initialCards.isEmpty {
                            VStack(spacing: 10) {
                                Button(showExplanationDetails ? "Hide Strategy Explanation" : "Strategy Explanation") {
                                    showExplanationDetails.toggle()
                                }
                                .font(.caption)

                                if showExplanationDetails {
                                    Text("Best Hold: \(explanationLabel)")
                                        .font(.subheadline.weight(.medium))
                                        .multilineTextAlignment(.center)

                                    VStack(spacing: 8) {
                                        Text(explanationSummary)
                                            .font(.caption)
                                            .foregroundColor(.secondary)
                                            .multilineTextAlignment(.center)

                                        if !explanationPatternTip.isEmpty {
                                            Text("Pattern tip: \(explanationPatternTip)")
                                                .font(.caption)
                                                .foregroundColor(.secondary)
                                                .multilineTextAlignment(.center)
                                        }

                                        if !mistakeSeverity.isEmpty, let evDelta = mistakeEvDelta {
                                            Text("Current choice: \(severityDisplayText(mistakeSeverity))")
                                                .font(.caption)
                                                .foregroundColor(severityColor(mistakeSeverity))
                                                .multilineTextAlignment(.center)

                                            Text("EV loss vs solver: \(String(format: "%.2f", evDelta))")
                                                .font(.caption)
                                                .foregroundColor(.secondary)
                                                .multilineTextAlignment(.center)
                                        }

                                        if let bestEV = solverBestEV,
                                           let nextEV = solverNextEV,
                                           !solverNextBest.isEmpty {
                                            VStack(spacing: 0) {
                                                Text("Best EV: \(String(format: "%.2f", bestEV))")
                                                    .font(.caption)
                                                    .foregroundColor(.secondary)
                                                    .multilineTextAlignment(.center)

                                                Text("Next best: Hold \(solverNextBest) - EV \(String(format: "%.2f", nextEV))")
                                                    .font(.caption)
                                                    .foregroundColor(.secondary)
                                                    .multilineTextAlignment(.center)

                                                Text("EV edge: +\(String(format: "%.2f", bestEV - nextEV))")
                                                    .font(.caption)
                                                    .foregroundColor(.secondary)
                                                    .multilineTextAlignment(.center)
                                            }
                                        }
                                    }
                                }
                            }
                        }

                        VStack(spacing: 8) {
                            Text("Final Hand")
                                .font(.subheadline.weight(.semibold))
                            CardRow(cards: finalCards, interactive: false, suggestedMask: nil) { _ in }
                        }
                    }

                    Text("Payout: \(payout)")
                        .font(.subheadline.weight(.bold))
                        .foregroundColor(payout > 0 ? .green : .secondary)
                }
                .padding()
                .frame(maxWidth: .infinity)
            }
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button {
                        activeSheet = .help
                    } label: {
                        toolbarImageButton(named: "help", accessibilityLabel: "Help")
                    }
                }
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        activeSheet = .settings
                    } label: {
                        toolbarImageButton(named: "settings", accessibilityLabel: "Settings")
                    }
                }
            }
        }
        .sheet(item: $activeSheet) { sheet in
            switch sheet {
            case .help:
                HelpView()
            case .settings:
                SettingsView(
                    autoShowExplanation: $autoShowExplanation,
                    soundEnabled: $soundEnabled,
                    hapticsEnabled: $hapticsEnabled,
                    appVersionText: appVersionText,
                    onPlaceholderAction: { settingsMessage = $0 }
                )
            }
        }
        .alert("Not Available Yet", isPresented: Binding(
            get: { settingsMessage != nil },
            set: { if !$0 { settingsMessage = nil } }
        )) {
            Button("OK", role: .cancel) {
                settingsMessage = nil
            }
        } message: {
            Text(settingsMessage ?? "")
        }
        .onChange(of: autoHoldEnabled) { _ in
            refreshSuggestedHolds()
        }
        .onChange(of: canDraw) { newValue in
            if newValue {
                refreshSuggestedHolds()
            }
        }
        .onChange(of: bet) { _ in
            refreshSuggestedHolds()
        }
        .onChange(of: selectedVariantId) { _ in
            resetHandState()
        }
    }

    private func prepareEngine() -> NSError? {
        do {
            try bridge.setEngine("solver")
            try bridge.setVariant(selectedVariantId)
            return nil
        } catch {
            return error as NSError
        }
    }

    private func resetHandState() {
        initialCards = []
        finalCards = []
        payout = 0
        errorText = ""
        suggestedMask = 0
        explanationCategory = ""
        explanationLabel = ""
        explanationSummary = ""
        explanationPatternTip = ""
        showExplanationDetails = false
        mistakeSeverity = ""
        mistakeEvDelta = nil
        solverNextBest = ""
        solverBestEV = nil
        solverNextEV = nil
        canDraw = false
    }

    private func dealSuggested() {
        errorText = ""
        if let err = prepareEngine() {
            errorText = err.localizedDescription
            return
        }

        let handData: [AnyHashable: Any]
        do {
            handData = try bridge.dealSuggested(withBet: bet)
        } catch {
            errorText = (error as NSError).localizedDescription
            return
        }

        payout = 0
        canDraw = true
        suggestedMask = handData["holdMask"] as? Int ?? 0

        let initial = handData["initial"] as? [[String: Any]] ?? []
        initialCards = initial.map {
            UiCard(
                suit: $0["s"] as? Int ?? 1,
                rank: $0["r"] as? Int ?? 2,
                held: autoHoldEnabled ? (($0["held"] as? Int ?? 0) == 1) : false,
                winning: ($0["winning"] as? Int ?? 0) == 1
            )
        }
        let explanation = explainHold(cards: initialCards, holdMask: suggestedMask)
        explanationCategory = explanation.category
        explanationLabel = explanation.headline
        explanationSummary = explanation.summary
        explanationPatternTip = explanation.patternTip
        updateMistakeAnalysis(cards: initialCards)
        updateSolverAnalysis(cards: initialCards)
        showExplanationDetails = autoShowExplanation
        finalCards = []
        sounds.play(.dealPerformed, enabled: soundEnabled)
        haptics.perform(.dealPerformed, enabled: hapticsEnabled)
    }

    private func drawSelected() {
        errorText = ""
        let mask = initialCards.enumerated().reduce(0) { acc, pair in
            let (idx, card) = pair
            return card.held ? (acc | (1 << idx)) : acc
        }

        let handData: [AnyHashable: Any]
        do {
            handData = try bridge.draw(withBet: bet, holdMask: UInt(mask))
        } catch {
            errorText = (error as NSError).localizedDescription
            return
        }

        canDraw = false
        payout = handData["payout"] as? Int ?? 0
        explanationCategory = ""
        explanationLabel = ""
        explanationSummary = ""
        explanationPatternTip = ""
        mistakeSeverity = ""
        mistakeEvDelta = nil
        solverNextBest = ""
        solverBestEV = nil
        solverNextEV = nil
        showExplanationDetails = false

        let initial = handData["initial"] as? [[String: Any]] ?? []
        initialCards = initial.map {
            UiCard(
                suit: $0["s"] as? Int ?? 1,
                rank: $0["r"] as? Int ?? 2,
                held: ($0["held"] as? Int ?? 0) == 1,
                winning: ($0["winning"] as? Int ?? 0) == 1
            )
        }

        let final = handData["final"] as? [[String: Any]] ?? []
        finalCards = final.map {
            UiCard(
                suit: $0["s"] as? Int ?? 1,
                rank: $0["r"] as? Int ?? 2,
                held: ($0["held"] as? Int ?? 0) == 1,
                winning: ($0["winning"] as? Int ?? 0) == 1
            )
        }
        sounds.play(.drawPerformed, enabled: soundEnabled)
        haptics.perform(.drawPerformed, enabled: hapticsEnabled)
        if payout > 0 {
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.15) {
                sounds.play(.winResultShown, enabled: soundEnabled)
                haptics.perform(.winResultShown, enabled: hapticsEnabled)
            }
        }
    }

    private func refreshSuggestedHolds() {
        guard canDraw, initialCards.count == 5 else {
            return
        }

        errorText = ""
        if let err = prepareEngine() {
            errorText = err.localizedDescription
            return
        }

        let suits = initialCards.map { NSNumber(value: $0.suit) }
        let ranks = initialCards.map { NSNumber(value: $0.rank) }
        var updatedMask: UInt = 0

        do {
            try bridge.calculateHoldMask(withBet: bet, suits: suits, ranks: ranks, holdMask: &updatedMask)
            suggestedMask = Int(updatedMask)
            let explanation = explainHold(cards: initialCards, holdMask: suggestedMask)
            explanationCategory = explanation.category
            explanationLabel = explanation.headline
            explanationSummary = explanation.summary
            explanationPatternTip = explanation.patternTip
            if autoHoldEnabled {
                applyHoldMask(Int(updatedMask))
            }
            updateMistakeAnalysis(cards: initialCards)
            updateSolverAnalysis(cards: initialCards)
        } catch {
            errorText = (error as NSError).localizedDescription
        }
    }

    private func updateMistakeAnalysis(cards: [UiCard]) {
        guard cards.count == 5 else {
            mistakeSeverity = ""
            mistakeEvDelta = nil
            return
        }

        let suits = cards.map { NSNumber(value: $0.suit) }
        let ranks = cards.map { NSNumber(value: $0.rank) }
        let holdMask = cards.enumerated().reduce(0) { acc, pair in
            let (idx, card) = pair
            return card.held ? (acc | (1 << idx)) : acc
        }

        do {
            let analysis = try bridge.analyzePlayerHold(withBet: bet, suits: suits, ranks: ranks, holdMask: UInt(holdMask))
            mistakeSeverity = analysis["severity"] as? String ?? ""
            mistakeEvDelta = analysis["evDelta"] as? Double
        } catch {
            mistakeSeverity = ""
            mistakeEvDelta = nil
        }
    }

    private func updateSolverAnalysis(cards: [UiCard]) {
        guard let analysis = analyzeSolver(cards: cards) else {
            solverNextBest = ""
            solverBestEV = nil
            solverNextEV = nil
            return
        }

        solverBestEV = analysis.bestEV
        solverNextEV = analysis.secondEV
        solverNextBest = formatHeldCards(cards: cards, holdMask: analysis.secondMask)
    }

    private func applyHoldMask(_ holdMask: Int) {
        initialCards = initialCards.enumerated().map { idx, card in
            var updatedCard = card
            updatedCard.held = (holdMask & (1 << idx)) != 0
            return updatedCard
        }
    }

    private func explainHold(cards: [UiCard], holdMask: Int) -> (category: String, headline: String, summary: String, patternTip: String) {
        let suits = cards.map { NSNumber(value: $0.suit) }
        let ranks = cards.map { NSNumber(value: $0.rank) }
        do {
            let explanation = try bridge.explainHold(withSuits: suits, ranks: ranks, holdMask: UInt(holdMask))
            let category = explanation["category"] as? String ?? ""
            let headline = explanation["headline"] as? String ?? ""
            let summary = explanation["summary"] as? String ?? ""
            let patternTip = explanation["patternTip"] as? String ?? ""
            return (category, headline, summary, patternTip)
        } catch {
            return ("", "", "", "")
        }
    }

    private func analyzeSolver(cards: [UiCard]) -> (bestMask: Int, secondMask: Int, bestEV: Double, secondEV: Double)? {
        let suits = cards.map { NSNumber(value: $0.suit) }
        let ranks = cards.map { NSNumber(value: $0.rank) }
        do {
            let analysis = try bridge.analyzeSolver(withBet: bet, suits: suits, ranks: ranks)
            return (
                bestMask: analysis["bestMask"] as? Int ?? 0,
                secondMask: analysis["secondMask"] as? Int ?? 0,
                bestEV: analysis["bestEV"] as? Double ?? 0,
                secondEV: analysis["secondEV"] as? Double ?? 0
            )
        } catch {
            return nil
        }
    }

    private func formatHeldCards(cards: [UiCard], holdMask: Int) -> String {
        let held = cards.enumerated().compactMap { index, card -> String? in
            guard (holdMask & (1 << index)) != 0 else {
                return nil
            }
            return "\(rankText(card.rank))\(suitText(card.suit))"
        }
        return held.isEmpty ? "nothing" : held.joined(separator: " ")
    }

    private func severityColor(_ severity: String) -> Color {
        switch severity {
        case "perfect": return .green
        case "very_close": return Color(red: 0.33, green: 0.55, blue: 0.18)
        case "small_leak": return .yellow
        case "moderate": return .orange
        case "major": return .red
        default: return .secondary
        }
    }

    private func severityDisplayText(_ severity: String) -> String {
        switch severity {
        case "perfect": return "perfect"
        case "very_close": return "very close"
        case "small_leak": return "small mistake"
        case "moderate": return "moderate mistake"
        case "major": return "major mistake"
        default: return severity
        }
    }

    private func rankText(_ rank: Int) -> String {
        switch rank {
        case 14: return "A"
        case 13: return "K"
        case 12: return "Q"
        case 11: return "J"
        case 10: return "10"
        default: return String(rank)
        }
    }

    private func suitText(_ suit: Int) -> String {
        switch suit {
        case 1: return "s"
        case 2: return "c"
        case 3: return "h"
        case 4: return "d"
        default: return "?"
        }
    }

    @ViewBuilder
    private func toolbarImageButton(named imageName: String, accessibilityLabel: String) -> some View {
        if let path = Bundle.main.path(forResource: imageName, ofType: "png"),
           let image = UIImage(contentsOfFile: path) {
            Image(uiImage: image)
                .resizable()
                .aspectRatio(contentMode: .fit)
                .frame(height: 22)
                .accessibilityLabel(accessibilityLabel)
        } else {
            Text(accessibilityLabel)
        }
    }
}

private struct HelpView: View {
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    HelpSectionView(
                        title: "How the trainer works",
                        detail: "Deal a hand, choose which cards to hold, then draw. The trainer compares your choice to the solver-backed best play."
                    )
                    HelpSectionView(
                        title: "Holding and discarding",
                        detail: "Turn off Show Best Hold if you want to choose cards yourself. Tap dealt cards to hold or release them before drawing."
                    )
                    HelpSectionView(
                        title: "Show Best Hold",
                        detail: "When this is on, the trainer marks the solver-recommended hold for the current hand."
                    )
                    HelpSectionView(
                        title: "Mistake levels",
                        detail: "Perfect means you matched the best play. Very close means the EV loss was tiny. Small, moderate, and major mistakes mean you gave up more value versus the solver."
                    )
                    HelpSectionView(
                        title: "What EV means",
                        detail: "EV stands for expected value. It is the average return of a play over many repetitions, not a guarantee for one hand."
                    )
                    HelpSectionView(
                        title: "Free variants",
                        detail: "9/6 and 8/5 describe the full house and flush payouts. 9/6 returns more under optimal play than 8/5."
                    )
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding()
            }
            .navigationTitle("Help / How to Play")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Done") { dismiss() }
                }
            }
        }
    }
}

private struct SettingsView: View {
    @Binding var autoShowExplanation: Bool
    @Binding var soundEnabled: Bool
    @Binding var hapticsEnabled: Bool
    let appVersionText: String
    let onPlaceholderAction: (String) -> Void

    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            List {
                Section("Trainer") {
                    Toggle("Auto-show strategy explanation", isOn: $autoShowExplanation)
                }

                Section("Feedback") {
                    Toggle("Sound", isOn: $soundEnabled)
                    Toggle("Haptics", isOn: $hapticsEnabled)
                }

                Section("About") {
                    Button("Restore Purchases") {
                        onPlaceholderAction("Purchase restore is reserved for future premium content and is not active in this MVP.")
                    }
                    Button("Privacy Policy") {
                        onPlaceholderAction("A dedicated privacy policy link has not been added to the app yet.")
                    }
                    Button("Terms") {
                        onPlaceholderAction("A dedicated terms link has not been added to the app yet.")
                    }
                    HStack {
                        Text("App Version")
                        Spacer()
                        Text(appVersionText)
                            .foregroundColor(.secondary)
                    }
                }
            }
            .navigationTitle("Settings / About")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Done") { dismiss() }
                }
            }
        }
    }
}

private struct HelpSectionView: View {
    let title: String
    let detail: String

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(title)
                .font(.subheadline.weight(.semibold))
            Text(detail)
                .font(.caption)
                .foregroundColor(.secondary)
        }
    }
}

private struct PaytableEntry: Identifiable {
    let name: String
    let payout: Int

    var id: String { name }
}

private func paytableEntries(for variantId: String, bet: Int) -> [PaytableEntry] {
    let fullHouse = variantId == "jacks_or_better_8_5" ? 8 : 9
    let flush = variantId == "jacks_or_better_8_5" ? 5 : 6
    return [
        PaytableEntry(name: "Royal Flush", payout: bet == 5 ? 4000 : bet * 250),
        PaytableEntry(name: "Straight Flush", payout: bet * 50),
        PaytableEntry(name: "Four of a Kind", payout: bet * 25),
        PaytableEntry(name: "Full House", payout: bet * fullHouse),
        PaytableEntry(name: "Flush", payout: bet * flush),
        PaytableEntry(name: "Straight", payout: bet * 4),
        PaytableEntry(name: "Three of a Kind", payout: bet * 3),
        PaytableEntry(name: "Two Pair", payout: bet * 2),
        PaytableEntry(name: "Jacks or Better", payout: bet)
    ]
}

struct CardRow: View {
    let cards: [UiCard]
    let interactive: Bool
    let suggestedMask: Int?
    let onTap: (Int) -> Void

    var body: some View {
        HStack(spacing: 8) {
            ForEach(Array(cards.enumerated()), id: \.element.id) { idx, card in
                ZStack {
                    cardImage(suit: card.suit, rank: card.rank)
                        .background(card.winning ? Color.yellow.opacity(0.1) : Color.white)
                        .cornerRadius(8)
                        .shadow(radius: 1)

                    if card.held && !card.winning {
                        Color.black.opacity(0.15)
                            .cornerRadius(8)

                        VStack {
                            Spacer()
                            Text("HELD")
                                .font(.system(size: 8, weight: .heavy))
                                .foregroundColor(.white)
                                .padding(.horizontal, 4)
                                .padding(.vertical, 1)
                                .background(Color.orange)
                                .cornerRadius(2)
                        }
                        .padding(.bottom, 4)
                    }

                    if card.winning {
                        VStack {
                            Spacer()
                            Text("WIN")
                                .font(.system(size: 8, weight: .heavy))
                                .foregroundColor(.black)
                                .padding(.horizontal, 4)
                                .padding(.vertical, 1)
                                .background(Color.yellow)
                                .cornerRadius(2)
                        }
                        .padding(.bottom, 4)
                    }
                }
                .frame(width: 60, height: 90)
                .overlay(
                    RoundedRectangle(cornerRadius: 8)
                        .stroke(strokeColor(index: idx, card: card), lineWidth: strokeWidth(index: idx, card: card))
                )
                .onTapGesture {
                    if interactive {
                        onTap(idx)
                    }
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .center)
    }

    private func cardImageName(suit: Int, rank: Int) -> String {
        let r: String
        switch rank {
        case 14: r = "ace"
        case 13: r = "king"
        case 12: r = "queen"
        case 11: r = "jack"
        case 10: r = "ten"
        case 9: r = "nine"
        case 8: r = "eight"
        case 7: r = "seven"
        case 6: r = "six"
        case 5: r = "five"
        case 4: r = "four"
        case 3: r = "three"
        case 2: r = "two"
        default: r = ""
        }
        let s: String
        switch suit {
        case 1: s = "spades"
        case 2: s = "clubs"
        case 3: s = "hearts"
        case 4: s = "diamonds"
        default: s = ""
        }
        return "\(r)_\(s)"
    }

    private func cardImage(suit: Int, rank: Int) -> some View {
        let imageName = cardImageName(suit: suit, rank: rank)
        let uiImage = UIImage(
            contentsOfFile: Bundle.main.path(forResource: imageName, ofType: "png", inDirectory: "cards") ?? ""
        ) ?? UIImage(
            contentsOfFile: Bundle.main.path(forResource: "card_back", ofType: "png", inDirectory: "cards") ?? ""
        ) ?? UIImage()

        return Image(uiImage: uiImage)
            .resizable()
            .aspectRatio(contentMode: .fit)
    }

    private func strokeColor(index: Int, card: UiCard) -> Color {
        if card.winning { return .yellow }
        guard interactive, let suggestedMask else {
            return card.held ? .orange : Color.black.opacity(0.2)
        }
        let suggested = (suggestedMask & (1 << index)) != 0
        if card.held == suggested {
            return card.held ? .green : Color.black.opacity(0.2)
        }
        return .red
    }

    private func strokeWidth(index: Int, card: UiCard) -> CGFloat {
        if card.winning { return 3 }
        guard interactive, let suggestedMask else {
            return card.held ? 2 : 1
        }
        let suggested = (suggestedMask & (1 << index)) != 0
        return card.held == suggested ? (card.held ? 2 : 1) : 3
    }
}
